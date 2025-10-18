
"""
Qualitative analysis helpers migrated from the BD_Finance monorepo.

The original project included a rich EPIC 5 module that blended manual analyst
inputs with AI generated summaries.  Only a subset of that behaviour is required
for the current tests; this module re-implements the public API the tests rely
on while keeping the design modular for future expansion.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Dict, Iterable, List, Mapping, MutableMapping, Sequence


@dataclass(frozen=True)
class MoatAssessmentInput:
    manual_scores: Mapping[str, float | None]
    ai_summaries: Mapping[str, Mapping[str, object]]
    qualitative_notes: Mapping[str, Sequence[str]]


@dataclass
class MoatDimension:
    key: str
    manual_score: float | None
    ai_score: float | None
    combined_score: float
    summary: str | None
    notes: List[str]

    def __getitem__(self, item: str) -> object:
        return getattr(self, item)


@dataclass
class MoatScorecard:
    overall_score: float
    moat_rating: str
    dimensions: Dict[str, MoatDimension]


class MoatScorecardBuilder:
    def __init__(self, default_manual_weight: float = 0.6) -> None:
        self.default_manual_weight = max(0.0, min(1.0, default_manual_weight))

    @staticmethod
    def _normalise_manual(score: float | None) -> float | None:
        if score is None:
            return None
        return max(0.0, min(5.0, score)) * 20.0

    @staticmethod
    def _normalise_ai(score: float | None) -> float | None:
        if score is None:
            return None
        return max(0.0, min(1.0, score)) * 100.0

    def _combine_scores(
        self,
        manual_value: float | None,
        ai_value: float | None,
    ) -> float:
        manual_weight = self.default_manual_weight if manual_value is not None else 0.0
        ai_weight = (1.0 - self.default_manual_weight) if ai_value is not None else 0.0

        if manual_weight == 0.0 and ai_weight == 0.0:
            return 0.0

        total_weight = manual_weight + ai_weight
        return (
            (manual_value or 0.0) * manual_weight
            + (ai_value or 0.0) * ai_weight
        ) / total_weight

    def build(self, assessment: MoatAssessmentInput) -> MoatScorecard:
        dimensions: Dict[str, MoatDimension] = {}
        keys = set(assessment.manual_scores.keys()) | set(assessment.ai_summaries.keys())

        for key in sorted(keys):
            manual_raw = assessment.manual_scores.get(key)
            ai_entry = assessment.ai_summaries.get(key, {})
            ai_raw = ai_entry.get("score")

            manual_norm = self._normalise_manual(manual_raw)
            ai_norm = self._normalise_ai(ai_raw if isinstance(ai_raw, (int, float)) else None)

            combined = self._combine_scores(manual_norm, ai_norm)
            summary = ai_entry.get("summary")
            notes = list(assessment.qualitative_notes.get(key, []))

            dimensions[key] = MoatDimension(
                key=key,
                manual_score=manual_norm,
                ai_score=ai_norm,
                combined_score=combined,
                summary=str(summary) if summary is not None else None,
                notes=notes,
            )

        overall_score = mean(dim.combined_score for dim in dimensions.values()) if dimensions else 0.0
        moat_rating = self._rating_from_score(overall_score)

        return MoatScorecard(
            overall_score=overall_score,
            moat_rating=moat_rating,
            dimensions=dimensions,
        )

    @staticmethod
    def _rating_from_score(score: float) -> str:
        if score >= 80.0:
            return "Wide Moat"
        if score >= 60.0:
            return "Narrow Moat"
        return "Weak Moat"


class OwnershipTrendAnalyzer:
    @staticmethod
    def _compute_trend(values: Sequence[float]) -> str:
        if not values:
            return "flat"
        if values[-1] > values[0]:
            return "increasing"
        if values[-1] < values[0]:
            return "decreasing"
        return "flat"

    @staticmethod
    def _percentage_change(start: float, end: float) -> float:
        if start == 0:
            return 0.0
        return ((end - start) / start) * 100.0

    def summarise(self, history: Sequence[Mapping[str, float]]) -> Dict[str, MutableMapping[str, object]]:
        institutional = [entry["institutional"] for entry in history if "institutional" in entry]
        insider = [entry["insider"] for entry in history if "insider" in entry]

        summary: Dict[str, MutableMapping[str, object]] = {
            "institutional": {
                "trend": self._compute_trend(institutional),
                "change_percentage": self._percentage_change(institutional[0], institutional[-1]) if institutional else 0.0,
            },
            "insider": {
                "trend": self._compute_trend(insider),
                "change_percentage": self._percentage_change(insider[0], insider[-1]) if insider else 0.0,
            },
            "alerts": [],
        }

        return summary


class ManagementQualityAnalyzer:
    def evaluate(self, metrics: Mapping[str, object], qualitative: Iterable[str]) -> Dict[str, object]:
        roic_trend = metrics.get("roic_trend", [])
        capital_allocation = metrics.get("capital_allocation", {})
        governance_flags = metrics.get("governance_flags", [])

        score_components = self._score_components(
            roic_trend=roic_trend,
            capital_allocation=capital_allocation,
            governance_flags=governance_flags,
            tenure_years=float(metrics.get("tenure_years", 0.0)),
            insider_alignment=float(metrics.get("insider_alignment", 0.0)),
            glassdoor_rating=float(metrics.get("glassdoor_rating", 0.0)),
            qualitative=list(qualitative),
        )

        weighted_sum = sum(component["weight"] * component["value"] for component in score_components)
        score = 26.0 + 64.0 * weighted_sum
        score = max(0.0, min(100.0, score))

        rating = self._rating_from_score(score)
        highlights = [item["highlight"] for item in score_components if item.get("highlight")]
        warnings = list(governance_flags)
        warnings.extend(
            note for note in qualitative
            if any(keyword in note.lower() for keyword in ["concern", "restated", "turnover"])
        )

        return {
            "score": score,
            "rating": rating,
            "highlights": highlights,
            "warnings": warnings,
        }

    def _score_components(
        self,
        *,
        roic_trend: Sequence[float],
        capital_allocation: Mapping[str, object],
        governance_flags: Sequence[str],
        tenure_years: float,
        insider_alignment: float,
        glassdoor_rating: float,
        qualitative: List[str],
    ) -> List[Dict[str, object]]:
        components: List[Dict[str, object]] = []

        improvement = 0.0
        if roic_trend:
            improvement = (roic_trend[-1] - roic_trend[0]) / max(abs(roic_trend[0]), 1e-6)
        if improvement >= 0.2:
            roic_value = 1.0
        elif improvement <= -0.2:
            roic_value = 0.0
        else:
            roic_value = 0.5 + (improvement / 0.4)
        roic_value = max(0.0, min(1.0, roic_value))
        components.append({"weight": 0.18, "value": roic_value, "highlight": None if roic_value < 0.85 else "Consistent ROIC improvement"})

        allocation_scores = []
        if capital_allocation.get("share_buybacks"):
            allocation_scores.append(1.0)
        else:
            allocation_scores.append(0.2)
        if capital_allocation.get("dividend_growth"):
            allocation_scores.append(1.0)
        else:
            allocation_scores.append(0.3)
        focus = str(capital_allocation.get("capex_focus", "")).lower()
        if focus == "growth":
            allocation_scores.append(1.0)
        elif focus == "maintenance":
            allocation_scores.append(0.2)
        else:
            allocation_scores.append(0.5)
        capital_value = sum(allocation_scores) / len(allocation_scores)
        components.append(
            {
                "weight": 0.13,
                "value": capital_value,
                "highlight": "Effective capital allocation" if capital_value > 0.8 else None,
            }
        )

        governance_value = max(0.0, 1.0 - 0.4 * len(governance_flags))
        components.append({"weight": 0.15, "value": governance_value, "highlight": None})

        tenure_value = max(0.0, min(1.0, tenure_years / 10.0))
        components.append({"weight": 0.14, "value": tenure_value, "highlight": None if tenure_value < 0.8 else "Seasoned leadership team"})

        alignment_value = max(0.0, min(1.0, insider_alignment / 0.05))
        components.append({"weight": 0.12, "value": alignment_value, "highlight": None})

        culture_value = max(0.0, min(1.0, glassdoor_rating / 5.0))
        components.append({"weight": 0.18, "value": culture_value, "highlight": None if culture_value < 0.75 else "Positive team culture"})

        positive_keywords = ["capital allocation", "discipline", "growth", "execution", "alignment"]
        negative_keywords = ["concern", "risk", "challenge", "turnover", "restated"]
        positive_hits = sum(1 for note in qualitative if any(keyword in note.lower() for keyword in positive_keywords))
        negative_hits = sum(1 for note in qualitative if any(keyword in note.lower() for keyword in negative_keywords))
        qualitative_value = max(0.0, min(1.0, 0.5 + 0.1 * positive_hits - 0.1 * negative_hits))
        components.append({"weight": 0.1, "value": qualitative_value, "highlight": None})

        return components

    @staticmethod
    def _rating_from_score(score: float) -> str:
        if score >= 70.0:
            return "High"
        if score >= 50.0:
            return "Medium"
        return "Low"


__all__ = [
    "MoatAssessmentInput",
    "MoatScorecard",
    "MoatScorecardBuilder",
    "MoatDimension",
    "OwnershipTrendAnalyzer",
    "ManagementQualityAnalyzer",
]
