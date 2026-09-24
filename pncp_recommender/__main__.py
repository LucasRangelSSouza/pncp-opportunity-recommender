from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path

from .ranking import rank_opportunities


def main() -> None:
    parser = argparse.ArgumentParser(description="Transparent PNCP opportunity ranking reference.")
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--opportunities", type=Path, required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    opportunities = json.loads(args.opportunities.read_text(encoding="utf-8"))
    rankings = rank_opportunities(profile, opportunities, date.fromisoformat(args.as_of))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"rankings": rankings}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ranked", "results": len(rankings), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
