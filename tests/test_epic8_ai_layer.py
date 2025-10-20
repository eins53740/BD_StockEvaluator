from __future__ import annotations

from unittest.mock import patch


from bd_stockevaluator.analysis.epic8_ai_layer import (
    FinancialSummaryAgent,
    MarketCommentaryBot,
    NaturalLanguageScreener,
    PredictiveModel,
)


@patch("bd_stockevaluator.analysis.epic8_ai_layer.Groq")
def test_financial_summary_agent(mock_groq):
    # Arrange
    mock_groq.return_value.chat.completions.create.return_value.choices[
        0
    ].message.content = '{"rating": 8, "rationale": "The company shows strong growth and profitability."}'

    metrics = {
        "revenue_growth": 0.2,
        "pe_ratio": 15,
        "roe": 0.25,
    }

    # Act
    agent = FinancialSummaryAgent(api_key="fake_key")
    summary = agent.summarise(metrics)

    # Assert
    assert summary["rating"] == 8
    assert summary["rationale"] == "The company shows strong growth and profitability."


@patch("bd_stockevaluator.analysis.epic8_ai_layer.Groq")
def test_market_commentary_bot(mock_groq):
    # Arrange
    mock_groq.return_value.chat.completions.create.return_value.choices[
        0
    ].message.content = '{"summary": "The market is showing positive signs with low inflation and steady growth."}'

    macro_data = {
        "gdp_growth": 0.02,
        "cpi": 0.01,
        "unemployment_rate": 0.04,
    }

    # Act
    bot = MarketCommentaryBot(api_key="fake_key")
    commentary = bot.generate_commentary(macro_data)

    # Assert
    assert (
        commentary["summary"]
        == "The market is showing positive signs with low inflation and steady growth."
    )


@patch("bd_stockevaluator.analysis.epic8_ai_layer.Groq")
def test_natural_language_screener(mock_groq):
    # Arrange
    mock_groq.return_value.chat.completions.create.return_value.choices[
        0
    ].message.content = '{"filters": [{"field": "roe", "operator": ">", "value": 0.15}, {"field": "debt_to_equity", "operator": "<", "value": 0.5}]}'

    stocks = [
        {"ticker": "A", "roe": 0.2, "debt_to_equity": 0.3},
        {"ticker": "B", "roe": 0.1, "debt_to_equity": 0.4},
        {"ticker": "C", "roe": 0.3, "debt_to_equity": 0.6},
    ]

    query = "find stocks with ROE > 15% and low debt"

    # Act
    screener = NaturalLanguageScreener(api_key="fake_key")
    results = screener.screen(query, stocks)

    # Assert
    assert [stock["ticker"] for stock in results] == ["A"]


@patch("bd_stockevaluator.analysis.epic8_ai_layer.Groq")
def test_predictive_model(mock_groq):
    # Arrange
    mock_groq.return_value.chat.completions.create.return_value.choices[
        0
    ].message.content = '{"sentiment_score": 0.8}'

    text = "This is a great company with strong fundamentals."

    # Act
    model = PredictiveModel(api_key="fake_key")
    score = model.get_sentiment_score(text)

    # Assert
    assert score == 0.8
