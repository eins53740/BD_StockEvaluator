package com.bdfinance.stockevaluator.data.local

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.bdfinance.stockevaluator.domain.EvaluationSummary

@Entity(tableName = "evaluations")
data class EvaluationEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val ticker: String,
    val companyName: String,
    val result: String,
    val generatedAt: String
) {
    fun toDomain(): EvaluationSummary = EvaluationSummary(
        id = id,
        ticker = ticker,
        companyName = companyName,
        result = result,
        generatedAt = generatedAt
    )

    companion object {
        fun fromDomain(model: EvaluationSummary): EvaluationEntity = EvaluationEntity(
            id = model.id,
            ticker = model.ticker,
            companyName = model.companyName,
            result = model.result,
            generatedAt = model.generatedAt
        )
    }
}
