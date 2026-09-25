from __future__ import annotations

import argparse
from datetime import date, datetime
import json
from pathlib import Path

from .ranking import rank_opportunities


def rank_fixture(args: argparse.Namespace) -> dict:
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    opportunities = json.loads(args.opportunities.read_text(encoding="utf-8"))
    rankings = rank_opportunities(profile, opportunities, date.fromisoformat(args.as_of))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"rankings": rankings}, indent=2) + "\n", encoding="utf-8")
    return {"status": "ranked", "results": len(rankings), "output": str(args.output)}


def evaluate_release(args: argparse.Namespace) -> dict:
    from .experiment import run_experiment
    from .release import resolve_release

    release = resolve_release(args.release_dir)
    profiles = json.loads(args.profiles.read_text(encoding="utf-8"))
    report = run_experiment(release, profiles, args.output, cutoff=datetime.fromisoformat(args.cutoff))
    return {"status": "evaluated", "counts": report["counts"], "metrics": report["metrics"], "output": str(args.output)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Transparent PNCP opportunity ranking reference.")
    commands = parser.add_subparsers(dest="command", required=True)

    fixture = commands.add_parser("rank-fixture", help="rank synthetic open opportunities")
    fixture.add_argument("--profile", type=Path, required=True)
    fixture.add_argument("--opportunities", type=Path, required=True)
    fixture.add_argument("--as-of", required=True)
    fixture.add_argument("--output", type=Path, required=True)
    fixture.set_defaults(handler=rank_fixture)

    release = commands.add_parser("evaluate-release", help="evaluate rankers on the pinned PNCP Kaggle release")
    release.add_argument("--profiles", type=Path, default=Path("data/synthetic_profiles.json"))
    release.add_argument("--release-dir", type=Path, help="verified local copy; default downloads the pinned version")
    release.add_argument("--cutoff", default="2025-01-06T00:00:00")
    release.add_argument("--output", type=Path, default=Path("artifacts/release-v1"))
    release.set_defaults(handler=evaluate_release)

    args = parser.parse_args()
    print(json.dumps(args.handler(args), indent=2))


if __name__ == "__main__":
    main()
