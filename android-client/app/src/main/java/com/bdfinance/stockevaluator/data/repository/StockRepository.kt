package com.bdfinance.stockevaluator.data.repository

import com.bdfinance.stockevaluator.data.local.EvaluationDao
import com.bdfinance.stockevaluator.data.local.EvaluationEntity
import com.bdfinance.stockevaluator.data.remote.StockApi
import com.bdfinance.stockevaluator.data.remote.model.EvaluateRequest
import com.bdfinance.stockevaluator.data.remote.model.EvaluationResponse
import com.bdfinance.stockevaluator.data.remote.model.EvaluationStepDto
import com.bdfinance.stockevaluator.data.remote.model.RiskAssessmentDto
import com.bdfinance.stockevaluator.data.remote.model.TrendAnalysisDto
import com.bdfinance.stockevaluator.data.remote.model.ComparativeAnalysisDto
import com.bdfinance.stockevaluator.data.remote.model.DividendAnalysisDto
import com.bdfinance.stockevaluator.domain.ComparativeAnalysis
import com.bdfinance.stockevaluator.domain.DividendAnalysis
import com.bdfinance.stockevaluator.domain.EvaluationDetail
import com.bdfinance.stockevaluator.domain.EvaluationNode
import com.bdfinance.stockevaluator.domain.EvaluationSummary
import com.bdfinance.stockevaluator.domain.RiskAssessment
import com.bdfinance.stockevaluator.domain.TrendAnalysis
import com.bdfinance.stockevaluator.domain.TrendPeriod
import com.bdfinance.stockevaluator.util.flowchartHtml
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

@Singleton
class StockRepository @Inject constructor(
    private val api: StockApi,
    private val evaluationDao: EvaluationDao
) {

    fun observeHistory(): Flow<List<EvaluationSummary>> =
        evaluationDao.observeEvaluations().map { list -> list.map { it.toDomain() } }

    suspend fun evaluateTicker(ticker: String): EvaluationDetail {
        val response = api.evaluate(EvaluateRequest(ticker = ticker))
        val summary = response.toSummary()
        evaluationDao.upsert(EvaluationEntity.fromDomain(summary))
        evaluationDao.pruneTo(limit = 20)
        return response.toDetail(summary)
    }
}

private fun EvaluationResponse.toSummary(): EvaluationSummary =
    EvaluationSummary(
        ticker = ticker,
        companyName = companyName,
        result = result,
        generatedAt = generatedAt
    )

private fun EvaluationResponse.toDetail(summary: EvaluationSummary): EvaluationDetail =
    EvaluationDetail(
        summary = summary,
        metrics = metrics,
        nodes = path.map { it.toDomainNode() },
        flowchartDefinition = flowchartDefinition,
        flowchartHtml = flowchartHtml(flowchartDefinition),
        opinionHtml = opinionReport,
        riskAssessment = riskAssessment?.toDomain(),
        trendAnalysis = trendAnalysis?.toDomain(),
        comparativeAnalysis = comparativeAnalysis?.toDomain(),
        dividendAnalysis = dividendAnalysis?.toDomain()
    )

private fun EvaluationStepDto.toDomainNode(): EvaluationNode =
    EvaluationNode(
        metric = metric,
        value = value?.let { formatNumber(it) } ?: "n/a",
        threshold = threshold.toReadable(),
        status = status
    )

private fun RiskAssessmentDto.toDomain(): RiskAssessment =
    RiskAssessment(
        overallRiskScore = overallRiskScore,
        riskLevel = riskLevel,
        recommendations = recommendations ?: emptyList()
    )

private fun TrendAnalysisDto.toDomain(): TrendAnalysis =
    TrendAnalysis(
        periods = trends?.entries?.map { (period, data) ->
            TrendPeriod(
                period = period,
                percentReturn = data.periodReturn,
                trendDirection = data.trendDirection
            )
        } ?: emptyList(),
        momentumScore = momentumScore,
        trendConsistency = trendConsistency
    )

private fun ComparativeAnalysisDto.toDomain(): ComparativeAnalysis =
    ComparativeAnalysis(
        sector = sector,
        marketCapCategory = marketCapCategory,
        valuationVsPeers = valuationVsPeers,
        growthVsPeers = growthVsPeers,
        profitabilityVsPeers = profitabilityVsPeers
    )

private fun DividendAnalysisDto.toDomain(): DividendAnalysis =
    DividendAnalysis(
        currentYield = currentYield,
        payoutRatio = payoutRatio,
        dividendSustainability = dividendSustainability,
        yieldAttractiveness = yieldAttractiveness
    )

private fun Any?.toReadable(): String = when (this) {
    null -> "n/a"
    is Number -> formatNumber(this.toDouble())
    is String -> this
    is Boolean -> toString()
    else -> toString()
}

private fun formatNumber(value: Double): String =
    if (kotlin.math.abs(value) >= 1.0) String.format("%.2f", value) else String.format("%.4f", value)
