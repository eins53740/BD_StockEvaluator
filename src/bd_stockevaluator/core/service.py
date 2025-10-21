"""
Reusable core logic for stock evaluation workflows.

This module decouples the business logic from the Flask web layer so it can be
reused by alternative backends (e.g., FastAPI) and future Android integrations.
"""

from __future__ import annotations

import os
import json
import textwrap
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, MutableMapping, Sequence, Tuple

from cachetools import TTLCache, cached
from dotenv import load_dotenv

from ..evaluator import StockEvaluator
from ..features import StockAnalysisFeatures
from ..analysis import (
    Epic2Analyzer,
    Epic3TechnicalAnalyzer,
    ManagementQualityAnalyzer,
    MoatAssessmentInput,
    MoatScorecardBuilder,
    OwnershipTrendAnalyzer,
)
from .data_pipeline import (
    CurrencyConverter,
    MultiSourceDataClient,
    SchedulerHooks,
    SQLiteDataStore,
)
from .keys import get_api_key
from .macro import MacroContextService
from .watchlist import WatchlistAlert, WatchlistAlertEngine

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(__file__).resolve().parents[3]

ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH, override=False)

try:
    from groq import Groq as _GroqClient
except Exception:  # Groq optional
    _GroqClient = None

try:
    import google.generativeai as genai
    from google.generativeai import types
except Exception:  # Gemini SDK optional
    genai = None
    types = None

try:
    import markdown as _markdown

    def _md_to_html(text: str) -> str:
        return _markdown.markdown(text)

except Exception:  # Markdown optional

    def _md_to_html(text: str) -> str:
        return f"<pre>{text or ''}</pre>"


DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

STATIC_DIR = PACKAGE_ROOT / "static"

DEFAULT_RATES = {
    "USD": 1.0,
    "EUR": 1.07,
    "GBP": 1.27,
}

DATA_STORE = SQLiteDataStore(DATA_DIR / "stocks.db")
CURRENCY_CONVERTER = CurrencyConverter(DEFAULT_RATES)
DATA_CLIENT = MultiSourceDataClient(store=DATA_STORE, converter=CURRENCY_CONVERTER)
SCHEDULER_HOOKS = SchedulerHooks(DATA_CLIENT)
MACRO_DATA_DIR = DATA_DIR / "macro"
MACRO_DATA_DIR.mkdir(parents=True, exist_ok=True)
MACRO_SERVICE = MacroContextService(DATA_STORE, DATA_DIR)
QUALITATIVE_MOAT_BUILDER = MoatScorecardBuilder()
OWNERSHIP_ANALYZER = OwnershipTrendAnalyzer()
MANAGEMENT_ANALYZER = ManagementQualityAnalyzer()


def _ensure_gemini_imported() -> bool:
    """Attempt lazy import of the Gemini SDK if not already loaded."""
    global genai, types
    if genai is not None and types is not None:
        return True
    try:
        import importlib

        genai = importlib.import_module("google.generativeai")
        types = importlib.import_module("google.generativeai.types")
        return True
    except Exception as exc:
        print(f"Gemini SDK lazy import failed: {exc}")
        return False


def fmt(val: Optional[float], is_percent: bool = False, default: str = "n/a") -> str:
    """Format numeric values for display."""
    if val is None:
        return default
    if is_percent:
        return f"{(val * 100):.1f}%"
    return f"{val:.2f}"


def _coalesce_trend(*values: Optional[float]) -> Optional[float]:
    for value in values:
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _normalize_records(entries: Sequence[Any]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for entry in entries:
        if isinstance(entry, Mapping):
            converted: Dict[str, Any] = {}
            for key, value in entry.items():
                if isinstance(value, datetime):
                    converted[key] = value.isoformat()
                else:
                    converted[key] = value
            normalized.append(converted)
        else:
            normalized.append(entry if isinstance(entry, dict) else {"value": entry})
    return normalized


def _score_from_ranges(
    value: Optional[float],
    ranges: Sequence[tuple[float, float]],
    *,
    fallback: float,
) -> Optional[float]:
    if value is None:
        return None
    for threshold, score in ranges:
        if value >= threshold:
            return round(score, 2)
    return round(fallback, 2)


def _normalize_metric(
    value: Optional[float],
    *,
    lower: float,
    upper: float,
    default: float = 0.5,
) -> float:
    if value is None:
        return default
    if upper == lower:
        return default
    ratio = (float(value) - lower) / (upper - lower)
    return float(_clamp(ratio, 0.0, 1.0))


def _estimate_manual_moat_scores(
    stock_info: Mapping[str, Any],
) -> Dict[str, Optional[float]]:
    profit_margins = stock_info.get("profitMargins")
    revenue_growth = stock_info.get("revenueGrowth")
    return_on_equity = stock_info.get("returnOnEquity")
    fcf_yield = stock_info.get("fcfYield")
    market_cap = stock_info.get("marketCap")
    market_cap_billions = (
        float(market_cap) / 1_000_000_000
        if isinstance(market_cap, (int, float))
        else None
    )

    return {
        "switching_costs": _score_from_ranges(
            profit_margins,
            [(0.25, 4.6), (0.18, 4.1), (0.12, 3.6), (0.08, 3.1)],
            fallback=2.7,
        ),
        "network_effects": _score_from_ranges(
            revenue_growth,
            [(0.18, 4.5), (0.12, 4.0), (0.06, 3.5), (0.0, 3.0)],
            fallback=2.6,
        ),
        "intangibles": _score_from_ranges(
            return_on_equity,
            [(0.22, 4.7), (0.18, 4.2), (0.12, 3.6), (0.08, 3.1)],
            fallback=2.8,
        ),
        "cost_advantage": _score_from_ranges(
            fcf_yield,
            [(0.08, 4.8), (0.06, 4.0), (0.04, 3.4), (0.02, 3.0)],
            fallback=2.6,
        ),
        "efficient_scale": _score_from_ranges(
            market_cap_billions,
            [(200, 4.6), (50, 4.0), (10, 3.4), (2, 3.0)],
            fallback=2.5,
        ),
    }


def _build_ai_moat_summaries(
    stock_info: Mapping[str, Any],
    manual_scores: Mapping[str, Optional[float]],
) -> Dict[str, Dict[str, Any]]:
    descriptors = {
        "switching_costs": (
            stock_info.get("profitMargins"),
            (0.05, 0.30),
            lambda v: (
                f"Profit margin at {v * 100:.1f}% supports sticky contracts."
                if v is not None
                else "Profit margin data unavailable; assuming neutral switching costs."
            ),
        ),
        "network_effects": (
            stock_info.get("revenueGrowth"),
            (0.0, 0.22),
            lambda v: (
                f"Revenue growth of {v * 100:.1f}% suggests expanding demand."
                if v is not None
                else "Growth data unavailable; network effects estimated conservatively."
            ),
        ),
        "intangibles": (
            stock_info.get("returnOnEquity"),
            (0.06, 0.28),
            lambda v: (
                f"ROE at {v * 100:.1f}% indicates durable brand and execution."
                if v is not None
                else "Return on equity missing; intangible moat scored neutrally."
            ),
        ),
        "cost_advantage": (
            stock_info.get("fcfYield"),
            (0.01, 0.10),
            lambda v: (
                f"FCF yield of {v * 100:.1f}% highlights pricing discipline."
                if v is not None
                else "Free cash flow not available; cost edge inferred from peers."
            ),
        ),
        "efficient_scale": (
            stock_info.get("marketCap"),
            (1_000_000_000, 200_000_000_000),
            lambda v: (
                f"Scale around {v/1_000_000_000:.1f}B market cap offers operating leverage."
                if v is not None
                else "Scale data unavailable; efficient scale treated as average."
            ),
        ),
    }

    summaries: Dict[str, Dict[str, Any]] = {}
    for dimension, (metric_value, bounds, summary_builder) in descriptors.items():
        if dimension == "efficient_scale":
            low, high = bounds
            value = (
                float(metric_value) if isinstance(metric_value, (int, float)) else None
            )
            normalized = _normalize_metric(value, lower=low, upper=high, default=0.5)
        else:
            low, high = bounds
            normalized = _normalize_metric(
                float(metric_value) if isinstance(metric_value, (int, float)) else None,
                lower=low,
                upper=high,
            )
        manual_score = manual_scores.get(dimension)
        if manual_score is not None:
            normalized = (normalized + manual_score / 5.0) / 2
        summary = summary_builder(
            metric_value if isinstance(metric_value, (int, float)) else None
        )
        summaries[dimension] = {
            "score": round(_clamp(normalized, 0.0, 1.0), 3),
            "summary": summary,
        }
    return summaries


def _extract_ownership_history(stock_info: Mapping[str, Any]) -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = []
    for entry in stock_info.get("ownershipHistory", []) or []:
        if not isinstance(entry, Mapping):
            continue
        raw_date = entry.get("date")
        if not raw_date:
            continue
        if isinstance(raw_date, datetime):
            date_val = raw_date
        else:
            raw = str(raw_date)
            if raw.endswith("Z"):
                raw = raw[:-1] + "+00:00"
            try:
                date_val = datetime.fromisoformat(raw)
            except Exception:
                continue
        history.append(
            {
                "date": date_val,
                "institutional": entry.get("institutional"),
                "insider": entry.get("insider"),
            }
        )
    return history


def _infer_governance_flags(stock_info: Mapping[str, Any]) -> List[str]:
    flags: List[str] = []
    for field in (
        "auditRisk",
        "boardRisk",
        "compensationRisk",
        "shareholderRightsRisk",
    ):
        value = stock_info.get(field)
        if isinstance(value, (int, float)) and value >= 4:
            flags.append(field.lower())
    esg = stock_info.get("esgRiskScore")
    if isinstance(esg, (int, float)) and esg > 35:
        flags.append("esg_risk_elevated")
    return flags


def _determine_capex_focus(advanced_analysis: Optional[Dict[str, Any]]) -> str:
    if not advanced_analysis:
        return "balanced"
    growth = advanced_analysis.get("growth") or {}
    overall = growth.get("overall_score")
    metrics = growth.get("metrics") or {}
    fcf_metric = metrics.get("fcf") if isinstance(metrics, Mapping) else {}
    acceleration = (fcf_metric or {}).get("acceleration")
    if acceleration == "accelerating" or (overall and overall >= 70):
        return "growth"
    if overall and overall >= 55:
        return "balanced"
    return "maintenance"


def _extract_executive_tenure(stock_info: Mapping[str, Any]) -> Optional[float]:
    for key in ("ceoTenure", "averageTenure", "managementTenure"):
        value = stock_info.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _build_management_metrics(
    stock_info: Mapping[str, Any],
    advanced_analysis: Optional[Dict[str, Any]],
    ownership_summary: Mapping[str, Any],
    risk_assessment: Mapping[str, Any],
) -> tuple[Dict[str, Any], List[str]]:
    historical = stock_info.get("historicalMetrics") or []
    roic_series: List[float] = []
    for item in historical:
        if not isinstance(item, Mapping):
            continue
        for key in ("roic", "return_on_invested_capital", "roe"):
            value = item.get(key)
            if isinstance(value, (int, float)):
                roic_series.append(float(value))
                break
    roic_series = roic_series[-6:]

    capital_allocation = {
        "share_buybacks": bool(
            isinstance(stock_info.get("buybackYield"), (int, float))
            and stock_info.get("buybackYield", 0) < 0
        ),
        "dividend_growth": bool(
            isinstance(stock_info.get("dividendYield"), (int, float))
            and stock_info.get("dividendYield", 0) > 0
        ),
        "capex_focus": _determine_capex_focus(advanced_analysis),
    }

    governance_flags = _infer_governance_flags(stock_info)
    tenure = _extract_executive_tenure(stock_info)

    insider_block = (
        ownership_summary.get("insider")
        if isinstance(ownership_summary, Mapping)
        else {}
    )
    insider_alignment = None
    if isinstance(insider_block, Mapping):
        latest = insider_block.get("latest")
        if isinstance(latest, (int, float)):
            insider_alignment = latest / 100.0

    culture = None
    for key in ("glassdoorRating", "employeeOpinionScore", "cultureScore"):
        value = stock_info.get(key)
        if isinstance(value, (int, float)):
            culture = float(value)
            break

    qualitative_notes = list(risk_assessment.get("recommendations", []) or [])
    for alert in ownership_summary.get("alerts", []) or []:
        qualitative_notes.append(alert)
    qualitative_notes = [str(note) for note in qualitative_notes if note]

    metrics = {
        "roic_trend": roic_series,
        "capital_allocation": capital_allocation,
        "governance_flags": governance_flags,
        "tenure_years": tenure,
        "insider_alignment": insider_alignment,
        "glassdoor_rating": culture,
    }
    return metrics, qualitative_notes


def _build_qualitative_components(
    stock_info: MutableMapping[str, Any],
    advanced_analysis: Optional[Dict[str, Any]],
    risk_assessment: Mapping[str, Any],
) -> Dict[str, Any]:
    manual_scores = _estimate_manual_moat_scores(stock_info)
    ai_summaries = _build_ai_moat_summaries(stock_info, manual_scores)

    shared_notes = list(risk_assessment.get("recommendations", []) or [])[:4]
    qualitative_notes_map = {
        dimension: shared_notes
        for dimension in (
            "switching_costs",
            "network_effects",
            "intangibles",
            "cost_advantage",
            "efficient_scale",
        )
    }

    moat_input = MoatAssessmentInput(
        manual_scores=manual_scores,
        ai_summaries=ai_summaries,
        qualitative_notes=qualitative_notes_map,
    )
    moat_scorecard = QUALITATIVE_MOAT_BUILDER.build(moat_input)
    moat_payload = {
        "overall_score": moat_scorecard.overall_score,
        "moat_rating": moat_scorecard.moat_rating,
        "dimensions": {
            key: {
                "manual_score": dimension.manual_score,
                "ai_score": dimension.ai_score,
                "combined_score": dimension.combined_score,
                "summary": dimension.summary,
                "notes": dimension.notes,
            }
            for key, dimension in moat_scorecard.dimensions.items()
        },
    }

    ownership_history = _extract_ownership_history(stock_info)
    ownership_summary = OWNERSHIP_ANALYZER.summarise(ownership_history)

    management_metrics, qualitative_notes = _build_management_metrics(
        stock_info,
        advanced_analysis,
        ownership_summary,
        risk_assessment,
    )
    management_quality = MANAGEMENT_ANALYZER.evaluate(
        management_metrics, qualitative_notes
    )

    return {
        "moat": moat_payload,
        "ownership": ownership_summary,
        "management": management_quality,
    }


def _derive_fundamental_trends(
    advanced_analysis: Optional[Dict[str, Any]],
    stock_info: MutableMapping[str, Any],
) -> Dict[str, Dict[str, Optional[float]]]:
    growth_metrics = (
        (advanced_analysis or {}).get("growth", {}).get("metrics", {})
        if advanced_analysis
        else {}
    )
    revenue_metric = (
        growth_metrics.get("revenue", {}) if isinstance(growth_metrics, dict) else {}
    )
    eps_metric = (
        growth_metrics.get("eps", {}) if isinstance(growth_metrics, dict) else {}
    )
    fcf_metric = (
        growth_metrics.get("fcf", {}) if isinstance(growth_metrics, dict) else {}
    )

    trends = {
        "revenue_growth": {
            "trend": _coalesce_trend(
                revenue_metric.get("cagr_5y"),
                revenue_metric.get("cagr_10y"),
                stock_info.get("revenueGrowth"),
            )
        },
        "eps_growth": {
            "trend": _coalesce_trend(
                eps_metric.get("cagr_5y"),
                eps_metric.get("cagr_10y"),
                stock_info.get("earningsQuarterlyGrowth"),
            )
        },
        "fcf_growth": {
            "trend": _coalesce_trend(
                fcf_metric.get("cagr_5y"),
                fcf_metric.get("cagr_10y"),
                stock_info.get("freeCashFlowGrowth"),
            )
        },
    }
    return trends


def _build_opinion_prompt(
    company_name: str, ticker: str, metrics: Dict[str, Any]
) -> str:
    formatted_metrics = f"""
- Revenue Growth (TTM): {fmt(metrics.get('rev_growth'), is_percent=True)}
- P/E Ratio: {fmt(metrics.get('pe'))}
- Return on Equity (ROE): {fmt(metrics.get('roe'), is_percent=True)}
- Net Profit Margin: {fmt(metrics.get('margin'), is_percent=True)}
- Debt to Equity Ratio: {fmt(metrics.get('de'))}
- Quick Ratio: {fmt(metrics.get('qr'))}
"""

    return textwrap.dedent(
        f"""
        Act as a seasoned value investor in the style of Warren Buffett.
        Start with a concise dual recommendation line: one of "buy"/"do not buy"/"neutral"
        and one of "sell"/"do not sell"/"neutral". Then explain.
        Provide a concise, fundamental, and growth-oriented analysis for the company:
        {company_name} ({ticker}).

        Here are its key financial metrics:
        {formatted_metrics}

        Based on these metrics and your investment philosophy, write a few paragraphs covering:
        1. Business Quality & Profitability: Comment on profitability (ROE, margins) and whether it suggests a quality,
           durable business with an advantage.
        2. Valuation: Discuss valuation based on P/E relative to growth prospects.
        3. Financial Health: Analyze stability and debt management (Debt/Equity, Quick Ratio).
        4. Overall Outlook: Summarize long-term suitability.

        Keep the tone professional, insightful, and focused on long-term value.
        Use markdown headings like "### Business Quality".
        """
    )


def generate_stock_opinion(
    api_key: Optional[str],
    company_name: str,
    ticker: str,
    metrics: Dict[str, Any],
) -> Optional[str]:
    """Generate AI opinion report with Groq (preferred) then Gemini fallback."""

    groq_key = api_key or get_api_key("api_key_groq")
    prompt = _build_opinion_prompt(company_name, ticker, metrics)

    if _GroqClient and groq_key:
        try:
            client_kwargs: Dict[str, Any] = {"api_key": groq_key}
            base_url = os.getenv("GROQ_API_BASE", "").strip()
            if base_url:
                client_kwargs["base_url"] = base_url
            client = _GroqClient(**client_kwargs)
            response = client.chat.completions.create(
                model=os.getenv(
                    "GROQ_MODEL", "llama-3.1-8b-instant"
                ),  # llama-3.3-70b-versatile
                messages=[
                    {
                        "role": "system",
                        "content": "You are an experienced value investor providing measured analysis.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=900,
            )
            content = response.choices[0].message.content if response.choices else None
            return _md_to_html(content or "")
        except Exception as exc:
            print(f"Groq opinion generation failed: {exc}")

    # Gemini fallback
    gemini_key = get_api_key("api_key_gemini")
    if gemini_key and _ensure_gemini_imported():
        try:
            genai.configure(api_key=gemini_key)
            model_name = os.getenv(
                "GEMINI_MODEL", "models/gemini-2.5-flash-lite"
            )  # gemini-2.5-flash-lite
            generation_config = types.GenerationConfig(
                temperature=0.4,
                max_output_tokens=900,
            )
            model = genai.GenerativeModel(
                model_name, generation_config=generation_config
            )
            response = model.generate_content(prompt)
            text = ""
            if hasattr(response, "text"):
                text = response.text
            elif hasattr(response, "candidates") and response.candidates:
                text = response.candidates[0].content.parts[0].text
            return _md_to_html(text or "")
        except Exception as exc:
            print(f"Gemini opinion generation failed: {exc}")

    return None


@cached(cache=TTLCache(maxsize=100, ttl=600))
def get_stock_data(ticker_symbol: str) -> Dict[str, Any]:
    """Fetch stock fundamentals through the multi-source aggregation pipeline."""

    ticker = ticker_symbol.strip().upper()
    if not ticker:
        raise ValueError("Ticker symbol is required")

    refreshed_at = datetime.now(timezone.utc)
    return DATA_CLIENT.sync_ticker(ticker, as_of=refreshed_at)


def refresh_macro_snapshot(
    *, overrides: Optional[MutableMapping[str, Sequence[Any]]] = None
) -> Dict[str, Dict]:
    """Refresh macro time-series snapshot using configured providers or overrides."""
    return MACRO_SERVICE.refresh(overrides=overrides)


def get_macro_context(
    fundamentals_trends: Optional[
        MutableMapping[str, MutableMapping[str, Optional[float]]]
    ] = None,
    *,
    ensure_fresh: bool = False,
) -> Dict[str, Dict]:
    """Retrieve macro context with optional trend alignment overrides."""
    trends = fundamentals_trends or {}
    return MACRO_SERVICE.get_context(
        fundamentals_trends=trends, ensure_fresh=ensure_fresh
    )


def generate_flowchart_definition(
    evaluator: StockEvaluator, result: str, path: Any
) -> str:
    """Produce Mermaid definition for flowchart rendering."""

    def wrap_text(text, width=20):
        """Wraps text to a maximum of two lines."""
        # Normalize whitespace and remove excessive blank lines
        if not text:
            return ""
        compact = " ".join(str(text).split())
        lines = textwrap.wrap(compact, width=width)
        if not lines:
            return ""
        if len(lines) > 2:
            lines = lines[:2]
            # ensure ellipsis doesn't create double spaces
            lines[1] = lines[1].rstrip() + "..."
        return "<br/>".join(lines)

    nodes = {
        "A": "Start Analysis",
        "B": "Revenue Growth >= 10%?",
        "C": "Valuation Check",
        "D": "Do Not Buy",
        "E": "ROE >= 15%?",
        "F": "PEG < 2?",
        "G": "Net Margin >= 10%?",
        "H": "Debt/Equity < 1?",
        "I": "Quick Ratio >= 1.5?",
        "J": "BUY",
        "K": "BUY with Caution",
    }

    graph_def = "graph TD\n"
    for node_id, text in nodes.items():
        wrapped_text = wrap_text(text)
        if node_id in ["D", "J", "K"]:
            graph_def += f'    {node_id}(["{wrapped_text}"]);\n'
        elif node_id == "A":
            graph_def += f'    {node_id}(["{wrapped_text}"]);\n'
        else:
            graph_def += f"    {node_id}{{{wrapped_text}}};\n"

    links = [
        ("A", "B"),
        ("B", "C", "Yes"),
        ("B", "D", "No"),
        ("C", "E", "P/E < 25"),
        ("C", "F", "Else"),
        ("F", "E", "Yes"),
        ("F", "D", "No"),
        ("E", "G", "Yes"),
        ("E", "D", "No"),
        ("G", "H", "Yes"),
        ("G", "D", "No"),
        ("H", "I", "Yes"),
        ("H", "D", "No"),
        ("I", "J", "Yes"),
        ("I", "K", "No"),
    ]

    for link in links:
        if len(link) == 3:
            graph_def += f"    {link[0]} -->|{link[2]}| {link[1]};\n"
        else:
            graph_def += f"    {link[0]} --> {link[1]};\n"

    node_map = {
        "Revenue Growth (TTM)": "B",
        "P/E Ratio": "C",
        "PEG Ratio": "F",
        "Return on Equity": "E",
        "Net Profit Margin": "G",
        "Debt to Equity": "H",
        "Quick Ratio": "I",
    }

    link_order = [
        ("A", "B"),
        ("B", "C"),
        ("B", "D"),
        ("C", "E"),
        ("C", "F"),
        ("F", "E"),
        ("F", "D"),
        ("E", "G"),
        ("E", "D"),
        ("G", "H"),
        ("G", "D"),
        ("H", "I"),
        ("H", "D"),
        ("I", "J"),
        ("I", "K"),
    ]
    link_map = {link: idx for idx, link in enumerate(link_order)}
    active_links = getattr(evaluator, "active_links", set())

    styles = []
    link_styles = ["linkStyle default stroke:#aaa,stroke-width:2px;"]

    for name, _, _, status in path:
        node_id = node_map.get(name)
        if not node_id:
            continue
        if status == "PASS":
            styles.append(f"class {node_id} pass;")
        elif status == "CLOSE_FAIL":
            styles.append(f"class {node_id} close_fail;")
        else:
            styles.append(f"class {node_id} fail;")

    for link in active_links:
        if link in link_map:
            link_styles.append(
                f"linkStyle {link_map[link]} stroke:#198754,stroke-width:4px;"
            )

    if "Do Not Buy" in result:
        styles.append("class D fail;")
    elif "Caution" in result:
        styles.append("class K close_fail;")
    elif "BUY" in result:
        styles.append("class J pass;")

    class_defs = textwrap.dedent(
        """
        classDef default fill:#f9f9f9,stroke:#333,stroke-width:2px,color:#333;
        classDef pass fill:#d1e7dd,stroke:#198754,stroke-width:3px,color:#000;
        classDef fail fill:#f8d7da,stroke:#dc3545,stroke-width:3px,color:#000;
        classDef close_fail fill:#fff3cd,stroke:#ffc107,stroke-width:3px,color:#000;
        classDef start fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#000;
        classDef decision fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000;
        """
    ).strip()

    styles.append("class A start;")
    for node_id in ["B", "C", "E", "F", "G", "H", "I"]:
        if not any(f"class {node_id}" in style for style in styles):
            styles.append(f"class {node_id} decision;")

    script_parts = [graph_def, class_defs, *styles, *link_styles]
    script = "\n".join(script_parts)
    # Collapse multiple blank lines to a single newline to avoid Mermaid parsing issues
    script = re.sub(r"\n{2,}", "\n", script)
    return script.strip()


class StockAnalysisService:
    """Facade providing a single entry-point for stock analysis workflows."""

    def __init__(
        self,
        opinion_api_key: Optional[str] = None,
        watchlist_engine: Optional[WatchlistAlertEngine] = None,
    ) -> None:
        self.opinion_api_key = opinion_api_key
        self.watchlist_engine = watchlist_engine or WatchlistAlertEngine()
        self.thresholds = self._load_thresholds()

    def _load_thresholds(self) -> Dict[str, float]:
        """Loads thresholds from a JSON file."""
        thresholds_path = PROJECT_ROOT / "config" / "thresholds.json"
        if thresholds_path.exists():
            with open(thresholds_path, "r") as f:
                return json.load(f)
        return StockEvaluator.THRESHOLDS

    @property
    def macro_service(self) -> MacroContextService:
        """Expose the shared macro service for downstream consumers."""
        return MACRO_SERVICE

    def analyze(
        self, ticker_symbol: str, include_opinion: bool = True
    ) -> Dict[str, Any]:
        """Run complete analysis for a ticker and return structured payload."""

        stock_info = get_stock_data(ticker_symbol)
        company_name = stock_info.get("longName", ticker_symbol.upper())

        evaluator = StockEvaluator(stock_info, thresholds=self.thresholds)
        verdict, path, active_links = evaluator.evaluate()

        flowchart_def = generate_flowchart_definition(evaluator, verdict, path)

        historical_metrics_raw = stock_info.get("historicalMetrics")
        price_history_raw = stock_info.get("priceHistory")
        historical_metrics = (
            _normalize_records(historical_metrics_raw) if historical_metrics_raw else []
        )
        price_history = (
            _normalize_records(price_history_raw) if price_history_raw else []
        )

        features_analyzer = StockAnalysisFeatures(
            ticker_symbol,
            stock_info,
            historical_metrics_raw,
        )
        risk_assessment = features_analyzer.get_risk_assessment()
        trend_analysis = features_analyzer.get_trend_analysis()
        comparative_analysis = features_analyzer.get_comparative_analysis()
        dividend_analysis = features_analyzer.get_dividend_analysis()

        epic2_analyzer = Epic2Analyzer(
            stock_info,
            stock_info.get("historicalMetrics"),
            sector=stock_info.get("sector"),
        )
        advanced_analysis = epic2_analyzer.analyze()

        technical_summary: Optional[Dict[str, Any]] = None
        try:
            if price_history:
                technical_analyzer = Epic3TechnicalAnalyzer(
                    price_history, ticker=ticker_symbol
                )
            else:
                technical_analyzer = Epic3TechnicalAnalyzer.from_ticker(ticker_symbol)
            indicators = technical_analyzer.compute_indicator_suite()
            patterns = technical_analyzer.detect_price_patterns()
            signal = technical_analyzer.generate_signal(verdict=verdict)
            performance = technical_analyzer.compute_performance_metrics()
            chart_paths = technical_analyzer.export_charts(ticker_symbol, STATIC_DIR)
            try:
                relative_png = chart_paths["png"].relative_to(STATIC_DIR)
                png_ref = str(relative_png).replace("\\", "/")
            except ValueError:
                png_ref = chart_paths["png"].name
            technical_summary = {
                "indicators": indicators,
                "patterns": patterns,
                "signal": signal,
                "performance": performance,
                "chart": {
                    "png": png_ref,
                    "json": str(chart_paths["json"]),
                },
            }
        except Exception as exc:
            technical_summary = {"error": str(exc)}

        macro_context: Optional[Dict[str, Any]] = None
        try:
            fundamental_trends = _derive_fundamental_trends(
                advanced_analysis, stock_info
            )
            macro_context = MACRO_SERVICE.get_context(
                fundamentals_trends=fundamental_trends,
                ensure_fresh=True,
            )
        except Exception as exc:
            macro_context = {"error": str(exc)}

        qualitative_components: Dict[str, Any]
        try:
            qualitative_components = _build_qualitative_components(
                stock_info,
                advanced_analysis,
                risk_assessment,
            )
        except Exception as exc:
            qualitative_components = {
                "moat": None,
                "ownership": {
                    "institutional": {
                        "trend": "unknown",
                        "change_percentage": None,
                        "latest": None,
                    },
                    "insider": {
                        "trend": "unknown",
                        "change_percentage": None,
                        "latest": None,
                    },
                    "alerts": [str(exc)],
                },
                "management": {
                    "score": None,
                    "rating": "Unknown",
                    "highlights": [],
                    "warnings": [str(exc)],
                },
            }

        opinion_report = None
        if include_opinion:
            opinion_report = generate_stock_opinion(
                self.opinion_api_key,
                company_name,
                ticker_symbol,
                evaluator.metrics,
            )

        active_links_list = sorted([[a, b] for (a, b) in active_links])

        data_providers = (
            stock_info.get("data_providers") or stock_info.get("providers") or {}
        )

        return {
            "ticker": ticker_symbol.upper(),
            "company_name": company_name,
            "result": verdict,
            "path": path,
            "active_links": active_links_list,
            "flowchart_definition": flowchart_def,
            "opinion_report": opinion_report,
            "risk_assessment": risk_assessment,
            "trend_analysis": trend_analysis,
            "comparative_analysis": comparative_analysis,
            "dividend_analysis": dividend_analysis,
            "valuation_scorecard": advanced_analysis.get("valuation"),
            "profitability_snapshot": advanced_analysis.get("profitability"),
            "growth_trends": advanced_analysis.get("growth"),
            "intrinsic_value_models": advanced_analysis.get("intrinsic_values"),
            "historical_context": advanced_analysis.get("historical_context"),
            "technical_analysis": technical_summary,
            "macro_context": macro_context,
            "qualitative_moat": qualitative_components.get("moat"),
            "ownership_trends": qualitative_components.get("ownership"),
            "management_quality": qualitative_components.get("management"),
            "metrics": evaluator.metrics,
            "data_providers": data_providers,
            "fundamentals_history": historical_metrics,
            "price_history": price_history,
            "generated_at": datetime.now(timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        }

    def evaluate_watchlist(
        self,
        watchlist: Sequence[Mapping[str, Any]],
        *,
        include_opinion: bool = False,
    ) -> Tuple[List[WatchlistAlert], Dict[str, Dict[str, Any]]]:
        """
        Evaluate configured watchlist entries and return triggered alerts.

        The method reuses the standard ``analyze`` pipeline so callers receive
        fully enriched analysis payloads alongside the alert summaries.
        """

        if not watchlist:
            return ([], {})

        analysis_results: Dict[str, Dict[str, Any]] = {}
        triggered_alerts: List[WatchlistAlert] = []

        for entry in watchlist:
            ticker = str(entry.get("ticker", "")).strip()
            if not ticker or ticker.upper() in analysis_results:
                continue
            try:
                analysis = self.analyze(ticker, include_opinion=include_opinion)
            except Exception:
                continue
            analysis_results[analysis["ticker"]] = analysis

        if analysis_results:
            try:
                triggered_alerts = self.watchlist_engine.evaluate(
                    watchlist, analysis_results
                )
            except Exception:
                triggered_alerts = []

        return triggered_alerts, analysis_results

    def build_sync_payload(self, ticker_symbol: str) -> Dict[str, Any]:
        """
        Construct a versioned payload combining normalized data for sync clients.
        """

        analysis = self.analyze(ticker_symbol, include_opinion=False)

        fundamentals_snapshot = (
            DATA_STORE.load_latest_snapshot(ticker_symbol.upper()) or {}
        )
        fundamentals_history = DATA_STORE.load_history(
            ticker_symbol.upper()
        ) or analysis.get("fundamentals_history", [])

        macro_snapshot = MACRO_SERVICE.get_snapshot() or {}

        technical_chart = analysis.get("technical_analysis", {}).get("chart") or {}

        return {
            "ticker": analysis["ticker"],
            "version": analysis["generated_at"],
            "data_providers": analysis.get("data_providers", {}),
            "fundamentals": {
                "snapshot": fundamentals_snapshot,
                "history": fundamentals_history,
            },
            "price_history": analysis.get("price_history", []),
            "technical_chart": technical_chart,
            "macro_snapshot": macro_snapshot,
        }
