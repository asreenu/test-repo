#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from mac_studio_finder.config import load_config
from mac_studio_finder.runner import run_search


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search reputable sellers for high-memory Mac Studio listings."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).resolve().parent / "config.yaml",
        help="Path to config.yaml",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--print-json",
        action="store_true",
        help="Print full JSON results to stdout",
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config)
        run = run_search(config, verbose=args.verbose)
    except Exception as exc:  # noqa: BLE001
        print(f"Search failed: {exc}", file=sys.stderr)
        return 1

    print(f"Matched listings: {len(run.matched_listings)}")
    print(f"New listings: {len(run.new_listings)}")
    if run.warnings:
        print(f"Warnings: {len(run.warnings)}")
        for warning in run.warnings:
            print(f"  - {warning}")

    for listing in run.matched_listings[:20]:
        price = f"${listing.price:,.0f}" if listing.price is not None else "n/a"
        memory = f"{listing.memory_gb}GB" if listing.memory_gb else "RAM?"
        print(f"[{listing.tier:11}] {listing.source:16} {memory:6} {price:>10}  {listing.title[:70]}")

    if args.print_json:
        print(json.dumps(run.to_dict(), indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
