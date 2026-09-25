import hashlib
import json
from datetime import datetime
from pathlib import Path
import tempfile
import unittest

import pyarrow as pa
import pyarrow.parquet as pq

from pncp_recommender.evaluation import evaluate_at_k
from pncp_recommender.experiment import run_experiment
from pncp_recommender.identifiers import classify_identifier
from pncp_recommender.learning_to_rank import LearningToRankDisabled, train
from pncp_recommender.notices import (
    Notice,
    buyer_affinity,
    graded_judgments,
    rank_metadata_filter,
    rank_weighted,
    validate_declared_profile,
    value_fit,
)
from pncp_recommender.release import PinnedRelease, ReleaseVerificationError, resolve_release, verify_release

VALID_CNPJ = "11222333000181"
OTHER_CNPJ = "11444777000161"
PROFILE = {"profile_id": "p", "categories": ["health"], "min_value": 1000, "max_value": 10000, "synthetic": True}


def notice(notice_id, category="health", value=5000.0, day=6, org=VALID_CNPJ):
    return Notice(notice_id, org, "MUNICIPIO TESTE", category, value, datetime(2025, 1, day, 10), 2025, 1)


def build_release(directory: Path, rows: list[dict]) -> PinnedRelease:
    table = pa.Table.from_pylist(rows)
    files = []
    for layer in ("raw", "trusted", "semantic"):
        path = directory / f"{layer}_records.parquet"
        pq.write_table(table, path)
        files.append({"path": f"{layer}/records.parquet", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {"files": files, "git_commit": "abc", "privacy_gate": "passed", "schema_version": "1.1"}
    manifest_path = directory / "release_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    return PinnedRelease("owner/test", 1, hashlib.sha256(manifest_path.read_bytes()).hexdigest(), "1.1")


def release_row(notice_id, org, category, value, published):
    return {
        "id": notice_id, "contracting_organization_id": org, "contracting_organization_name": "MUNICIPIO TESTE",
        "procurement_category": category, "estimated_value": value, "published_at": published,
        "procurement_year": 2025, "procurement_sequence": 7,
    }


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.pin = build_release(self.dir, [
            release_row("h1", VALID_CNPJ, "health", 5000.0, "2025-01-02T09:00:00"),
            release_row("c1", VALID_CNPJ, "health", 5000.0, "2025-01-06T09:00:00"),
            release_row("c2", OTHER_CNPJ, "health", 90000.0, "2025-01-07T09:00:00"),
            release_row("c3", "12345678901", "health", 5000.0, "2025-01-07T09:00:00"),
        ])

    def tearDown(self):
        self.tmp.cleanup()

    def test_verified_release_resolves_without_network(self):
        release = resolve_release(self.dir, self.pin, downloader=lambda handle: self.fail("network used"))
        self.assertEqual(release.lineage()["dataset_version"], 1)

    def test_unapproved_manifest_is_rejected(self):
        other = PinnedRelease("owner/test", 2, "0" * 64, "1.1")
        with self.assertRaisesRegex(ReleaseVerificationError, "not the approved"):
            verify_release(self.dir, other)

    def test_altered_layer_is_rejected(self):
        with (self.dir / "semantic_records.parquet").open("ab") as handle:
            handle.write(b"x")
        with self.assertRaisesRegex(ReleaseVerificationError, "hash mismatch"):
            verify_release(self.dir, self.pin)

    def test_experiment_excludes_non_organizations_and_records_lineage(self):
        report = run_experiment(verify_release(self.dir, self.pin), [PROFILE], self.dir / "out")
        self.assertEqual(report["counts"]["excluded_non_organization_rows"], 1)
        self.assertEqual(report["counts"]["history_rows"], 1)
        self.assertEqual(report["counts"]["candidate_rows"], 2)
        queue = [json.loads(line) for line in (self.dir / "out" / "review_queue.jsonl").read_text().splitlines()]
        self.assertEqual([row["notice_id"] for row in queue], ["c1", "c2"])
        self.assertEqual(queue[0]["lineage"]["manifest_sha256"], self.pin.manifest_sha256)
        self.assertEqual(queue[0]["evidence"]["buyer_prior_notices_in_category"], 1)

    def test_experiment_is_deterministic(self):
        release = verify_release(self.dir, self.pin)
        first = run_experiment(release, [PROFILE], self.dir / "a")
        second = run_experiment(release, [PROFILE], self.dir / "b")
        self.assertEqual(first["review_queue"]["sha256"], second["review_queue"]["sha256"])
        self.assertEqual(first["metrics"], second["metrics"])


class RankingTests(unittest.TestCase):
    def test_category_is_a_hard_constraint_with_explained_scores(self):
        ranked = rank_weighted(PROFILE, [notice("a"), notice("b", category="transport")])
        self.assertEqual([row["notice_id"] for row in ranked], ["a"])
        self.assertEqual(set(ranked[0]["contributions"]), {"value_fit", "buyer_affinity", "recency"})
        self.assertIn("deadline", ranked[0]["missing_evidence"])
        self.assertEqual(ranked[0]["record_type"], "historical_notice")
        self.assertTrue(ranked[0]["win_probability_not_estimated"])

    def test_buyer_affinity_uses_only_history(self):
        history = [notice("h", day=2, org=OTHER_CNPJ)]
        ranked = rank_weighted(PROFILE, [notice("a"), notice("b", org=OTHER_CNPJ)], buyer_affinity(history))
        self.assertEqual(ranked[0]["notice_id"], "b")

    def test_value_fit_decays_by_order_of_magnitude(self):
        self.assertEqual(value_fit(5000, 1000, 10000), 1.0)
        self.assertEqual(value_fit(100000, 1000, 10000), 0.0)
        self.assertAlmostEqual(value_fit(31622.7766, 1000, 10000), 0.5, places=4)

    def test_metadata_filter_drops_out_of_band_values(self):
        self.assertEqual(rank_metadata_filter(PROFILE, [notice("a", value=50.0)]), [])

    def test_profile_rejects_identity_fields_and_unknown_categories(self):
        with self.assertRaisesRegex(ValueError, "unsupported fields"):
            validate_declared_profile({**PROFILE, "cpf": "123"})
        with self.assertRaisesRegex(ValueError, "subset"):
            validate_declared_profile({**PROFILE, "categories": ["weapons"]})

    def test_graded_judgments(self):
        grades = graded_judgments(PROFILE, [notice("a"), notice("b", value=1e6), notice("c", category="other")])
        self.assertEqual(grades, {"a": 2, "b": 1})


class EvaluationTests(unittest.TestCase):
    def test_graded_ndcg_prefers_higher_grade_first(self):
        grades = {"a": 2, "b": 1}
        self.assertEqual(evaluate_at_k(["a", "b"], grades, 10)["ndcg"], 1.0)
        self.assertLess(evaluate_at_k(["b", "a"], grades, 10)["ndcg"], 1.0)

    def test_recall_at_k_is_bounded_by_k(self):
        self.assertEqual(evaluate_at_k(["a"], {"a": 2, "b": 2}, 1)["recall"], 1.0)


class IdentifierTests(unittest.TestCase):
    def test_classification(self):
        self.assertEqual(classify_identifier(VALID_CNPJ), "organization")
        self.assertEqual(classify_identifier("11.222.333/0001-81"), "organization")
        self.assertEqual(classify_identifier("12345678901"), "natural_person")
        self.assertEqual(classify_identifier("11222333000182"), "unknown")
        self.assertEqual(classify_identifier("00000000000000"), "unknown")


class LearningToRankTests(unittest.TestCase):
    EVENT = {"event_id": "e", "profile_id": "p", "notice_id": "n", "event_type": "open",
             "occurred_at": "2026-01-01", "source": "synthetic", "consent_basis": ""}

    def test_disabled_by_default(self):
        with self.assertRaises(LearningToRankDisabled):
            train([self.EVENT])

    def test_synthetic_events_cannot_claim_real_propensity(self):
        with self.assertRaisesRegex(ValueError, "synthetic"):
            train([self.EVENT], enabled=True, claim_real_propensity=True)

    def test_synthetic_run_is_labelled(self):
        self.assertIn("synthetic", train([self.EVENT], enabled=True)["label"])

    def test_real_events_need_consent(self):
        with self.assertRaisesRegex(ValueError, "consent"):
            train([{**self.EVENT, "source": "app"}], enabled=True)


if __name__ == "__main__":
    unittest.main()
