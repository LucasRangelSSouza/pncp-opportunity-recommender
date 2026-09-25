from __future__ import annotations

from math import log2


def evaluate_at_k(ranked: list[str], grades: dict[str, int], k: int) -> dict[str, float]:
    """Recall@K, MRR, and graded nDCG@K for one query."""
    top = ranked[:k]
    relevant = {item for item, grade in grades.items() if grade > 0}
    if not relevant:
        return {"recall": 1.0, "mrr": 1.0, "ndcg": 1.0}
    hits = [index for index, item in enumerate(top, start=1) if item in relevant]
    gain = sum((2 ** grades.get(item, 0) - 1) / log2(index + 1) for index, item in enumerate(top, start=1))
    ideal = sorted(grades.values(), reverse=True)[:k]
    ideal_gain = sum((2 ** grade - 1) / log2(index + 1) for index, grade in enumerate(ideal, start=1))
    return {
        "recall": len(set(top) & relevant) / min(len(relevant), k),
        "mrr": 1 / hits[0] if hits else 0.0,
        "ndcg": gain / ideal_gain if ideal_gain else 0.0,
    }


def mean_metrics(per_query: list[dict[str, float]]) -> dict[str, float]:
    keys = per_query[0].keys()
    return {key: round(sum(row[key] for row in per_query) / len(per_query), 4) for key in keys}
