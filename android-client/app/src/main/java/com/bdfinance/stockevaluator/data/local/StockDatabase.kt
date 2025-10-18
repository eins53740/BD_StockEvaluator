package com.bdfinance.stockevaluator.data.local

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [EvaluationEntity::class],
    version = 1,
    exportSchema = false
)
abstract class StockDatabase : RoomDatabase() {
    abstract fun evaluationDao(): EvaluationDao
}
