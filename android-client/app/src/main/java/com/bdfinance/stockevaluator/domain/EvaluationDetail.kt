package com.bdfinance.stockevaluator.domain

data class EvaluationNode(
    val metric: String,
    val value: String,
    val threshold: String,
    val status: String
)

data class RiskAssessment(
    val overallRiskScore: Double?,
    val riskLevel: String?,
    val recommendations: List<String>
)

data class TrendPeriod(
    val period: String,
    val percentReturn: Double?,
    val trendDirection: String?
)

data class TrendAnalysis(
    val periods: List<TrendPeriod>,
    val momentumScore: Double?,
    val trendConsistency: String?
)

data class ComparativeAnalysis(
    val sector: String?,
    val marketCapCategory: String?,
    val valuationVsPeers: String?,
    val growthVsPeers: String?,
    val profitabilityVsPeers: String?
)

data class DividendAnalysis(
    val currentYield: Double?,
    val payoutRatio: Double?,
    val dividendSustainability: String?,
    val yieldAttractiveness: String?
)

data class EvaluationDetail(
    val summary: EvaluationSummary,
    val metrics: Map<String, Double?>?,
    val nodes: List<EvaluationNode>,
    val flowchartDefinition: String?,
    val flowchartHtml: String?,
    val opinionHtml: String?,
    val riskAssessment: RiskAssessment?,
    val trendAnalysis: TrendAnalysis?,
    val comparativeAnalysis: ComparativeAnalysis?,
    val dividendAnalysis: DividendAnalysis?
)
