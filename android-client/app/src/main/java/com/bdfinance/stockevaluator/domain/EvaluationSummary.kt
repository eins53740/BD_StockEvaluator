package com.bdfinance.stockevaluator.domain

data class EvaluationSummary(
    val id: Long = 0,
    val ticker: String,
    val companyName: String,
    val result: String,
    val generatedAt: String
)
