from __future__ import annotations

import logging
import re
from typing import Iterable

from .models import Listing

MEMORY_RE = re.compile(
    r"(?:(\d{2,4})\s*(?:gb|g\b)|(\d{2,4})\s*(?:unified\s*)?(?:memory|ram))",
    re.IGNORECASE,
)
RAM_CONTEXT_RE = re.compile(
    r"(\d{2,4})\s*(?:gb|g\b)\s*(?:unified\s*)?(?:memory|ram|ram\b)",
    re.IGNORECASE,
)


def parse_memory_gb(text: str) -> int | None:
    if not text:
        return None
    ram_values = [int(m.group(1)) for m in RAM_CONTEXT_RE.finditer(text)]
    if ram_values:
        return max(ram_values)

    values: list[int] = []
    for match in MEMORY_RE.finditer(text):
        raw = match.group(1) or match.group(2)
        if raw:
            values.append(int(raw))
    if not values:
        return None
    plausible = [v for v in values if v in {32, 36, 48, 64, 96, 128, 192, 256, 512}]
    if plausible:
        return max(plausible)
    return max(values)


def parse_price(text: str) -> float | None:
    if not text:
        return None
    match = re.search(r"[\$£€]\s*([\d,]+(?:\.\d{2})?)", text)
    if not match:
        match = re.search(r"([\d,]+(?:\.\d{2})?)", text)
    if not match:
        return None
    return float(match.group(1).replace(",", ""))


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", title).strip()


def listing_matches(
    listing: Listing,
    *,
    min_memory_gb: int,
    max_price_usd: float | None,
    chip_keywords: Iterable[str],
    exclude_title_keywords: Iterable[str],
) -> bool:
    if listing.condition == "Search link":
        return True

    title = listing.title.lower()
    if any(ex.lower() in title for ex in exclude_title_keywords):
        return False
    if "mac studio" not in title and "studio" not in title:
        # Allow Apple titles like "Refurbished Mac Studio ..."
        if "mac studio" not in listing.url.lower():
            return False

    memory = listing.memory_gb or parse_memory_gb(listing.title)
    if memory is not None and memory < min_memory_gb:
        return False

    if memory is None:
        if not any(kw.lower() in title for kw in chip_keywords):
            return False

    if max_price_usd is not None and listing.price is not None:
        # Rough FX for GBP/EUR listings when comparing to USD cap.
        price_usd = listing.price
        if listing.currency == "GBP":
            price_usd = listing.price * 1.27
        elif listing.currency == "EUR":
            price_usd = listing.price * 1.08
        if price_usd > max_price_usd:
            return False

    if listing.available is False:
        return False

    return True


def filter_listings(
    listings: Iterable[Listing],
    config: dict,
) -> list[Listing]:
    search = config.get("search", {})
    matched: list[Listing] = []
    for listing in listings:
        if listing_matches(
            listing,
            min_memory_gb=int(search.get("min_memory_gb", 128)),
            max_price_usd=search.get("max_price_usd"),
            chip_keywords=search.get("chip_keywords", []),
            exclude_title_keywords=search.get("exclude_title_keywords", []),
        ):
            if listing.memory_gb is None:
                listing.memory_gb = parse_memory_gb(listing.title)
            matched.append(listing)
    matched.sort(key=lambda item: (item.price is None, item.price or 0.0))
    return matched


def configure_logging(log_file: str | None, verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_file:
        from pathlib import Path
        import os

        path = Path(os.path.expanduser(log_file))
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(path, encoding="utf-8"))

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
