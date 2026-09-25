"""Offline experiment over the pinned PNCP release with a temporal split.

Buyer affinity is computed only from notices published before the cutoff;
candidates are the notices published on or after it.
"""

from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from .evaluation import evaluate_at_k, mean_metrics
from .identifiers import classify_identifier
from .notices import (
    PROFILE_SCHEMA_VERSION,
    RANKER_VERSION,
    RANKERS,
    buyer_affinity,
    graded_judgments,
    load_notices,
    rank_weighted,
    split_by_cutoff,
    validate_declared_profile,
)
from .release import VerifiedRelease

DEFAULT_CUTOFF = datetime(2025, 1, 6)
K_VALUES = (10, 50)


def code_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run_experiment(
    release: VerifiedRelease,
    profiles: list[dict[str, Any]],
    output_dir: Path,
    cutoff: datetime = DEFAULT_CUTOFF,
    queue_size: int = 20,
) -> dict[str, Any]:
    for profile in profiles:
        validate_declared_profile(profile)
    loaded = load_notices(release.layer("semantic"))
    notices = [n for n in loaded if classify_identifier(n.organization_id) == "organization"]
    history, candidates = split_by_cutoff(notices, cutoff)
    affinity = buyer_affinity(history)

    results: dict[str, dict[str, Any]] = {}
    per_profile: dict[str, dict[str, Any]] = {}
    for name, ranker in RANKERS.items():
        scores = {f"@{k}": [] for k in K_VALUES}
        for profile in profiles:
            ranked = [row["notice_id"] for row in ranker(profile, candidates, affinity=affinity)]
            grades = graded_judgments(profile, candidates)
            for k in K_VALUES:
                metrics = evaluate_at_k(ranked, grades, k)
                scores[f"@{k}"].append(metrics)
                per_profile.setdefault(profile["profile_id"], {"relevant_grade_2": sum(g == 2 for g in grades.values()), "relevant_grade_1": sum(g == 1 for g in grades.values())})
                per_profile[profile["profile_id"]][f"{name}@{k}"] = {key: round(value, 4) for key, value in metrics.items()}
        results[name] = {cut: mean_metrics(rows) for cut, rows in scores.items()}

    lineage = {
        **release.lineage(),
        "code_commit": code_commit(),
        "profile_schema": PROFILE_SCHEMA_VERSION,
        "ranker_version": RANKER_VERSION,
        "cutoff": cutoff.isoformat(),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    queue_path = output_dir / "review_queue.jsonl"
    with queue_path.open("w", encoding="utf-8", newline="\n") as queue:
        for profile in profiles:
            for position, row in enumerate(rank_weighted(profile, candidates, affinity)[:queue_size], start=1):
                queue.write(json.dumps({"profile_id": profile["profile_id"], "position": position, **row, "lineage": lineage}, sort_keys=True) + "\n")

    report = {
        "label": "rule-derived judgments over synthetic declared profiles; measures constraint adherence, not user relevance",
        "lineage": lineage,
        "counts": {
            "release_rows": len(loaded),
            "organization_rows": len(notices),
            "excluded_non_organization_rows": len(loaded) - len(notices),
            "history_rows": len(history),
            "candidate_rows": len(candidates),
            "profiles": len(profiles),
        },
        "metrics": results,
        "per_profile": per_profile,
        "review_queue": {"path": queue_path.name, "sha256": hashlib.sha256(queue_path.read_bytes()).hexdigest()},
    }
    (output_dir / "evaluation.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return report
