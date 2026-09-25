# Project memory

## Current state

- v0.2.0 ranks historical notices from the pinned Kaggle release `lucasrangelss/brazil-pncp-procurement-history` version 1 (manifest SHA-256 `9301e838…0c66`). The resolver downloads through `kagglehub` and verifies the manifest and every layer before loading ([ADR 0002](docs/adr/0002-pin-release-and-temporal-split.md)).
- The 2026-09-25 offline evaluation at commit `02bd7d0` used a temporal split (history before 2025-01-06) and six synthetic profiles with rule-derived judgments. Results and hashes: [evidence record](docs/evidence/pncp-release-v1-evaluation-2026-09-25.md). The metrics measure constraint adherence, not user relevance.
- 22 unit tests pass locally and in CI.
- The original fixture path (lexical overlap, deadline, status, modality, state) remains as `rank-fixture`.

## Accepted decisions

- Release v1 lacks deadline, status, location, item text, and supplier results. Output rows are `historical_notice` and list that missing evidence.
- Learning-to-rank is disabled by default and rejects synthetic events for real-propensity claims.
- Identifier guard: CNPJ check digits; any 11-digit value is dropped as a possible CPF.

## Next verifiable task

Pin a later PNCP release that adds deadlines and item descriptions, then run lexical retrieval on real data. Organization-history and item-to-supplier modes wait for the gated supplier-result tables.
