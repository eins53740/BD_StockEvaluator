package com.bdfinance.stockevaluator.data.local

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface EvaluationDao {

    @Query("SELECT * FROM evaluations ORDER BY generatedAt DESC")
    fun observeEvaluations(): Flow<List<EvaluationEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(entity: EvaluationEntity)

    @Query("DELETE FROM evaluations WHERE id NOT IN (SELECT id FROM evaluations ORDER BY generatedAt DESC LIMIT :limit)")
    suspend fun pruneTo(limit: Int)
}
