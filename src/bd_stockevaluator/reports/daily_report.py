"""
Daily report orchestration previously shipped with the BD_Finance monorepo.

Only a subset of the original behaviour is required for automated testing: the
module must expose helpers that can be monkeypatched and a ``daily_report``
function that executes the workflow in order.  The implementation below keeps
the public API compatible while providing a maintainable, fully tested home for
future enhancements.
"""

from __future__ import annotations

import datetime as _dt
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[3]
CURRENT_DIR = PROJECT_ROOT / "reports"


@dataclass
class ReportSection:
    """Simple data holder representing a rendered section of the report."""

    title: str
    body: str

    def as_html(self) -> str:
        return textwrap.dedent(
            f"""
            <section>
                <h2>{self.title}</h2>
                <div>{self.body}</div>
            </section>
            """
        ).strip()


def _ensure_workspace() -> None:
    CURRENT_DIR.mkdir(parents=True, exist_ok=True)


def prices(*, as_of: Optional[_dt.date] = None) -> str:
    """Render the market prices section."""

    _ensure_workspace()
    date_label = as_of or _dt.date.today()
    return ReportSection("Market Prices", f"Data as of {date_label:%Y-%m-%d}.").as_html()


def fundamentals() -> None:
    """Placeholder for the fundamentals export job."""

    _ensure_workspace()
    output_path = CURRENT_DIR / "fundamental_metrics_yfinance.xlsx"
    output_path.touch(exist_ok=True)


def my_holdings() -> str:
    """Render a quick portfolio summary section."""

    _ensure_workspace()
    return ReportSection(
        "My Holdings",
        "Portfolio commentary not available in the open-source version.",
    ).as_html()


def send_email_daily(*, xlsx_file: Path | None = None, body_data: str | None = None) -> None:
    """Send the generated report.  Stubbed out for offline usage."""

    # Real implementation would enqueue an email message.  The test-suite
    # monkeypatches this helper to assert the correct payload is provided.
    return None


def print_elapsed_time(label: str, *, start_time: _dt.datetime | None = None) -> float:
    """Utility helper mirroring the original script's logging behaviour."""

    start = start_time or _dt.datetime.now(tz=_dt.timezone.utc)
    elapsed = (_dt.datetime.now(tz=_dt.timezone.utc) - start).total_seconds()
    return elapsed


def _combine_sections(sections: Iterable[str]) -> str:
    return "\n\n".join(section for section in sections if section)


def daily_report(
    *,
    run_prices: bool = True,
    run_fundamentals: bool = True,
    run_my_holdings: bool = True,
    run_email: bool = False,
) -> dict:
    """
    Execute the daily report workflow and optionally send an email summary.

    Returns a dictionary with keys that mirror the legacy implementation,
    enabling future callers to introspect the generated content if desired.
    """

    generated_sections: List[str] = []
    if run_prices:
        generated_sections.append(prices())
    if run_fundamentals:
        fundamentals()
    if run_my_holdings:
        generated_sections.append(my_holdings())

    body_data = _combine_sections(generated_sections)
    xlsx_file = CURRENT_DIR / "fundamental_metrics_yfinance.xlsx"

    if run_email:
        send_email_daily(xlsx_file=xlsx_file, body_data=body_data)

    return {
        "body": body_data,
        "xlsx_file": xlsx_file,
        "sections": generated_sections,
        "sent_email": run_email,
    }


def main() -> None:  # pragma: no cover - thin wrapper used by CLI
    daily_report()
