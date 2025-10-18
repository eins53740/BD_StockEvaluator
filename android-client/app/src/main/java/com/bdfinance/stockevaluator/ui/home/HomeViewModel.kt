package com.bdfinance.stockevaluator.ui.home

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bdfinance.stockevaluator.data.repository.StockRepository
import com.bdfinance.stockevaluator.domain.EvaluationDetail
import com.bdfinance.stockevaluator.domain.EvaluationSummary
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class HomeUiState(
    val tickerInput: String = "",
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
    val lastDetail: EvaluationDetail? = null,
    val history: List<EvaluationSummary> = emptyList()
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val repository: StockRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState

    init {
        viewModelScope.launch {
            repository.observeHistory().collectLatest { items ->
                _uiState.update { state ->
                    state.copy(history = items)
                }
            }
        }
    }

    fun onTickerChanged(value: String) {
        _uiState.update { it.copy(tickerInput = value.uppercase(), errorMessage = null) }
    }

    fun evaluateTicker() {
        val ticker = uiState.value.tickerInput.trim().uppercase()
        if (ticker.isEmpty()) {
            _uiState.update { it.copy(errorMessage = "Enter a ticker symbol.") }
            return
        }

        _uiState.update { it.copy(isLoading = true, errorMessage = null) }
        viewModelScope.launch {
            try {
                val detail = repository.evaluateTicker(ticker)
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        tickerInput = "",
                        lastDetail = detail
                    )
                }
            } catch (ex: Exception) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        errorMessage = ex.message ?: "Failed to evaluate ticker."
                    )
                }
            }
        }
    }
}
