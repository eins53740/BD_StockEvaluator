package com.bdfinance.stockevaluator.data.remote.model

import com.squareup.moshi.Json

data class EvaluateRequest(
    val ticker: String,
    @Json(name = "include_opinion") val includeOpinion: Boolean = true
)

data class EvaluationStepDto(
    val metric: String,
    val value: Double?,
    val threshold: Any?,
    val status: String
)

data class EvaluationResponse(
    val ticker: String,
    @Json(name = "company_name") val companyName: String,
    val result: String,
    @Json(name = "generated_at") val generatedAt: String,
    val path: List<EvaluationStepDto> = emptyList(),
    @Json(name = "active_links") val activeLinks: List<List<String>> = emptyList(),
    @Json(name = "flowchart_definition") val flowchartDefinition: String? = null,
    @Json(name = "opinion_report") val opinionReport: String? = null,
    val metrics: Map<String, Double?>? = null,
    @Json(name = "risk_assessment") val riskAssessment: RiskAssessmentDto? = null,
    @Json(name = "trend_analysis") val trendAnalysis: TrendAnalysisDto? = null,
    @Json(name = "comparative_analysis") val comparativeAnalysis: ComparativeAnalysisDto? = null,
    @Json(name = "dividend_analysis") val dividendAnalysis: DividendAnalysisDto? = null
)
