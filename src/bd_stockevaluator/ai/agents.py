"""
AI Agents for Epic 8 - AI & Automation Layer.

Implements:
- F8.1: Financial Summary Agent with 1-10 rating rationale
- F8.2: Market Commentary Bot for macro/sentiment summaries
"""

from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
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
class FinancialRating:
    """Structured rating output from Financial Summary Agent."""

    overall_score: float  # 1-10
    buy_rating: float  # 1-10
    quality_rating: float  # 1-10
    value_rating: float  # 1-10
    growth_rating: float  # 1-10
    financial_health_rating: float  # 1-10
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    recommendation: str  # "Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"
    confidence: str  # "High", "Medium", "Low"
    rationale: str


@dataclass
class MarketCommentary:
    """Market commentary output from Bot."""

    title: str
    summary: str
    macro_outlook: str
    sentiment: str  # "Bullish", "Neutral", "Bearish"
    key_risks: List[str]
    opportunities: List[str]
    generated_at: str


class FinancialSummaryAgent:
    """
    F8.1: AI agent that analyzes expanded metrics and provides 1-10 ratings.

    Uses Groq (primary) or Gemini (fallback) to generate structured financial
    ratings with detailed rationale.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize agent with optional API key."""
        self.api_key = api_key

    def _build_prompt(
        self,
        ticker: str,
        company_name: str,
        analysis: Dict[str, Any],
    ) -> str:
        """Build comprehensive prompt for financial rating."""

        metrics = analysis.get("metrics", {})
        risk = analysis.get("risk_assessment", {})
        trend = analysis.get("trend_analysis", {})
        comparative = analysis.get("comparative_analysis", {})
        valuation = analysis.get("valuation_scorecard", {})
        profitability = analysis.get("profitability_snapshot", {})
        growth = analysis.get("growth_trends", {})

        prompt = textwrap.dedent(
            f"""
            You are an expert financial analyst providing structured investment ratings.

            Analyze {company_name} ({ticker}) and provide ratings on a 1-10 scale (10 is best).

            ## Available Data:

            ### Basic Metrics:
            - Revenue Growth: {metrics.get('rev_growth', 'N/A')}
            - P/E Ratio: {metrics.get('pe', 'N/A')}
            - ROE: {metrics.get('roe', 'N/A')}
            - Net Margin: {metrics.get('margin', 'N/A')}
            - Debt/Equity: {metrics.get('de', 'N/A')}
            - Quick Ratio: {metrics.get('qr', 'N/A')}

            ### Risk Assessment:
            - Risk Score: {risk.get('risk_score', 'N/A')}%
            - Risk Level: {risk.get('risk_level', 'N/A')}

            ### Trend Analysis:
            - Momentum Score: {trend.get('momentum_score', 'N/A')}
            - Trend Consistency: {trend.get('trend_consistency', 'N/A')}

            ### Comparative:
            - Market Cap Category: {comparative.get('market_cap_category', 'N/A')}
            - Valuation Assessment: {comparative.get('valuation_assessment', 'N/A')}
            - Growth Profile: {comparative.get('growth_profile', 'N/A')}
            - Profitability Assessment: {comparative.get('profitability_assessment', 'N/A')}

            ### Valuation Scorecard:
            {self._format_scorecard(valuation)}

            ### Profitability:
            {self._format_scorecard(profitability)}

            ### Growth Trends:
            {self._format_scorecard(growth)}

            ## Required Output Format (JSON):

            {{
                "overall_score": <1-10>,
                "buy_rating": <1-10>,
                "quality_rating": <1-10>,
                "value_rating": <1-10>,
                "growth_rating": <1-10>,
                "financial_health_rating": <1-10>,
                "summary": "<2-3 sentence overview>",
                "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
                "weaknesses": ["<weakness 1>", "<weakness 2>", "<weakness 3>"],
                "recommendation": "<Strong Buy|Buy|Hold|Sell|Strong Sell>",
                "confidence": "<High|Medium|Low>",
                "rationale": "<Detailed 2-3 paragraph explanation of ratings>"
            }}

            Guidelines:
            - overall_score: Weighted average reflecting investment attractiveness
            - buy_rating: Buy recommendation strength (10=strong buy, 1=strong sell)
            - quality_rating: Business quality and moat strength
            - value_rating: Valuation attractiveness (10=very undervalued)
            - growth_rating: Growth prospects and momentum
            - financial_health_rating: Balance sheet strength and stability
            - Be objective and data-driven
            - Highlight 3 key strengths and 3 key weaknesses
            - Provide clear rationale for each rating

            Return ONLY the JSON object, no additional text.
            """
        )

        return prompt

    def _format_scorecard(self, scorecard: Optional[Dict[str, Any]]) -> str:
        """Format scorecard data for prompt."""
        if not scorecard:
            return "Not available"

        lines = []
        for key, value in scorecard.items():
            if isinstance(value, dict):
                score = value.get("score") or value.get("overall_score")
                if score is not None:
                    lines.append(f"- {key}: {score}")
            elif isinstance(value, (int, float)):
                lines.append(f"- {key}: {value}")

        return "\n".join(lines) if lines else "Not available"

    def _call_groq(self, prompt: str) -> Optional[str]:
        """Call Groq API for rating generation."""
        if not _GroqClient:
            return None

        groq_key = self.api_key or get_api_key("api_key_groq")
        if not groq_key:
            return None

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
                        "content": "You are an expert financial analyst. Return only valid JSON.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1500,
            )

            content = response.choices[0].message.content if response.choices else None
            return content

        except Exception as exc:
            print(f"Groq API call failed: {exc}")
            return None

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Call Gemini API for rating generation (fallback)."""
        if not genai:
            return None

        gemini_key = get_api_key("api_key_gemini")
        if not gemini_key:
            return None

        try:
            genai.configure(api_key=gemini_key)
            model_name = os.getenv("GEMINI_MODEL", "models/gemini-2.5-flash-lite")
            generation_config = types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=1500,
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
            print(f"Gemini API call failed: {exc}")
            return None

    def _parse_rating_response(self, response: str) -> Optional[FinancialRating]:
        """Parse JSON response into FinancialRating object."""
        import json

        try:
            # Extract JSON from response (handle markdown code blocks)
            response = response.strip()
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()

            data = json.loads(response)

            return FinancialRating(
                overall_score=float(data.get("overall_score", 5.0)),
                buy_rating=float(data.get("buy_rating", 5.0)),
                quality_rating=float(data.get("quality_rating", 5.0)),
                value_rating=float(data.get("value_rating", 5.0)),
                growth_rating=float(data.get("growth_rating", 5.0)),
                financial_health_rating=float(data.get("financial_health_rating", 5.0)),
                summary=data.get("summary", ""),
                strengths=data.get("strengths", []),
                weaknesses=data.get("weaknesses", []),
                recommendation=data.get("recommendation", "Hold"),
                confidence=data.get("confidence", "Medium"),
                rationale=data.get("rationale", ""),
            )

        except Exception as exc:
            print(f"Failed to parse rating response: {exc}")
            return None

    def generate_rating(
        self,
        ticker: str,
        company_name: str,
        analysis: Dict[str, Any],
    ) -> Optional[FinancialRating]:
        """
        Generate structured financial rating with 1-10 scores.

        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            analysis: Complete analysis payload from StockAnalysisService

        Returns:
            FinancialRating object or None if generation fails
        """
        prompt = self._build_prompt(ticker, company_name, analysis)

        # Try Groq first, then Gemini
        response = self._call_groq(prompt)
        if not response:
            response = self._call_gemini(prompt)

        if not response:
            return None

        return self._parse_rating_response(response)


class MarketCommentaryBot:
    """
    F8.2: AI bot that generates daily/weekly macro and sentiment summaries.

    Analyzes macro context, market sentiment, and provides outlook commentary.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize bot with optional API key."""
        self.api_key = api_key

    def _build_commentary_prompt(
        self,
        macro_context: Optional[Dict[str, Any]],
        period: str = "daily",
    ) -> str:
        """Build prompt for market commentary."""

        macro_str = self._format_macro_context(macro_context)

        prompt = textwrap.dedent(
            f"""
            You are a market analyst providing {period} market commentary.

            ## Macro Context:
            {macro_str}

            ## Required Output Format (JSON):

            {{
                "title": "<Catchy {period} market title>",
                "summary": "<2-3 sentence market summary>",
                "macro_outlook": "<2-3 paragraphs on macro conditions>",
                "sentiment": "<Bullish|Neutral|Bearish>",
                "key_risks": ["<risk 1>", "<risk 2>", "<risk 3>"],
                "opportunities": ["<opportunity 1>", "<opportunity 2>", "<opportunity 3>"]
            }}

            Guidelines:
            - Be concise and actionable
            - Focus on key macro drivers
            - Identify top risks and opportunities
            - Provide clear sentiment assessment
            - Use data-driven insights

            Return ONLY the JSON object, no additional text.
            """
        )

        return prompt

    def _format_macro_context(self, macro_context: Optional[Dict[str, Any]]) -> str:
        """Format macro context for prompt."""
        if not macro_context:
            return "No macro data available"

        lines = []
        dashboard = macro_context.get("dashboard", {})

        for indicator, data in dashboard.items():
            if isinstance(data, dict):
                latest = data.get("latest", {})
                value = latest.get("value")
                trend = latest.get("trend")
                if value is not None:
                    lines.append(f"- {indicator}: {value} ({trend})")

        return "\n".join(lines) if lines else "No macro data available"

    def generate_commentary(
        self,
        macro_context: Optional[Dict[str, Any]] = None,
        period: str = "daily",
    ) -> Optional[MarketCommentary]:
        """
        Generate market commentary.

        Args:
            macro_context: Macro context from MacroContextService
            period: "daily" or "weekly"

        Returns:
            MarketCommentary object or None if generation fails
        """
        prompt = self._build_commentary_prompt(macro_context, period)

        # Use same Groq/Gemini pattern
        agent = FinancialSummaryAgent(self.api_key)
        response = agent._call_groq(prompt)
        if not response:
            response = agent._call_gemini(prompt)

        if not response:
            return None

        try:
            import json

            # Extract JSON
            response = response.strip()
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                response = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                response = response[start:end].strip()

            data = json.loads(response)

            return MarketCommentary(
                title=data.get("title", "Market Update"),
                summary=data.get("summary", ""),
                macro_outlook=data.get("macro_outlook", ""),
                sentiment=data.get("sentiment", "Neutral"),
                key_risks=data.get("key_risks", []),
                opportunities=data.get("opportunities", []),
                generated_at=datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            )

        except Exception as exc:
            print(f"Failed to parse commentary response: {exc}")
            return None
