"""Rank historical PNCP notices from a verified release against a declared supplier profile.

Release v1 carries no deadline, status, location, or item text. Results are
therefore historical notices for similarity review, never open opportunities.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from math import log10
from typing import Any, Iterable

CATEGORIES = frozenset({"education", "health", "technology", "works_and_maintenance", "transport", "other"})
PROFILE_SCHEMA_VERSION = "declared-profile/1"
RANKER_VERSION = "weighted-transparent/1"


@dataclass(frozen=True)
class Notice:
    notice_id: str
    organization_id: str
    organization_name: str
    category: str
    estimated_value: float
    published_at: datetime
    procurement_year: int
    procurement_sequence: int

    @property
    def source_record_url(self) -> str:
        return (
            "https://pncp.gov.br/app/editais/"
            f"{self.organization_id}/{self.procurement_year}/{self.procurement_sequence}"
        )


def load_notices(parquet_path) -> list[Notice]:
    import pyarrow.parquet as pq

    rows = pq.read_table(parquet_path).to_pylist()
    return [
        Notice(
            notice_id=row["id"],
            organization_id=row["contracting_organization_id"],
            organization_name=row["contracting_organization_name"],
            category=row["procurement_category"],
            estimated_value=float(row["estimated_value"]),
            published_at=datetime.fromisoformat(row["published_at"]),
            procurement_year=int(row["procurement_year"]),
            procurement_sequence=int(row["procurement_sequence"]),
        )
        for row in rows
    ]


def split_by_cutoff(notices: Iterable[Notice], cutoff: datetime) -> tuple[list[Notice], list[Notice]]:
    history = [notice for notice in notices if notice.published_at < cutoff]
    candidates = [notice for notice in notices if notice.published_at >= cutoff]
    return history, candidates


def validate_declared_profile(profile: dict[str, Any]) -> None:
    allowed = {"profile_id", "categories", "min_value", "max_value", "synthetic"}
    unexpected = set(profile) - allowed
    if unexpected:
        raise ValueError(f"declared profile has unsupported fields: {sorted(unexpected)}")
    categories = profile.get("categories")
    if not categories or not set(categories) <= CATEGORIES:
        raise ValueError(f"categories must be a non-empty subset of {sorted(CATEGORIES)}")
    if not 0 <= profile["min_value"] <= profile["max_value"]:
        raise ValueError("value band must satisfy 0 <= min_value <= max_value")


def buyer_affinity(history: Iterable[Notice]) -> Counter[tuple[str, str]]:
    """Count earlier notices per (buyer, category); computed from history only."""
    return Counter((notice.organization_id, notice.category) for notice in history)


def value_fit(value: float, low: float, high: float) -> float:
    """1.0 inside the band, decaying by order of magnitude outside it."""
    if low <= value <= high:
        return 1.0
    if value <= 0:
        return 0.0
    edge = low if value < low else high
    if edge <= 0:
        return 0.0
    return max(0.0, 1.0 - abs(log10(value / edge)))


def _in_profile(notice: Notice, profile: dict[str, Any]) -> bool:
    return notice.category in profile["categories"]


def rank_recency(profile: dict[str, Any], candidates: list[Notice], **_: Any) -> list[dict[str, Any]]:
    """Baseline A: newest notices first, no profile filter."""
    ordered = sorted(candidates, key=lambda n: (-n.published_at.timestamp(), n.notice_id))
    return [{"notice_id": n.notice_id, "score": 0.0} for n in ordered]


def rank_metadata_filter(profile: dict[str, Any], candidates: list[Notice], **_: Any) -> list[dict[str, Any]]:
    """Baseline B: category and value-band filter, newest first."""
    kept = [
        n for n in candidates
        if _in_profile(n, profile) and profile["min_value"] <= n.estimated_value <= profile["max_value"]
    ]
    ordered = sorted(kept, key=lambda n: (-n.published_at.timestamp(), n.notice_id))
    return [{"notice_id": n.notice_id, "score": 1.0} for n in ordered]


WEIGHTS = {"value_fit": 0.6, "buyer_affinity": 0.3, "recency": 0.1}


def rank_weighted(
    profile: dict[str, Any],
    candidates: list[Notice],
    affinity: Counter[tuple[str, str]] | None = None,
) -> list[dict[str, Any]]:
    """Transparent ranker: category is a hard constraint; each score term is reported."""
    validate_declared_profile(profile)
    affinity = affinity or Counter()
    kept = [n for n in candidates if _in_profile(n, profile)]
    if not kept:
        return []
    newest = max(n.published_at for n in kept).timestamp()
    oldest = min(n.published_at for n in kept).timestamp()
    span = (newest - oldest) or 1.0
    results = []
    for notice in kept:
        prior = affinity[(notice.organization_id, notice.category)]
        contributions = {
            "value_fit": WEIGHTS["value_fit"] * value_fit(notice.estimated_value, profile["min_value"], profile["max_value"]),
            "buyer_affinity": WEIGHTS["buyer_affinity"] * min(prior, 5) / 5,
            "recency": WEIGHTS["recency"] * (notice.published_at.timestamp() - oldest) / span,
        }
        results.append({
            "notice_id": notice.notice_id,
            "score": round(sum(contributions.values()), 6),
            "contributions": {key: round(value, 6) for key, value in contributions.items()},
            "evidence": {
                "category": notice.category,
                "estimated_value": notice.estimated_value,
                "buyer_prior_notices_in_category": prior,
                "published_at": notice.published_at.isoformat(),
            },
            "missing_evidence": ["deadline", "status", "location", "item_specification"],
            "source_record_url": notice.source_record_url,
            "record_type": "historical_notice",
            "review_required": True,
            "eligibility_not_assessed": True,
            "win_probability_not_estimated": True,
        })
    return sorted(results, key=lambda row: (-row["score"], row["notice_id"]))


RANKERS = {
    "recency": rank_recency,
    "metadata_filter": rank_metadata_filter,
    "weighted_transparent": rank_weighted,
}


def graded_judgments(profile: dict[str, Any], candidates: list[Notice]) -> dict[str, int]:
    """Rule-derived relevance: 2 = category and value band, 1 = category only.

    These labels measure constraint adherence against a declared profile.
    They are not observed user relevance.
    """
    grades = {}
    for notice in candidates:
        if not _in_profile(notice, profile):
            continue
        in_band = profile["min_value"] <= notice.estimated_value <= profile["max_value"]
        grades[notice.notice_id] = 2 if in_band else 1
    return grades
