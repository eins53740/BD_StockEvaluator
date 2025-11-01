# D:/GitHub/BD_Python_AI/BD_Finance/FlowchartStocks/stock-evaluator/features.py
# Enhanced features for stock evaluation
# 20251507 BDLRA

import yfinance as yf
import numpy as np
from typing import Dict, List, Optional


class StockAnalysisFeatures:
    """
    Additional analysis features for comprehensive stock evaluation.
    Provides risk assessment, trend analysis, and comparative metrics.
    """

    def __init__(
        self,
        ticker_symbol: str,
        stock_info: Dict,
        historical_metrics: Optional[List[Dict]] = None,
    ):
        self.ticker = ticker_symbol
        self.info = stock_info
        self.history = historical_metrics or stock_info.get("historicalMetrics") or []
        self.stock = yf.Ticker(ticker_symbol)

    def get_risk_assessment(self) -> Dict:
        """
        Comprehensive risk assessment based on multiple factors.
        Returns risk score and detailed breakdown.
        """
        risk_factors = {
            "volatility_risk": self._assess_volatility_risk(),
            "liquidity_risk": self._assess_liquidity_risk(),
            "financial_risk": self._assess_financial_risk(),
            "market_risk": self._assess_market_risk(),
            "sector_risk": self._assess_sector_risk(),
        }

        # Calculate overall risk score (0-100, higher = riskier)
        weights = {
            "volatility_risk": 0.25,
            "liquidity_risk": 0.15,
            "financial_risk": 0.30,
            "market_risk": 0.20,
            "sector_risk": 0.10,
        }

        overall_risk = sum(
            risk_factors[factor] * weights[factor]
            for factor in risk_factors
            if risk_factors[factor] is not None
        )

        return {
            "overall_risk_score": round(overall_risk, 1),
            "risk_level": self._categorize_risk(overall_risk),
            "risk_factors": risk_factors,
            "recommendations": self._generate_risk_recommendations(risk_factors),
        }

    def get_trend_analysis(self) -> Dict:
        """
        Analyzes price and volume trends over different time periods.
        """
        try:
            # Get historical data for different periods
            periods = ["1mo", "3mo", "6mo", "1y"]
            trends = {}

            for period in periods:
                hist = self.stock.history(period=period)
                if not hist.empty:
                    trends[period] = self._analyze_period_trend(hist)

            return {
                "trends": trends,
                "momentum_score": self._calculate_momentum_score(trends),
                "trend_consistency": self._assess_trend_consistency(trends),
            }

        except Exception as e:
            return {"error": f"Failed to analyze trends: {str(e)}"}

    def get_comparative_analysis(self) -> Dict:
        """
        Compares stock metrics against industry and market averages.
        """
        try:
            sector = self.info.get("sector", "Unknown")
            industry = self.info.get("industry", "Unknown")

            # Get basic comparison metrics
            comparison = {
                "sector": sector,
                "industry": industry,
                "market_cap_category": self._categorize_market_cap(),
                "valuation_vs_peers": self._compare_valuation(),
                "growth_vs_peers": self._compare_growth(),
                "profitability_vs_peers": self._compare_profitability(),
            }

            return comparison

        except Exception as e:
            return {"error": f"Failed to perform comparative analysis: {str(e)}"}

    def get_dividend_analysis(self) -> Dict:
        """
        Analyzes dividend history and sustainability.
        """
        try:
            dividend_yield = self.info.get("dividendYield", 0)
            payout_ratio = self.info.get("payoutRatio", 0)

            # Get dividend history
            dividends = self.stock.dividends

            analysis = {
                "current_yield": dividend_yield,
                "payout_ratio": payout_ratio,
                "dividend_sustainability": self._assess_dividend_sustainability(
                    payout_ratio
                ),
                "dividend_growth": (
                    self._analyze_dividend_growth(dividends)
                    if not dividends.empty
                    else None
                ),
                "yield_attractiveness": self._assess_yield_attractiveness(
                    dividend_yield
                ),
            }

            return analysis

        except Exception as e:
            return {"error": f"Failed to analyze dividends: {str(e)}"}

    # Private helper methods
    def _assess_volatility_risk(self) -> Optional[float]:
        """Assess volatility-based risk (0-100)"""
        try:
            beta = self.info.get("beta")
            if beta is None:
                return None

            # Convert beta to risk score
            if beta < 0.5:
                return 10  # Very low risk
            elif beta < 1.0:
                return 30  # Low risk
            elif beta < 1.5:
                return 60  # Moderate risk
            else:
                return 90  # High risk

        except Exception:
            return None

    def _assess_liquidity_risk(self) -> Optional[float]:
        """Assess liquidity risk based on trading volume"""
        try:
            avg_volume = self.info.get("averageVolume", 0)
            market_cap = self.info.get("marketCap", 0)

            if avg_volume == 0 or market_cap == 0:
                return None

            # Calculate liquidity ratio
            liquidity_ratio = avg_volume * self.info.get("currentPrice", 1) / market_cap

            if liquidity_ratio > 0.01:
                return 10  # High liquidity, low risk
            elif liquidity_ratio > 0.005:
                return 30  # Good liquidity
            elif liquidity_ratio > 0.001:
                return 60  # Moderate liquidity
            else:
                return 90  # Low liquidity, high risk

        except Exception:
            return None

    def _assess_financial_risk(self) -> Optional[float]:
        """Assess financial health risk"""
        try:
            debt_to_equity = self.info.get("debtToEquity", 0)
            current_ratio = self.info.get("currentRatio", 0)
            roe = self.info.get("returnOnEquity", 0)

            risk_score = 0
            factors = 0

            # Debt to equity risk
            if debt_to_equity is not None:
                if debt_to_equity > 100:
                    risk_score += 80
                elif debt_to_equity > 50:
                    risk_score += 50
                elif debt_to_equity > 25:
                    risk_score += 25
                else:
                    risk_score += 10
                factors += 1

            # Current ratio risk
            if current_ratio is not None:
                if current_ratio < 1.0:
                    risk_score += 70
                elif current_ratio < 1.5:
                    risk_score += 40
                else:
                    risk_score += 15
                factors += 1

            # ROE risk
            if roe is not None:
                if roe < 0:
                    risk_score += 90
                elif roe < 0.05:
                    risk_score += 60
                elif roe < 0.10:
                    risk_score += 30
                else:
                    risk_score += 10
                factors += 1

            return risk_score / factors if factors > 0 else None

        except Exception:
            return None

    def _assess_market_risk(self) -> Optional[float]:
        """Assess market-related risk"""
        try:
            # Simple market risk based on market cap and sector
            market_cap = self.info.get("marketCap", 0)

            if market_cap > 200_000_000_000:  # Large cap
                return 20
            elif market_cap > 10_000_000_000:  # Mid cap
                return 40
            elif market_cap > 2_000_000_000:  # Small cap
                return 60
            else:  # Micro cap
                return 80

        except Exception:
            return 50  # Default moderate risk

    def _assess_sector_risk(self) -> Optional[float]:
        """Assess sector-specific risk"""
        try:
            sector = self.info.get("sector", "").lower()

            # Sector risk mapping (simplified)
            high_risk_sectors = ["technology", "biotechnology", "energy"]
            moderate_risk_sectors = [
                "consumer discretionary",
                "industrials",
                "materials",
            ]
            low_risk_sectors = ["utilities", "consumer staples", "healthcare"]

            if any(s in sector for s in high_risk_sectors):
                return 70
            elif any(s in sector for s in moderate_risk_sectors):
                return 40
            elif any(s in sector for s in low_risk_sectors):
                return 20
            else:
                return 50  # Default

        except Exception:
            return 50

    def _categorize_risk(self, risk_score: float) -> str:
        """Categorize overall risk level"""
        if risk_score < 25:
            return "Low Risk"
        elif risk_score < 50:
            return "Moderate Risk"
        elif risk_score < 75:
            return "High Risk"
        else:
            return "Very High Risk"

    def _generate_risk_recommendations(self, risk_factors: Dict) -> List[str]:
        """Generate risk-based recommendations"""
        recommendations = []

        def exceeds(value: Optional[float], threshold: float) -> bool:
            return value is not None and value > threshold

        if exceeds(risk_factors.get("volatility_risk"), 70):
            recommendations.append(
                "High volatility detected - consider position sizing carefully"
            )

        if exceeds(risk_factors.get("liquidity_risk"), 60):
            recommendations.append(
                "Low liquidity - may be difficult to exit position quickly"
            )

        if exceeds(risk_factors.get("financial_risk"), 60):
            recommendations.append(
                "Financial health concerns - monitor debt levels and profitability"
            )

        if not recommendations:
            recommendations.append(
                "Risk profile appears manageable for diversified portfolio"
            )

        return recommendations

    def _analyze_period_trend(self, hist_data) -> Dict:
        """Analyze trend for a specific period"""
        if hist_data.empty:
            return {}

        start_price = hist_data["Close"].iloc[0]
        end_price = hist_data["Close"].iloc[-1]
        high_price = hist_data["High"].max()
        low_price = hist_data["Low"].min()

        return {
            "return": (end_price - start_price) / start_price,
            "volatility": np.nanstd(hist_data["Close"].pct_change()),
            "max_drawdown": (low_price - high_price) / high_price,
            "trend_direction": "up" if end_price > start_price else "down",
        }

    def _calculate_momentum_score(self, trends: Dict) -> float:
        """Calculate momentum score based on multiple timeframes"""
        if not trends:
            return 0

        score = 0
        weights = {"1mo": 0.4, "3mo": 0.3, "6mo": 0.2, "1y": 0.1}

        for period, weight in weights.items():
            if period in trends and "return" in trends[period]:
                period_return = trends[period]["return"]
                score += period_return * weight * 100

        return round(score, 2)

    def _assess_trend_consistency(self, trends: Dict) -> str:
        """Assess consistency of trends across timeframes"""
        if not trends:
            return "Unknown"

        directions = [
            trends[p].get("trend_direction")
            for p in trends
            if "trend_direction" in trends[p]
        ]

        if not directions:
            return "Unknown"

        up_count = directions.count("up")
        consistency = up_count / len(directions)

        if consistency >= 0.75:
            return "Consistently Bullish"
        elif consistency <= 0.25:
            return "Consistently Bearish"
        else:
            return "Mixed Signals"

    def _categorize_market_cap(self) -> str:
        """Categorize company by market cap"""
        market_cap = self.info.get("marketCap", 0)

        if market_cap > 200_000_000_000:
            return "Mega Cap"
        elif market_cap > 10_000_000_000:
            return "Large Cap"
        elif market_cap > 2_000_000_000:
            return "Mid Cap"
        elif market_cap > 300_000_000:
            return "Small Cap"
        else:
            return "Micro Cap"

    def _compare_valuation(self) -> str:
        """Compare valuation metrics to typical ranges"""
        pe = self.info.get("trailingPE")
        if pe is None:
            return "Unable to assess"

        if pe < 15:
            return "Undervalued"
        elif pe < 25:
            return "Fairly Valued"
        else:
            return "Potentially Overvalued"

    def _compare_growth(self) -> str:
        """Compare growth metrics"""
        revenue_growth = self.info.get("revenueGrowth", 0)

        if revenue_growth > 0.20:
            return "High Growth"
        elif revenue_growth > 0.10:
            return "Moderate Growth"
        elif revenue_growth > 0:
            return "Low Growth"
        else:
            return "Declining"

    def _compare_profitability(self) -> str:
        """Compare profitability metrics"""
        roe = self.info.get("returnOnEquity", 0)

        if roe > 0.20:
            return "Highly Profitable"
        elif roe > 0.15:
            return "Good Profitability"
        elif roe > 0.10:
            return "Moderate Profitability"
        else:
            return "Low Profitability"

    def _assess_dividend_sustainability(self, payout_ratio: float) -> str:
        """Assess dividend sustainability"""
        if payout_ratio is None or payout_ratio == 0:
            return "No Dividend"

        if payout_ratio < 0.4:
            return "Very Sustainable"
        elif payout_ratio < 0.6:
            return "Sustainable"
        elif payout_ratio < 0.8:
            return "Moderately Sustainable"
        else:
            return "At Risk"

    def _analyze_dividend_growth(self, dividends) -> Dict:
        """Analyze dividend growth pattern"""
        if len(dividends) < 2:
            return {"growth_rate": None, "consistency": "Insufficient Data"}

        # Calculate year-over-year growth
        annual_dividends = dividends.resample("YE").sum()
        if len(annual_dividends) < 2:
            return {"growth_rate": None, "consistency": "Insufficient Data"}

        growth_rates = annual_dividends.pct_change().dropna()
        if growth_rates.empty:
            return {"growth_rate": None, "consistency": "Insufficient Data"}
        avg_growth = growth_rates.mean()
        return {
            "growth_rate": avg_growth,
            "consistency": (
                "Consistent" if np.nanstd(growth_rates) < 0.1 else "Variable"
            ),
        }

    def _assess_yield_attractiveness(self, dividend_yield: float) -> str:
        """Assess dividend yield attractiveness"""
        if dividend_yield is None or dividend_yield == 0:
            return "No Dividend"

        if dividend_yield > 0.06:
            return "High Yield"
        elif dividend_yield > 0.03:
            return "Moderate Yield"
        elif dividend_yield > 0.01:
            return "Low Yield"
        else:
            return "Very Low Yield"
