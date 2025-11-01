"""
Natural-Language Screener (Epic 8 - F8.3).

Handles queries like "find cheap tech stocks with ROE > 15% and low debt."
"""

from __future__ import annotations

import os
import re
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..core.keys import get_api_key

# Lazy imports for AI providers
try:
    from groq import Groq as _GroqClient
except ImportError:
    _GroqClient = None

try:
    import google.generativeai as genai
    from google.generativeai import types
except ImportError:
    genai = None
    types = None


@dataclass
class ScreenerCriteria:
    """Parsed screening criteria from natural language query."""

    sectors: List[str]
    min_roe: Optional[float] = None
    max_pe: Optional[float] = None
    min_revenue_growth: Optional[float] = None
    max_debt_to_equity: Optional[float] = None
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    min_dividend_yield: Optional[float] = None
    valuation: Optional[str] = None  # "cheap", "undervalued", "fair", "expensive"
    growth_profile: Optional[str] = None  # "high", "moderate", "low"
    quality: Optional[str] = None  # "high", "medium", "low"
    raw_query: str = ""


class NaturalLanguageScreener:
    """
    F8.3: AI-powered stock screener that understands natural language queries.

    Examples:
    - "find cheap tech stocks with ROE > 15% and low debt"
    - "show me large-cap healthcare companies with high dividends"
    - "quality growth stocks under $50"
    """

    # Sector mapping
    SECTOR_KEYWORDS = {
        "tech": ["Technology", "Information Technology", "Software"],
        "healthcare": ["Healthcare", "Health Care", "Biotechnology"],
        "finance": ["Financials", "Financial Services", "Banking"],
        "consumer": ["Consumer", "Consumer Discretionary", "Consumer Staples"],
        "energy": ["Energy", "Oil & Gas"],
        "industrial": ["Industrials", "Industrial"],
        "materials": ["Materials", "Basic Materials"],
        "utilities": ["Utilities"],
        "real estate": ["Real Estate", "REIT"],
        "communication": ["Communication Services", "Telecommunications"],
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize screener with optional API key."""
        self.api_key = api_key

    def _build_parsing_prompt(self, query: str) -> str:
        """Build prompt to parse natural language into structured criteria."""

        prompt = textwrap.dedent(
            f"""
            You are a financial screener assistant. Parse the following stock screening query
            into structured JSON criteria.

            Query: "{query}"

            Extract these fields (set to null if not mentioned):

            {{
                "sectors": ["<sector1>", "<sector2>"],  // Tech, Healthcare, Finance, etc.
                "min_roe": <float or null>,  // Minimum ROE as decimal (e.g., 0.15 for 15%)
                "max_pe": <float or null>,  // Maximum P/E ratio
                "min_revenue_growth": <float or null>,  // Minimum revenue growth as decimal
                "max_debt_to_equity": <float or null>,  // Maximum debt/equity ratio
                "min_market_cap": <float or null>,  // Minimum market cap in billions
                "max_market_cap": <float or null>,  // Maximum market cap in billions
                "min_dividend_yield": <float or null>,  // Minimum dividend yield as decimal
                "valuation": "<cheap|undervalued|fair|expensive|null>",
                "growth_profile": "<high|moderate|low|null>",
                "quality": "<high|medium|low|null>"
            }}

            Interpretation guidelines:
            - "cheap", "undervalued", "good value" → valuation: "cheap"
            - "expensive", "overvalued" → valuation: "expensive"
            - "high ROE", "profitable" → quality: "high"
            - "growth", "fast growing" → growth_profile: "high"
            - "low debt", "strong balance sheet" → max_debt_to_equity: 1.0
            - "large cap" → min_market_cap: 10
            - "mid cap" → min_market_cap: 2, max_market_cap: 10
            - "small cap" → max_market_cap: 2
            - Percentages should be converted to decimals (15% → 0.15)

            Return ONLY the JSON object, no additional text.
            """
        )

        return prompt

    def _call_ai(self, prompt: str) -> Optional[str]:
        """Call AI provider (Groq or Gemini)."""
        # Try Groq first
        groq_key = self.api_key or get_api_key("api_key_groq")
        if _GroqClient and groq_key:
            try:
                client_kwargs: Dict[str, Any] = {"api_key": groq_key}
                base_url = os.getenv("GROQ_API_BASE", "").strip()
                if base_url:
                    client_kwargs["base_url"] = base_url

                client = _GroqClient(**client_kwargs)
                response = client.chat.completions.create(
                    model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a financial screener. Return only valid JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=800,
                )

                return response.choices[0].message.content if response.choices else None

            except Exception as exc:
                print(f"Groq call failed: {exc}")

        # Fallback to Gemini
        gemini_key = get_api_key("api_key_gemini")
        if genai and gemini_key:
            try:
                genai.configure(api_key=gemini_key)
                model_name = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash-lite")
                generation_config = types.GenerationConfig(
                    temperature=0.2,
                    max_output_tokens=800,
                )
                model = genai.GenerativeModel(model_name, generation_config=generation_config)
                response = model.generate_content(prompt)

                text = ""
                if hasattr(response, "text"):
                    text = response.text
                elif hasattr(response, "candidates") and response.candidates:
                    text = response.candidates[0].content.parts[0].text

                return text

            except Exception as exc:
                print(f"Gemini call failed: {exc}")

        return None

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON from AI response."""
        import json

        try:
            # Extract JSON from response
            response = response.strip()
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()

            return json.loads(response)

        except Exception as exc:
            print(f"Failed to parse JSON response: {exc}")
            return None

    def parse_query(self, query: str) -> Optional[ScreenerCriteria]:
        """
        Parse natural language query into structured screening criteria.

        Args:
            query: Natural language stock screening query

        Returns:
            ScreenerCriteria object or None if parsing fails

        Example:
            >>> screener = NaturalLanguageScreener()
            >>> criteria = screener.parse_query("cheap tech stocks with ROE > 15%")
            >>> criteria.sectors
            ['Technology']
            >>> criteria.min_roe
            0.15
        """
        prompt = self._build_parsing_prompt(query)
        response = self._call_ai(prompt)

        if not response:
            return None

        data = self._parse_json_response(response)
        if not data:
            return None

        try:
            return ScreenerCriteria(
                sectors=data.get("sectors", []),
                min_roe=data.get("min_roe"),
                max_pe=data.get("max_pe"),
                min_revenue_growth=data.get("min_revenue_growth"),
                max_debt_to_equity=data.get("max_debt_to_equity"),
                min_market_cap=data.get("min_market_cap"),
                max_market_cap=data.get("max_market_cap"),
                min_dividend_yield=data.get("min_dividend_yield"),
                valuation=data.get("valuation"),
                growth_profile=data.get("growth_profile"),
                quality=data.get("quality"),
                raw_query=query,
            )

        except Exception as exc:
            print(f"Failed to create ScreenerCriteria: {exc}")
            return None

    def screen_stocks(
        self,
        criteria: ScreenerCriteria,
        stock_universe: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Apply screening criteria to a universe of stocks.

        Args:
            criteria: Parsed screening criteria
            stock_universe: List of stock analysis results

        Returns:
            Filtered list of stocks matching criteria
        """
        results = []

        for stock in stock_universe:
            if self._matches_criteria(stock, criteria):
                results.append(stock)

        # Sort by overall score (if available)
        results.sort(
            key=lambda s: s.get("risk_assessment", {}).get("risk_score", 100),
            reverse=False,
        )

        return results

    def _matches_criteria(
        self,
        stock: Dict[str, Any],
        criteria: ScreenerCriteria,
    ) -> bool:
        """Check if a stock matches the screening criteria."""

        # Sector filter
        if criteria.sectors:
            sector = stock.get("stock_info", {}).get("sector", "")
            if not any(
                keyword.lower() in sector.lower()
                for s in criteria.sectors
                for keyword in self.SECTOR_KEYWORDS.get(s.lower(), [s])
            ):
                return False

        metrics = stock.get("metrics", {})
        comparative = stock.get("comparative_analysis", {})

        # ROE filter
        if criteria.min_roe is not None:
            roe = metrics.get("roe")
            if roe is None or roe < criteria.min_roe:
                return False

        # P/E filter
        if criteria.max_pe is not None:
            pe = metrics.get("pe")
            if pe is None or pe > criteria.max_pe:
                return False

        # Revenue growth filter
        if criteria.min_revenue_growth is not None:
            rev_growth = metrics.get("rev_growth")
            if rev_growth is None or rev_growth < criteria.min_revenue_growth:
                return False

        # Debt filter
        if criteria.max_debt_to_equity is not None:
            de = metrics.get("de")
            if de is None or de > criteria.max_debt_to_equity:
                return False

        # Market cap filters
        market_cap_billions = stock.get("stock_info", {}).get("marketCap")
        if market_cap_billions:
            market_cap_billions = market_cap_billions / 1_000_000_000

            if criteria.min_market_cap is not None:
                if market_cap_billions < criteria.min_market_cap:
                    return False

            if criteria.max_market_cap is not None:
                if market_cap_billions > criteria.max_market_cap:
                    return False

        # Dividend yield filter
        if criteria.min_dividend_yield is not None:
            dividend_yield = stock.get("dividend_analysis", {}).get("current_yield")
            if dividend_yield is None or dividend_yield < criteria.min_dividend_yield:
                return False

        # Valuation filter
        if criteria.valuation:
            valuation_assessment = comparative.get("valuation_assessment", "").lower()
            if criteria.valuation == "cheap" and "under" not in valuation_assessment:
                return False
            elif criteria.valuation == "expensive" and "over" not in valuation_assessment:
                return False

        # Growth filter
        if criteria.growth_profile:
            growth_profile = comparative.get("growth_profile", "").lower()
            if criteria.growth_profile.lower() not in growth_profile:
                return False

        # Quality filter (based on risk score - lower is better)
        if criteria.quality:
            risk_score = stock.get("risk_assessment", {}).get("risk_score", 50)
            if criteria.quality == "high" and risk_score > 40:
                return False
            elif criteria.quality == "medium" and (risk_score < 40 or risk_score > 70):
                return False
            elif criteria.quality == "low" and risk_score < 70:
                return False

        return True
