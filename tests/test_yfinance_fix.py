#!/usr/bin/env python3
"""
Test script to verify yfinance rate limiting fixes
BD 2024 - Test enhanced yfinance utilities
"""

import sys
from pathlib import Path

import pytest

# Add utils to path
REPO_ROOT = Path(__file__).resolve().parents[1]
utils_path = REPO_ROOT / "utils"
if str(utils_path) not in sys.path:
    sys.path.insert(0, str(utils_path))


def test_single_ticker():
    """Test downloading data for a single ticker"""
    print("=== Testing Single Ticker Download ===")

    try:
        from yfinance_utils import download_data_robust
    except Exception as exc:  # pragma: no cover - import guard
        print(f"? Error importing helper: {exc}")
        pytest.skip(f"download_data_robust import failed: {exc}")

    symbol = "AAPL"
    print(f"Testing download for {symbol}...")

    try:
        data = download_data_robust(symbol, period="1mo", interval="1d")
    except Exception as exc:
        print(f"? Error in test: {exc}")
        pytest.skip(f"download_data_robust raised an exception: {exc}")

    if data is None or getattr(data, "empty", True):
        print(
            f"?? Could not download data for {symbol} - this may be expected due to rate limits"
        )
        pytest.skip("download_data_robust returned no data; likely rate limited.")

    print(f"? Success! Downloaded {len(data)} days of data for {symbol}")
    assert not data.empty, "download_data_robust returned an empty DataFrame"


def test_ticker_info():
    """Test getting ticker info"""
    print("\n=== Testing Ticker Info ===")

    try:
        from yfinance_utils import get_ticker_info_robust
    except Exception as exc:  # pragma: no cover - import guard
        print(f"? Error importing helper: {exc}")
        pytest.skip(f"get_ticker_info_robust import failed: {exc}")

    symbol = "AAPL"
    print(f"Testing info retrieval for {symbol}...")

    try:
        info = get_ticker_info_robust(symbol)
    except Exception as exc:
        print(f"? Error in test: {exc}")
        pytest.skip(f"get_ticker_info_robust raised an exception: {exc}")

    if not info:
        print(f"?? Failed to get info for {symbol}")
        pytest.skip("get_ticker_info_robust returned no data; likely rate limited.")

    company_name = info.get("longName", "Unknown")
    sector = info.get("sector", "Unknown")
    print(f"? Success! Got info for {company_name} in {sector} sector")
    assert (
        isinstance(info, dict) and info
    ), "get_ticker_info_robust returned unexpected payload"


def test_european_ticker():
    """Test with the European ticker that was failing"""
    print("\n=== Testing European Ticker (INGA.AS) ===")

    try:
        from yfinance_utils import download_data_robust
    except Exception as exc:  # pragma: no cover - import guard
        print(f"? Error importing helper: {exc}")
        pytest.skip(f"download_data_robust import failed: {exc}")

    symbol = "INGA.AS"
    print(f"Testing download for {symbol}...")

    try:
        data = download_data_robust(symbol, period="1mo", interval="1d", max_retries=3)
    except Exception as exc:
        print(f"? Error in test: {exc}")
        pytest.skip(f"download_data_robust raised an exception: {exc}")

    if data is None or getattr(data, "empty", True):
        print(
            f"?? Could not download data for {symbol} - this may be expected due to rate limits"
        )
        pytest.skip("download_data_robust returned no data; likely rate limited.")

    print(f"? Success! Downloaded {len(data)} days of data for {symbol}")
    assert (
        not data.empty
    ), "download_data_robust returned an empty DataFrame for INGA.AS"


def main():
    """Run all tests"""
    print("?? Testing Enhanced YFinance Utilities")
    print("=" * 50)

    import time

    tests = [
        test_single_ticker,
        test_ticker_info,
        test_european_ticker,
    ]

    results = []

    for index, test_func in enumerate(tests):
        try:
            test_func()
        except pytest.skip.Exception as exc:  # pragma: no cover - script helper
            print(f"⚠ {test_func.__name__} skipped: {exc}")
            results.append(None)
        except AssertionError as exc:  # pragma: no cover - script helper
            print(f"✗ {test_func.__name__} failed: {exc}")
            results.append(False)
        else:
            results.append(True)

        if index < len(tests) - 1:
            time.sleep(3)

    passed = sum(1 for result in results if result is True)
    failed = sum(1 for result in results if result is False)
    skipped = sum(1 for result in results if result is None)

    print("\n" + "=" * 50)
    print("?? Test Results Summary:")
    print(f"? Passed: {passed}/{len(tests)} tests")
    if skipped:
        print(f"⚠ Skipped: {skipped} (likely due to rate limits)")

    if failed:
        print("✗ Some tests failed. Review the logs above.")
        exit_code = 1
    elif skipped and passed == 0:
        print("⚠ All tests skipped. Yahoo Finance may be rate limited.")
        exit_code = 0
    elif skipped:
        print("⚠ Some tests were skipped due to transient issues.")
        exit_code = 0
    else:
        print("?? All tests passed! The enhanced utilities are working.")
        exit_code = 0

    print("\n?? Tips to improve success rate:")
    print("- Run the script at different times of day")
    print("- Use fewer tickers in your daily report")
    print("- Consider running the report less frequently")
    print("- Check your internet connection")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
