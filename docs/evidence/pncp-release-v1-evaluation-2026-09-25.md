# Offline evaluation on PNCP release v1

**Date:** 2026-09-25  
**Code commit:** `02bd7d0cdffdf906e00b795a416026a4adb479f2`  
**Dataset:** [`lucasrangelss/brazil-pncp-procurement-history`](https://www.kaggle.com/datasets/lucasrangelss/brazil-pncp-procurement-history), version 1  
**Manifest SHA-256:** `9301e83840fc575b841bcce31cff19a6b72bd37528a88fdee4b50c2fddb20c66`  
**Environment:** Windows 11, Python 3.12, public download through `kagglehub` without a Kaggle credential

## What was run

```powershell
python -m pip install -e ".[release]"
python -m pncp_recommender evaluate-release --output artifacts/run-a
python -m pncp_recommender evaluate-release --output artifacts/run-b
```

The resolver downloaded version 1, checked the manifest hash against the pinned value, and checked every layer against the manifest before loading the semantic layer. The identifier guard classified all 1,979 contracting-organization identifiers as valid CNPJ values, so no row was excluded.

Notices published before 2025-01-06 formed the history (831 rows). Buyer affinity was counted only from that history. Notices published on 2025-01-06 or 2025-01-07 were the candidates (1,148 rows). Six synthetic declared profiles in `data/synthetic_profiles.json` each chose one or two categories and a value band.

## Judgments

A candidate receives grade 2 when its category is in the profile and its estimated value is inside the band, grade 1 when only the category matches, and grade 0 otherwise. These labels are derived from the same fields the rankers can see. They measure how well a ranker respects a declared profile. They are not observed user relevance, and they cannot show recommendation quality or lift.

## Results

Mean over six profiles.

| Ranker | Recall@10 | MRR@10 | nDCG@10 | Recall@50 | nDCG@50 |
|---|---:|---:|---:|---:|---:|
| Recency, no filter | 0.1667 | 0.2431 | 0.0616 | 0.1685 | 0.0764 |
| Category and value filter, newest first | 1.0000 | 1.0000 | 1.0000 | 0.8307 | 0.9484 |
| Weighted transparent ranker | 1.0000 | 1.0000 | 0.9345 | 1.0000 | 0.9135 |

## Reading the result

The filter baseline scores a perfect nDCG@10 because its filter is the grade-2 rule. Its Recall@50 drops to 0.83 because it discards grade-1 candidates, and some profiles have fewer than 50 grade-2 candidates.

The weighted ranker keeps every category match and orders by value fit (weight 0.6), prior notices from the same buyer in the category (0.3), and recency (0.1). Buyer recurrence sometimes lifts a notice slightly outside the value band above an in-band notice, which costs nDCG against these labels. Whether buyer recurrence helps a real supplier is not answerable from this data: it would require authorized interaction events, which the project does not have.

Both runs produced identical outputs:

| File | SHA-256 |
|---|---|
| `evaluation.json` | `9bbac85522319754e10c711697e3c0384210b9aa95f9578d924242c8d457037c` |
| `review_queue.jsonl` | `35beeba0a9c65250b4083deb05a372a44cddeb42842693d2ef539e32488ab311` |

The hashes include the code commit in the lineage fields, so a run at a different commit produces different bytes.

## Limits of release v1

The release covers seven days of one modality. It has no deadline, status, location, item text, or supplier-result fields. The review queue therefore lists historical notices for similarity review, never open opportunities. Each entry names the missing evidence and links to the public PNCP notice page. Lexical and embedding baselines need item text and remain limited to the synthetic fixture path. Organization-history profiles and item-to-supplier discovery need the gated supplier-result tables.
