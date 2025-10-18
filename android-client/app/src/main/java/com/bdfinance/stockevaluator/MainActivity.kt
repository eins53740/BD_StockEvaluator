package com.bdfinance.stockevaluator

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import dagger.hilt.android.AndroidEntryPoint
import com.bdfinance.stockevaluator.ui.home.HomeRoute
import com.bdfinance.stockevaluator.ui.theme.StockEvaluatorTheme

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            StockEvaluatorTheme {
                HomeRoute()
            }
        }
    }
}
