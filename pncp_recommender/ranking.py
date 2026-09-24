from __future__ import annotations

from collections import Counter
from datetime import date
from math import log2
import re
from typing import Any


def terms(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]{3,}", value.casefold())}


def validate_profile(profile: dict[str, Any]) -> None:
    forbidden = {"cpf", "email", "phone", "address", "person_name"} & profile.keys()
    if forbidden:
        raise ValueError(f"profile contains prohibited personal fields: {sorted(forbidden)[0]}")
    if not profile.get("organization_id"):
        raise ValueError("organization_id is required")
    if not isinstance(profile.get("categories", []), list):
        raise ValueError("categories must be a list")


def rank_opportunities(profile: dict[str, Any], opportunities: list[dict[str, Any]], as_of: date) -> list[dict[str, Any]]:
    validate_profile(profile)
    profile_terms = terms(" ".join(profile.get("categories", [])))
    results: list[dict[str, Any]] = []
    for opportunity in opportunities:
        if opportunity.get("status") != "open":
            continue
        deadline = date.fromisoformat(opportunity["deadline"])
        if deadline < as_of:
            continue
        item_terms = terms(opportunity["item"])
        overlap = sorted(profile_terms & item_terms)
        modality_match = int(opportunity.get("modality") in profile.get("modalities", []))
        location_match = int(opportunity.get("state") in profile.get("states", []))
        score = len(overlap) * 10 + modality_match * 3 + location_match * 2
        if score == 0:
            continue
        results.append({
            "opportunity_id": opportunity["id"],
            "rank_score": score,
            "reason": {"matched_terms": overlap, "modality_match": bool(modality_match), "state_match": bool(location_match)},
            "source_record_url": opportunity["source_record_url"],
            "review_required": True,
            "eligibility_not_assessed": True,
            "win_probability_not_estimated": True,
        })
    return sorted(results, key=lambda item: (-item["rank_score"], item["opportunity_id"]))


def evaluate_rankings(ranked_by_query: dict[str, list[str]], relevant_by_query: dict[str, set[str]]) -> dict[str, float]:
    recalls: list[float] = []
    reciprocal_ranks: list[float] = []
    normalized_discounted_gains: list[float] = []
    for query, relevant in relevant_by_query.items():
        ranked = ranked_by_query.get(query, [])
        hits = [index for index, item in enumerate(ranked, start=1) if item in relevant]
        recalls.append(len(set(ranked) & relevant) / len(relevant) if relevant else 1.0)
        reciprocal_ranks.append(1 / hits[0] if hits else 0.0)
        discounted_gain = sum(1 / log2(index + 1) for index, item in enumerate(ranked, start=1) if item in relevant)
        ideal_gain = sum(1 / log2(index + 1) for index in range(1, min(len(relevant), len(ranked)) + 1))
        normalized_discounted_gains.append(discounted_gain / ideal_gain if ideal_gain else 1.0)
    return {
        "recall_at_all": round(sum(recalls) / len(recalls), 6),
        "mrr": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 6),
        "ndcg_at_all": round(sum(normalized_discounted_gains) / len(normalized_discounted_gains), 6),
    }
