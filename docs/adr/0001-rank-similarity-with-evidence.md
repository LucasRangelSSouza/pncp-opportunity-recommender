# ADR 0001: Rank similarity with explicit evidence

## Context

Historical procurement activity can suggest relevant opportunities but cannot prove eligibility, capacity, availability, or likelihood of winning.

## Decision

The ranker exposes normalized matching evidence and safety labels. It treats organization history as a supplied profile and rejects personal fields.

## Consequences

The output supports human review and carries no commercial or legal guarantee. Deterministic fixtures make ranking behavior inspectable.

## Alternatives considered

A black-box propensity model would hide the basis for a recommendation. Declaring suppliers superior would require criteria and evidence this reference does not hold.
