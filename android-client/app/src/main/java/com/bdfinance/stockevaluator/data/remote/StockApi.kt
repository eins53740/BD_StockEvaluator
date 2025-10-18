package com.bdfinance.stockevaluator.data.remote

import com.bdfinance.stockevaluator.data.remote.model.EvaluateRequest
import com.bdfinance.stockevaluator.data.remote.model.EvaluationResponse
import com.bdfinance.stockevaluator.data.remote.model.HealthResponse
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST

interface StockApi {
    @GET("health")
    suspend fun health(): HealthResponse

    @POST("evaluate")
    suspend fun evaluate(@Body request: EvaluateRequest): EvaluationResponse
}
