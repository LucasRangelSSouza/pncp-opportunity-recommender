# Evaluating a transparent procurement-opportunity ranking system

A procurement opportunity list becomes misleading when it hides the reason an item appears at the top. This reference implementation keeps the ranking deliberately small. It compares terms from an organization-level category profile with the item description, then adds declared modality and state matches. Every result keeps the terms and constraints that contributed to the score.

The implementation filters out closed opportunities and opportunities whose deadline has passed. It does not silently substitute a similar item when lexical evidence is absent. A locality or modality match can still surface a record for review, but the explanation shows that the item terms did not match.

The profile accepts an organization identifier and declared categories. It rejects personal fields such as CPF, email, phone, address, and person name. This is a boundary for the example, not evidence that a user is eligible to bid. Eligibility, technical qualification, pricing, delivery capacity, tax treatment, and notice requirements remain outside the ranking function.

The offline evaluator calculates Recall and mean reciprocal rank from a labeled relevance set. The fixture proves the calculation only. A public benchmark will need documented PNCP source records, a label protocol, and a pinned dataset version before any quality figure appears in the project documentation.
