from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Listing:
    source: str
    tier: str
    title: str
    url: str
    price: float | None
    currency: str
    memory_gb: int | None
    available: bool | None
    condition: str | None = None
    raw: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def listing_id(self) -> str:
        return f"{self.source}|{self.url}|{self.title}|{self.price}|{self.memory_gb}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourceResult:
    source: str
    tier: str
    listings: list[Listing]
    warnings: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass(slots=True)
class SearchRun:
    started_at: str
    finished_at: str
    config_summary: dict[str, Any]
    source_results: list[SourceResult]
    matched_listings: list[Listing]
    new_listings: list[Listing]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "config_summary": self.config_summary,
            "source_results": [
                {
                    "source": r.source,
                    "tier": r.tier,
                    "ok": r.ok,
                    "error": r.error,
                    "warnings": r.warnings,
                    "listing_count": len(r.listings),
                    "listings": [l.to_dict() for l in r.listings],
                }
                for r in self.source_results
            ],
            "matched_listings": [l.to_dict() for l in self.matched_listings],
            "new_listings": [l.to_dict() for l in self.new_listings],
            "warnings": self.warnings,
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
