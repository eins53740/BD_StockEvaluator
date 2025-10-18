package com.bdfinance.stockevaluator.di

import android.content.Context
import androidx.room.Room
import com.bdfinance.stockevaluator.data.local.EvaluationDao
import com.bdfinance.stockevaluator.data.local.StockDatabase
import com.bdfinance.stockevaluator.data.repository.StockRepository
import com.bdfinance.stockevaluator.data.remote.StockApi
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object DatabaseModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): StockDatabase =
        Room.databaseBuilder(
            context,
            StockDatabase::class.java,
            "stock_evaluator.db"
        ).build()

    @Provides
    fun provideEvaluationDao(db: StockDatabase): EvaluationDao = db.evaluationDao()

    @Provides
    @Singleton
    fun provideStockRepository(
        api: StockApi,
        evaluationDao: EvaluationDao
    ): StockRepository = StockRepository(api, evaluationDao)
}
