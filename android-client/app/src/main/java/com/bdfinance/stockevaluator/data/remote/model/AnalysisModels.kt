package com.bdfinance.stockevaluator.data.remote.model

import com.squareup.moshi.Json

data class RiskAssessmentDto(
    @Json(name = "overall_risk_score") val overallRiskScore: Double? = null,
    @Json(name = "risk_level") val riskLevel: String? = null,
    @Json(name = "risk_factors") val riskFactors: Map<String, Double?>? = null,
    val recommendations: List<String>? = null
)

data class TrendPeriodDto(
    @Json(name = "return") val periodReturn: Double? = null,
    @Json(name = "trend_direction") val trendDirection: String? = null
)

data class TrendAnalysisDto(
    val trends: Map<String, TrendPeriodDto>? = null,
    @Json(name = "momentum_score") val momentumScore: Double? = null,
    @Json(name = "trend_consistency") val trendConsistency: String? = null
)

data class ComparativeAnalysisDto(
    val sector: String? = null,
    @Json(name = "market_cap_category") val marketCapCategory: String? = null,
    @Json(name = "valuation_vs_peers") val valuationVsPeers: String? = null,
    @Json(name = "growth_vs_peers") val growthVsPeers: String? = null,
    @Json(name = "profitability_vs_peers") val profitabilityVsPeers: String? = null
)

data class DividendAnalysisDto(
    @Json(name = "current_yield") val currentYield: Double? = null,
    @Json(name = "payout_ratio") val payoutRatio: Double? = null,
    @Json(name = "dividend_sustainability") val dividendSustainability: String? = null,
    @Json(name = "dividend_growth") val dividendGrowth: Map<String, Any?>? = null,
    @Json(name = "yield_attractiveness") val yieldAttractiveness: String? = null
)
