from __future__ import annotations

import json

try:
    from groq import Groq
except Exception:  # pragma: no cover - optional dependency for AI features
    class Groq:  # minimal placeholder so tests can import and patch
        def __init__(self, *args, **kwargs):
            raise RuntimeError(
                "Optional package 'groq' is not installed. Install it or mock 'Groq' in tests."
            )


class FinancialSummaryAgent:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def summarise(self, metrics: dict) -> dict:
        prompt = f"""Summarize the following financial metrics and provide a rating from 1 to 10 and a rationale.

Metrics:
{json.dumps(metrics, indent=2)}

Respond with a JSON object with the keys 'rating' and 'rationale'."""

        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama3-8b-8192",
            temperature=0,
            max_tokens=1024,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
            stop=None,
        )
        response_content = chat_completion.choices[0].message.content
        return json.loads(response_content)


class MarketCommentaryBot:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def generate_commentary(self, macro_data: dict) -> dict:
        prompt = f"""Generate a market commentary based on the following macro data.

Macro Data:
{json.dumps(macro_data, indent=2)}

Respond with a JSON object with the key 'summary'."""

        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama3-8b-8192",
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
            stop=None,
        )
        response_content = chat_completion.choices[0].message.content
        return json.loads(response_content)


class NaturalLanguageScreener:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def _parse_query(self, query: str) -> dict:
        prompt = f"""Parse the following natural language query into a structured filter.

Query: {query}

Respond with a JSON object containing a list of filters. Each filter should have 'field', 'operator', and 'value'."""

        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama3-8b-8192",
            temperature=0,
            max_tokens=1024,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
            stop=None,
        )
        response_content = chat_completion.choices[0].message.content
        return json.loads(response_content)

    def screen(self, query: str, stocks: list[dict]) -> list[dict]:
        parsed_query = self._parse_query(query)
        filters = parsed_query.get("filters", [])

        filtered_stocks = []
        for stock in stocks:
            match = True
            for f in filters:
                field = f.get("field")
                operator = f.get("operator")
                value = f.get("value")

                if field not in stock or operator not in [">", "<", "="]:
                    match = False
                    break

                stock_value = stock[field]
                if operator == ">" and not stock_value > value:
                    match = False
                    break
                if operator == "<" and not stock_value < value:
                    match = False
                    break
                if operator == "=" and not stock_value == value:
                    match = False
                    break

            if match:
                filtered_stocks.append(stock)

        return filtered_stocks


class PredictiveModel:
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def get_sentiment_score(self, text: str) -> float:
        prompt = f"""Analyze the sentiment of the following text and provide a score from 0 to 1.

Text: {text}

Respond with a JSON object with the key 'sentiment_score'."""

        chat_completion = self.client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama3-8b-8192",
            temperature=0,
            max_tokens=1024,
            top_p=1,
            stream=False,
            response_format={"type": "json_object"},
            stop=None,
        )
        response_content = chat_completion.choices[0].message.content
        return json.loads(response_content).get("sentiment_score")
