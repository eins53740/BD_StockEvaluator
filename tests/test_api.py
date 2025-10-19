from unittest.mock import patch

from fastapi.testclient import TestClient

from bd_stockevaluator.api.main import app


client = TestClient(app)


@patch("bd_stockevaluator.api.main.analysis_service")
def test_evaluate_endpoint_success(service_mock):
    service_mock.analyze.return_value = {
        "ticker": "MSFT",
        "company_name": "Microsoft Corporation",
        "result": "BUY",
        "generated_at": "2025-01-01T00:00:00Z",
        "metrics": {},
        "flowchart_definition": "flowchart TD",
        "opinion_report": "<p>Opinion</p>",
        "path": [("Revenue Growth (TTM)", 0.2, 0.1, "PASS")],
        "active_links": [["A", "B"]],
        "risk_assessment": {},
        "trend_analysis": {},
        "comparative_analysis": {},
        "dividend_analysis": {},
    }

    response = client.post(
        "/evaluate", json={"ticker": "msft", "include_opinion": True}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "MSFT"
    assert payload["result"] == "BUY"
    assert payload["path"][0]["metric"] == "Revenue Growth (TTM)"
    service_mock.analyze.assert_called_once_with("MSFT", include_opinion=True)


@patch("bd_stockevaluator.api.main.analysis_service")
def test_features_endpoint_success(service_mock):
    service_mock.analyze.return_value = {
        "ticker": "MSFT",
        "generated_at": "2025-01-01T00:00:00Z",
        "risk_assessment": {"risk_level": "Low"},
        "trend_analysis": {},
        "comparative_analysis": {},
        "dividend_analysis": {},
    }

    response = client.get("/features/msft")
    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_assessment"]["risk_level"] == "Low"
    service_mock.analyze.assert_called_once_with("MSFT", include_opinion=False)


def test_evaluate_requires_ticker():
    response = client.post("/evaluate", json={"ticker": ""})
    assert response.status_code == 400
    assert response.json()["detail"] == "Ticker symbol is required."
