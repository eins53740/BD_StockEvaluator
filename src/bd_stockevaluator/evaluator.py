# D:/GitHub/BD_Python_AI/BD_Finance/FlowchartStocks/stock-evaluator/evaluator.py
import operator


class StockEvaluator:
    """
    Encapsulates the logic for evaluating a stock based on its financial metrics.
    Now includes a "close call" status and processes all checks for a complete UI.
    """

    # Decision thresholds
    THRESHOLDS = {
        "rev_growth": 0.10,  # 10% TTM Revenue Growth
        "pe": 25,
        "peg": 2,
        "roe": 0.15,  # 15% is a common benchmark for a strong ROE
        "margin": 0.10,  # 10% Net Profit Margin
        "de": 1.0,  # Debt/Equity less than 1.0
        "qr": 1.5,  # Quick Ratio
    }
    # How close a value needs to be to the threshold to be a "close call" (10% tolerance)
    CLOSE_CALL_TOLERANCE = 0.10

    def __init__(self, stock_info, thresholds=None):
        self.info = stock_info
        self.thresholds = thresholds or self.THRESHOLDS
        self.metrics = self._extract_metrics()
        self.path = []
        self.active_links = set()

    def _extract_metrics(self):
        """Extracts and standardizes metrics from the yfinance info dictionary."""
        return {
            "rev_growth": self.info.get("revenueGrowth"),
            "pe": self.info.get("trailingPE"),
            "roe": self.info.get("returnOnEquity"),
            "margin": self.info.get("profitMargins"),
            "de": self.info.get("debtToEquity"),
            "qr": self.info.get("quickRatio"),
        }

    def _check(self, metric_key, name, op, threshold_key):
        """
        Helper to perform a single metric check.
        Appends the result to the path and returns a status: 'PASS', 'FAIL', or 'CLOSE_FAIL'.
        """
        value = self.metrics.get(metric_key)
        threshold = self.thresholds[threshold_key]

        if value is None:
            self.path.append((name, None, threshold, "FAIL"))
            return "FAIL"

        if op(value, threshold):
            self.path.append((name, value, threshold, "PASS"))
            return "PASS"

        # If it failed, check if it was a close call
        if op == operator.ge and value >= threshold * (1 - self.CLOSE_CALL_TOLERANCE):
            self.path.append((name, value, threshold, "CLOSE_FAIL"))
            return "CLOSE_FAIL"
        elif op == operator.lt and value <= threshold * (1 + self.CLOSE_CALL_TOLERANCE):
            self.path.append((name, value, threshold, "CLOSE_FAIL"))
            return "CLOSE_FAIL"

        self.path.append((name, value, threshold, "FAIL"))
        return "FAIL"

    def evaluate(self):
        """
        Runs the stock evaluation flowchart. It processes all checks to provide a
        complete status for the UI, and determines the final verdict based on the
        first critical failure. It also tracks the active decision path.
        """
        verdict = "BUY"
        verdict_set = False
        self.active_links.add(("A", "B"))  # Path from Start to the first check

        # --- Process all checks to get a complete path for the UI ---

        # 1. Revenue Growth
        rev_status = self._check(
            "rev_growth", "Revenue Growth (TTM)", operator.ge, "rev_growth"
        )
        if rev_status == "PASS":
            self.active_links.add(("B", "C"))
        else:
            # Only mark Do Not Buy on definite FAILs; CLOSE_FAILs are non-fatal
            self.active_links.add(("B", "D"))
            if rev_status == "FAIL" and not verdict_set:
                verdict = "Do Not Buy"
                verdict_set = True

        # 2. P/E and PEG Ratio
        pe_value = self.metrics.get("pe")
        pe_threshold = self.thresholds["pe"]
        pe_ok = pe_value is not None and 0 < pe_value < pe_threshold
        self.path.append(
            ("P/E Ratio", pe_value, f"< {pe_threshold}", "PASS" if pe_ok else "FAIL")
        )

        peg_ok = False
        if pe_ok:
            self.active_links.add(("C", "E"))
        else:
            self.active_links.add(("C", "F"))
            rev_growth_pct = (self.metrics.get("rev_growth", 0) or 0) * 100
            peg_value = (
                (pe_value / rev_growth_pct)
                if rev_growth_pct and pe_value is not None
                else None
            )
            peg_threshold = self.thresholds["peg"]
            peg_ok = peg_value is not None and 0 < peg_value < peg_threshold
            self.path.append(
                (
                    "PEG Ratio",
                    peg_value,
                    f"< {peg_threshold}",
                    "PASS" if peg_ok else "FAIL",
                )
            )
            if peg_ok:
                self.active_links.add(("F", "E"))
            else:
                self.active_links.add(("F", "D"))

        if not pe_ok and not peg_ok and not verdict_set:
            verdict = "Do Not Buy"
            verdict_set = True

        # 3. Return on Equity (ROE)
        roe_status = self._check("roe", "Return on Equity", operator.ge, "roe")
        if roe_status == "PASS":
            self.active_links.add(("E", "G"))
        else:
            self.active_links.add(("E", "D"))
            if roe_status == "FAIL" and not verdict_set:
                verdict = "Do Not Buy"
                verdict_set = True

        # 4. Net Profit Margin
        margin_status = self._check(
            "margin", "Net Profit Margin", operator.ge, "margin"
        )
        if margin_status == "PASS":
            self.active_links.add(("G", "H"))
        else:
            self.active_links.add(("G", "D"))
            if margin_status == "FAIL" and not verdict_set:
                verdict = "Do Not Buy"
                verdict_set = True

        # 5. Debt to Equity
        de_status = self._check("de", "Debt to Equity", operator.lt, "de")
        if de_status == "PASS":
            self.active_links.add(("H", "I"))
        else:
            self.active_links.add(("H", "D"))
            if de_status == "FAIL" and not verdict_set:
                verdict = "Do Not Buy"
                verdict_set = True

        # 6. Quick Ratio (influences caution level, not a hard fail)
        qr_status = self._check("qr", "Quick Ratio", operator.ge, "qr")
        if qr_status == "PASS":
            self.active_links.add(("I", "J"))
        else:
            self.active_links.add(("I", "K"))
            if verdict == "BUY":
                verdict = "BUY with Caution"

        return verdict, self.path, self.active_links
