# Evaluating a transparent procurement-opportunity ranking system

**Versioned reference:** [v0.2.0](https://github.com/LucasRangelSSouza/pncp-opportunity-recommender/tree/v0.2.0)

A procurement opportunity list becomes misleading when it hides the reason an item appears at the top. This reference implementation keeps the ranking small enough to read. Every result carries the contribution of each feature, the evidence the ranker did not have, and a link to the official record.

## From fixtures to a pinned public release

The first version ranked synthetic opportunities by term overlap between a declared category list and an item description, then added modality and state matches. It proved the mechanics and nothing else.

Version 0.2.0 reads real records. The companion project [brazil-public-data-map](https://github.com/LucasRangelSSouza/brazil-public-data-map) publishes a reviewed derivative of the PNCP consultation API on Kaggle as `lucasrangelss/brazil-pncp-procurement-history`. The recommender pins version 1 of that dataset by slug, version number, and the SHA-256 of its release manifest. Before reading a single row, it hashes the manifest and every layer. A different release fails verification until someone updates the pin in a reviewed commit. The Kaggle CLI always fetches the latest version, so the resolver uses `kagglehub`, which accepts an explicit version and needs no credential for a public dataset.

Release v1 is narrow on purpose. It holds 1,979 notices published between 2025-01-01 and 2025-01-07 under one modality. Each row has the contracting organization, an estimated value, publication and update times, and a category from a six-value taxonomy. The free-text subject was reduced to that category before release. There is no deadline, no status, no location, no item text, and no supplier result.

Those absences decide what the system may claim. Without a status or deadline, nothing in the release is an open opportunity, so the review queue labels each row `historical_notice` and lists `deadline`, `status`, `location`, and `item_specification` as missing evidence. Without item text, lexical and embedding retrieval have nothing to match on real data. Without supplier results, the organization-history mode described in the specification cannot run.

## Study design

A declared profile contains one or two categories and a value band. Six synthetic profiles cover health, education, technology, civil works, transport, and a mixed case.

The evaluation splits the release by time. The 831 notices published before 2025-01-06 form the history; the 1,148 published on 2025-01-06 or 2025-01-07 are the candidates. The history is used only to count how often each buyer published in each category. This avoids a quiet form of leakage in which a ranker learns about the candidates from the candidates.

Three rankers compete. A recency baseline ignores the profile. A filter baseline keeps notices in the right category and value band and orders them newest first. The weighted ranker keeps every category match and scores value fit (weight 0.6), prior notices by the same buyer in that category (0.3), and recency (0.1). Value fit is 1 inside the band and loses one unit per order of magnitude outside it.

Relevance labels come from a rule: grade 2 when the category matches and the value is inside the band, grade 1 when only the category matches. The rule uses fields every ranker can see. The resulting metrics measure constraint adherence. They cannot measure what a supplier would find useful.

## Results

| Ranker | Recall@10 | nDCG@10 | Recall@50 | nDCG@50 |
|---|---:|---:|---:|---:|
| Recency, no filter | 0.1667 | 0.0616 | 0.1685 | 0.0764 |
| Category and value filter | 1.0000 | 1.0000 | 0.8307 | 0.9484 |
| Weighted transparent | 1.0000 | 0.9345 | 1.0000 | 0.9135 |

The filter baseline scores a perfect nDCG@10 because it is the grade-2 rule. It pays for that at K=50: it discards grade-1 notices, and some profiles have fewer than 50 grade-2 candidates, so recall falls to 0.83. The weighted ranker keeps them. Its buyer-recurrence term sometimes places a notice just outside the value band above one inside it, which the labels count as an error.

That trade-off is the honest finding. The labels cannot say whether buyer recurrence helps. Answering that would need interaction events from real users who agreed to share them. The repository defines an event schema and a training entry point for that phase, disabled by default, and it refuses synthetic events whenever a run is configured to claim real propensity.

Two runs at the same commit produced byte-identical evaluation and review-queue files. The dated record, including hashes, is in `docs/evidence/pncp-release-v1-evaluation-2026-09-25.md`.

## Boundaries

The profile accepts categories and a value band, nothing that identifies a person. Every organization identifier passes a CNPJ check-digit test before it can enter the candidate set; any 11-digit value is treated as a possible CPF and dropped. Every output row states that eligibility was not assessed and that no win probability was estimated. Technical qualification, pricing, delivery capacity, and notice requirements stay with the person reading the official notice.

## Replication

```powershell
python -m pip install -e ".[release]"
make check
make reproduce
```

The next useful step is a later dataset release with deadlines and item descriptions. With those, lexical retrieval and open-opportunity constraints can run on real data, and the fixture-only parts of this project can retire.
