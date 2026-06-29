from __future__ import annotations

import json
from pathlib import Path

from .config import expand_path
from .models import Listing


class SeenStore:
    def __init__(self, data_dir: str) -> None:
        self.data_dir = expand_path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.seen_path = self.data_dir / "seen_listings.json"
        self._seen: set[str] = set()
        self._load()

    def _load(self) -> None:
        if not self.seen_path.exists():
            return
        with self.seen_path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        self._seen = set(payload.get("seen_ids", []))

    def save(self) -> None:
        with self.seen_path.open("w", encoding="utf-8") as fh:
            json.dump({"seen_ids": sorted(self._seen)}, fh, indent=2)

    def split_new(self, listings: list[Listing]) -> tuple[list[Listing], list[Listing]]:
        new_items: list[Listing] = []
        for listing in listings:
            if listing.listing_id not in self._seen:
                new_items.append(listing)
            self._seen.add(listing.listing_id)
        return listings, new_items


def write_results(path: str, payload: dict) -> Path:
    output_path = expand_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return output_path
