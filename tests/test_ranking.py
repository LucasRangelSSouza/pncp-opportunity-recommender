import unittest
from datetime import date

from pncp_recommender.ranking import evaluate_rankings, rank_opportunities, validate_profile


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"organization_id": "org", "categories": ["office paper"], "modalities": ["pregao"], "states": ["GO"]}
        self.items = [
            {"id": "a", "item": "office paper", "status": "open", "deadline": "2026-10-01", "modality": "pregao", "state": "GO", "source_record_url": "https://pncp.gov.br/a"},
            {"id": "b", "item": "office chair", "status": "closed", "deadline": "2026-10-01", "modality": "pregao", "state": "GO", "source_record_url": "https://pncp.gov.br/b"},
        ]

    def test_ranking_is_deterministic_and_labels_safety_boundary(self):
        ranked = rank_opportunities(self.profile, self.items, date(2026, 9, 24))
        self.assertEqual([row["opportunity_id"] for row in ranked], ["a"])
        self.assertTrue(ranked[0]["review_required"])
        self.assertTrue(ranked[0]["eligibility_not_assessed"])

    def test_profile_rejects_personal_fields(self):
        with self.assertRaisesRegex(ValueError, "prohibited"):
            validate_profile({"organization_id": "org", "categories": [], "cpf": "00000000000"})

    def test_offline_metrics_are_computed(self):
        metrics = evaluate_rankings({"q": ["a", "b"]}, {"q": {"a"}})
        self.assertEqual(metrics, {"recall_at_all": 1.0, "mrr": 1.0})


if __name__ == "__main__":
    unittest.main()
