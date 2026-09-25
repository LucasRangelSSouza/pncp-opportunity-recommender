"""Propensity-ready interface. Disabled until authorized interaction events exist.

Public PNCP data contains no clicks, proposals, or wins, so no event source in
this repository can support a real propensity claim.
"""

from __future__ import annotations

from typing import Any

EVENT_FIELDS = frozenset({"event_id", "profile_id", "notice_id", "event_type", "occurred_at", "source", "consent_basis"})
EVENT_TYPES = frozenset({"impression", "open", "save", "dismiss"})


class LearningToRankDisabled(RuntimeError):
    pass


def validate_events(events: list[dict[str, Any]], claim_real_propensity: bool) -> None:
    for event in events:
        if set(event) != EVENT_FIELDS:
            raise ValueError(f"event fields must be exactly {sorted(EVENT_FIELDS)}")
        if event["event_type"] not in EVENT_TYPES:
            raise ValueError(f"unsupported event type: {event['event_type']}")
        if claim_real_propensity and event["source"] == "synthetic":
            raise ValueError("synthetic events cannot support a real-propensity claim")
        if event["source"] != "synthetic" and not event["consent_basis"]:
            raise ValueError("non-synthetic events require a recorded consent basis")


def train(events: list[dict[str, Any]], *, enabled: bool = False, claim_real_propensity: bool = False) -> dict[str, Any]:
    if not enabled:
        raise LearningToRankDisabled("learning-to-rank requires an authorized interaction-event dataset")
    validate_events(events, claim_real_propensity)
    positives = sum(event["event_type"] in {"open", "save"} for event in events)
    synthetic = all(event["source"] == "synthetic" for event in events)
    return {
        "status": "pipeline_exercised",
        "events": len(events),
        "positive_events": positives,
        "label": "synthetic experiment, not observed user behavior" if synthetic else "authorized events",
    }
