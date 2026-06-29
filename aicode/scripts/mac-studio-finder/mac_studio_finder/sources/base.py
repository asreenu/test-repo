from __future__ import annotations

from abc import ABC, abstractmethod

from ..http_client import HttpClient
from ..models import Listing, SourceResult


class Source(ABC):
    name: str
    tier: str

    def __init__(self, config: dict, http: HttpClient) -> None:
        self.config = config
        self.http = http

    @abstractmethod
    def fetch(self) -> SourceResult:
        raise NotImplementedError

    def _result(
        self,
        listings: list[Listing] | None = None,
        *,
        warnings: list[str] | None = None,
        error: str | None = None,
    ) -> SourceResult:
        return SourceResult(
            source=self.name,
            tier=self.tier,
            listings=listings or [],
            warnings=warnings or [],
            error=error,
        )
