"""
Reusable core logic for stock evaluation workflows.

This module decouples the business logic from the Flask web layer so it can be
reused by alternative backends (e.g., FastAPI) and future Android integrations.
"""

from __future__ import annotations

import os
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, MutableMapping, Sequence

from cachetools import TTLCache, cached
from dotenv import load_dotenv

from ..evaluator import StockEvaluator
from ..features import StockAnalysisFeatures
from ..analysis import Epic2Analyzer, Epic3TechnicalAnalyzer
from .data_pipeline import (
    CurrencyConverter,
    MultiSourceDataClient,
    SchedulerHooks,
    SQLiteDataStore,
)
from .keys import get_api_key
from .macro import MacroContextService

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

STATIC_DIR = PROJECT_ROOT / "static"

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


def _derive_fundamental_trends(
    advanced_analysis: Optional[Dict[str, Any]],
    stock_info: MutableMapping[str, Any],
) -> Dict[str, Dict[str, Optional[float]]]:
    growth_metrics = (advanced_analysis or {}).get("growth", {}).get("metrics", {}) if advanced_analysis else {}
    revenue_metric = growth_metrics.get("revenue", {}) if isinstance(growth_metrics, dict) else {}
    eps_metric = growth_metrics.get("eps", {}) if isinstance(growth_metrics, dict) else {}
    fcf_metric = growth_metrics.get("fcf", {}) if isinstance(growth_metrics, dict) else {}

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


def _build_opinion_prompt(company_name: str, ticker: str, metrics: Dict[str, Any]) -> str:
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
                model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"), #llama-3.3-70b-versatile
                messages=[
                    {"role": "system", "content": "You are an experienced value investor providing measured analysis."},
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
            model_name = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash-lite") #gemini-2.5-flash-lite
            generation_config = types.GenerationConfig(
                temperature=0.4,
                max_output_tokens=900,
            )
            model = genai.GenerativeModel(model_name, generation_config=generation_config)
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
    fundamentals_trends: Optional[MutableMapping[str, MutableMapping[str, Optional[float]]]] = None,
    *,
    ensure_fresh: bool = False,
) -> Dict[str, Dict]:
    """Retrieve macro context with optional trend alignment overrides."""
    trends = fundamentals_trends or {}
    return MACRO_SERVICE.get_context(fundamentals_trends=trends, ensure_fresh=ensure_fresh)


def generate_flowchart_definition(
    evaluator: StockEvaluator, result: str, path: Any
) -> str:
    """Produce Mermaid definition for flowchart rendering."""

    graph_def = textwrap.dedent(
        """
        flowchart TD
            A([Start Analysis]) --> B{Revenue Growth<br/>≥ 10%?}
            B -->|Yes| C[Valuation Check]
            B -->|No| D[Do Not Buy]
            C -->|P/E < 25| E{ROE<br/>≥ 15%?}
            C -->|Else| F{PEG<br/>&lt; 2?}
            F -->|Yes| E
            F -->|No| D
            E -->|Yes| G{Net Margin<br/>≥ 10%?}
            E -->|No| D
            G -->|Yes| H{Debt/Equity<br/>&lt; 1?}
            G -->|No| D
            H -->|Yes| I{Quick Ratio<br/>≥ 1.5?}
            H -->|No| D
            I -->|Yes| J([BUY])
            I -->|No| K([BUY with Caution])
        """
    ).strip()

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
            link_styles.append(f"linkStyle {link_map[link]} stroke:#198754,stroke-width:4px;")

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
    return "\n".join(script_parts)


class StockAnalysisService:
    """Facade providing a single entry-point for stock analysis workflows."""

    def __init__(self, opinion_api_key: Optional[str] = None) -> None:
        self.opinion_api_key = opinion_api_key

    def analyze(
        self, ticker_symbol: str, include_opinion: bool = True
    ) -> Dict[str, Any]:
        """Run complete analysis for a ticker and return structured payload."""

        stock_info = get_stock_data(ticker_symbol)
        company_name = stock_info.get("longName", ticker_symbol.upper())

        evaluator = StockEvaluator(stock_info)
        verdict, path, active_links = evaluator.evaluate()

        flowchart_def = generate_flowchart_definition(evaluator, verdict, path)

        features_analyzer = StockAnalysisFeatures(
            ticker_symbol,
            stock_info,
            stock_info.get("historicalMetrics"),
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
            price_history = stock_info.get("priceHistory")
            if price_history:
                technical_analyzer = Epic3TechnicalAnalyzer(price_history, ticker=ticker_symbol)
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
            fundamental_trends = _derive_fundamental_trends(advanced_analysis, stock_info)
            macro_context = MACRO_SERVICE.get_context(
                fundamentals_trends=fundamental_trends,
                ensure_fresh=True,
            )
        except Exception as exc:
            macro_context = {"error": str(exc)}

        opinion_report = None
        if include_opinion:
            opinion_report = generate_stock_opinion(
                self.opinion_api_key,
                company_name,
                ticker_symbol,
                evaluator.metrics,
            )

        active_links_list = sorted([[a, b] for (a, b) in active_links])

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
            "metrics": evaluator.metrics,
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
