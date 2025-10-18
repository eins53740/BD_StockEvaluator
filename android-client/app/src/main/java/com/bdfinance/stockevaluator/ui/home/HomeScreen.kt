package com.bdfinance.stockevaluator.ui.home

import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.hilt.navigation.compose.hiltViewModel
import com.bdfinance.stockevaluator.domain.ComparativeAnalysis
import com.bdfinance.stockevaluator.domain.DividendAnalysis
import com.bdfinance.stockevaluator.domain.EvaluationDetail
import com.bdfinance.stockevaluator.domain.EvaluationNode
import com.bdfinance.stockevaluator.domain.EvaluationSummary
import com.bdfinance.stockevaluator.domain.RiskAssessment
import com.bdfinance.stockevaluator.domain.TrendAnalysis
import com.bdfinance.stockevaluator.domain.TrendPeriod

@Composable
fun HomeRoute(
    viewModel: HomeViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    HomeScreen(
        state = uiState,
        onTickerChanged = viewModel::onTickerChanged,
        onEvaluate = viewModel::evaluateTicker
    )
}

@Composable
fun HomeScreen(
    state: HomeUiState,
    onTickerChanged: (String) -> Unit,
    onEvaluate: () -> Unit,
    modifier: Modifier = Modifier
) {
    Surface(modifier = modifier.fillMaxSize()) {
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 20.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                Text(
                    text = "Stock Evaluator",
                    style = MaterialTheme.typography.headlineSmall,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )
            }
            item {
                TickerInputSection(
                    ticker = state.tickerInput,
                    isLoading = state.isLoading,
                    onTickerChanged = onTickerChanged,
                    onEvaluate = onEvaluate
                )
            }
            state.errorMessage?.let { message ->
                item {
                    Text(
                        text = message,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            }
            state.lastDetail?.let { detail ->
                item {
                    EvaluationDetailSection(detail = detail)
                }
            }
            item {
                Text(
                    text = "History",
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier.padding(top = 8.dp)
                )
            }
            if (state.history.isEmpty()) {
                item {
                    Text(
                        text = "No evaluations yet. Enter a ticker to get started.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else {
                items(state.history) { summary ->
                    HistoryCard(summary)
                }
            }
            item { Spacer(modifier = Modifier.height(12.dp)) }
        }
    }
}

@Composable
private fun TickerInputSection(
    ticker: String,
    isLoading: Boolean,
    onTickerChanged: (String) -> Unit,
    onEvaluate: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        OutlinedTextField(
            modifier = Modifier.fillMaxWidth(),
            value = ticker,
            onValueChange = onTickerChanged,
            singleLine = true,
            label = { Text("Ticker") },
            keyboardOptions = KeyboardOptions(
                capitalization = KeyboardCapitalization.Characters,
                imeAction = ImeAction.Done,
                keyboardType = KeyboardType.Ascii
            ),
            keyboardActions = KeyboardActions(onDone = { onEvaluate() })
        )
        Button(
            onClick = onEvaluate,
            modifier = Modifier.fillMaxWidth(),
            enabled = !isLoading
        ) {
            if (isLoading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(18.dp),
                    strokeWidth = 2.dp
                )
            } else {
                Text("Evaluate")
            }
        }
    }
}

@Composable
private fun EvaluationDetailSection(detail: EvaluationDetail) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text(
                text = "${detail.summary.ticker} · ${detail.summary.result}",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                text = detail.summary.companyName,
                style = MaterialTheme.typography.bodyMedium
            )
            Text(
                text = "Generated ${detail.summary.generatedAt}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            detail.metrics?.takeIf { it.isNotEmpty() }?.let { metrics ->
                Divider()
                Text(
                    text = "Key Metrics",
                    style = MaterialTheme.typography.titleMedium
                )
                MetricsGrid(metrics = metrics)
            }

            if (detail.nodes.isNotEmpty()) {
                Divider()
                Text(
                    text = "Decision Flow",
                    style = MaterialTheme.typography.titleMedium
                )
                detail.nodes.forEach { node ->
                    DecisionRow(node)
                }
            }

            detail.riskAssessment?.let { assessment ->
                Divider()
                RiskAssessmentCard(assessment)
            }

            detail.trendAnalysis?.let { trends ->
                Divider()
                TrendSection(trends)
            }

            detail.comparativeAnalysis?.let { comparison ->
                Divider()
                ComparativeSection(comparison)
            }

            detail.dividendAnalysis?.let { dividend ->
                Divider()
                DividendSection(dividend)
            }

            detail.flowchartHtml?.let { html ->
                Divider()
                Text(
                    text = "Flowchart Preview",
                    style = MaterialTheme.typography.titleMedium
                )
                FlowchartPreview(html)
            }

            detail.opinionHtml?.let { html ->
                Divider()
                Text(
                    text = "AI Opinion",
                    style = MaterialTheme.typography.titleMedium
                )
                OpinionReport(html)
            }
        }
    }
}

@Composable
private fun MetricsGrid(metrics: Map<String, Double?>) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        metrics.entries.sortedBy { it.key }.forEach { (key, value) ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = key,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.weight(1f, fill = true),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = value?.let { String.format("%.3f", it) } ?: "n/a",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }
    }
}

@Composable
private fun DecisionRow(node: EvaluationNode) {
    val statusColor = when (node.status.uppercase()) {
        "PASS" -> Color(0xFF198754)
        "FAIL" -> Color(0xFFDC3545)
        "CLOSE_FAIL" -> Color(0xFFFFC107)
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surface)
            .padding(12.dp)
    ) {
        Text(
            text = node.metric,
            style = MaterialTheme.typography.bodyLarge,
            fontWeight = FontWeight.SemiBold
        )
        Text(
            text = "Value: ${node.value} · Threshold: ${node.threshold}",
            style = MaterialTheme.typography.bodyMedium
        )
        Text(
            text = node.status.replace('_', ' ').lowercase().replaceFirstChar { it.uppercase() },
            color = statusColor,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold
        )
    }
}

@Composable
private fun RiskAssessmentCard(assessment: RiskAssessment) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = "Risk Assessment",
            style = MaterialTheme.typography.titleMedium
        )
        val score = assessment.overallRiskScore?.let { String.format("%.1f", it) } ?: "?"
        Text(
            text = "Score: $score · Level: ${assessment.riskLevel ?: "Unknown"}",
            style = MaterialTheme.typography.bodyMedium
        )
        if (assessment.recommendations.isNotEmpty()) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                assessment.recommendations.forEach { rec ->
                    Text(text = "• $rec", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}

@Composable
private fun TrendSection(trends: TrendAnalysis) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = "Trend Analysis",
            style = MaterialTheme.typography.titleMedium
        )
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            trends.momentumScore?.let {
                Text(
                    text = "Momentum: ${String.format("%.2f", it)}",
                    style = MaterialTheme.typography.bodyMedium
                )
            }
            trends.trendConsistency?.let {
                Text(
                    text = it,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
        trends.periods.forEach { period ->
            TrendRow(period)
        }
    }
}

@Composable
private fun TrendRow(period: TrendPeriod) {
    val color = when (period.trendDirection?.lowercase()) {
        "up" -> Color(0xFF198754)
        "down" -> Color(0xFFDC3545)
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surface)
            .padding(8.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(text = period.period.uppercase(), style = MaterialTheme.typography.bodyMedium)
        Text(
            text = period.percentReturn?.let { String.format("%.2f%%", it * 100) } ?: "n/a",
            color = color,
            style = MaterialTheme.typography.bodyMedium
        )
    }
}

@Composable
private fun ComparativeSection(comparison: ComparativeAnalysis) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(
            text = "Comparative Snapshot",
            style = MaterialTheme.typography.titleMedium
        )
        comparison.sector?.let { Text("Sector: $it") }
        comparison.marketCapCategory?.let { Text("Market Cap: $it") }
        comparison.valuationVsPeers?.let { Text("Valuation: $it") }
        comparison.growthVsPeers?.let { Text("Growth: $it") }
        comparison.profitabilityVsPeers?.let { Text("Profitability: $it") }
    }
}

@Composable
private fun DividendSection(dividend: DividendAnalysis) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(
            text = "Dividend Profile",
            style = MaterialTheme.typography.titleMedium
        )
        dividend.currentYield?.let {
            Text("Yield: ${String.format("%.2f%%", it * 100)} (${dividend.yieldAttractiveness ?: "n/a"})")
        }
        dividend.payoutRatio?.let {
            Text("Payout Ratio: ${String.format("%.1f%%", it * 100)} (${dividend.dividendSustainability ?: "n/a"})")
        }
    }
}

@Composable
private fun FlowchartPreview(html: String) {
    val context = LocalContext.current
    AndroidView(
        factory = {
            WebView(context).apply {
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                webViewClient = WebViewClient()
            }
        },
        update = { webView ->
            webView.loadDataWithBaseURL(null, html, "text/html", "utf-8", null)
        },
        modifier = Modifier
            .fillMaxWidth()
            .height(220.dp)
    )
}

@Composable
private fun OpinionReport(html: String) {
    val context = LocalContext.current
    AndroidView(
        factory = {
            WebView(context).apply {
                settings.javaScriptEnabled = false
                webViewClient = WebViewClient()
            }
        },
        update = { it.loadDataWithBaseURL(null, html, "text/html", "utf-8", null) },
        modifier = Modifier
            .fillMaxWidth()
            .height(240.dp)
    )
}

@Composable
private fun HistoryCard(summary: EvaluationSummary) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Text(
                text = "${summary.ticker} · ${summary.result}",
                style = MaterialTheme.typography.titleMedium
            )
            Text(text = summary.companyName, style = MaterialTheme.typography.bodyMedium)
            Text(
                text = summary.generatedAt,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}
