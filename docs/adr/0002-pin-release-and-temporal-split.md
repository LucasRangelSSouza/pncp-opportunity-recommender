# ADR 0002: Pin the Kaggle release and evaluate with a temporal split

## Context

The recommender needs real public procurement records. The first reviewed release, `brazil-pncp-procurement-history` version 1, contains notice metadata and a controlled category, but no deadline, status, location, item text, or supplier results. Kaggle's CLI always downloads the latest version.

## Decision

The resolver pins slug, version, manifest SHA-256, and schema version in code. It downloads through `kagglehub`, which accepts an explicit version, and then verifies the manifest and every layer before any record is read. A local directory can replace the download for offline runs, with the same verification.

The evaluation splits the release by publication time. Buyer affinity is counted only from the earlier notices, and the later notices are the candidates. Judgments are rule-derived from the declared profile and are labeled that way in every report.

## Consequences

A new release cannot enter the ranker silently: the manifest hash changes and verification fails until the pin is updated in a reviewed commit. Results describe constraint adherence on historical notices and say nothing about user relevance or win probability.

## Alternatives considered

- Downloading the latest version and trusting it. Rejected because it breaks lineage.
- Hand-labeled relevance. Deferred: there is no item text in release v1 to judge against, and labels written by the author against the same fields would still be rule-like.
- Presenting historical notices as open opportunities. Rejected because the release carries no status or deadline.
