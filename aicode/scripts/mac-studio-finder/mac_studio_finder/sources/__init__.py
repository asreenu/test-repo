from __future__ import annotations

from ..http_client import HttpClient
from ..models import SourceResult
from .base import Source
from .vendors import (
    AppleRefurbSource,
    EbaySource,
    HtmlSearchSource,
    RefurbMeSource,
    ShopifySource,
)


def build_sources(config: dict, http: HttpClient) -> list[Source]:
    source_config = config.get("sources", {})
    built: list[Source] = []

    factory_map = {
        "apple_refurb": lambda cfg: AppleRefurbSource(cfg, http),
        "refurb_me": lambda cfg: RefurbMeSource(cfg, http),
        "techable": lambda cfg: ShopifySource("techable", "reputable", cfg, http),
        "hoxton_macs": lambda cfg: ShopifySource("hoxton_macs", "reputable", cfg, http),
        "ipowerresale": lambda cfg: ShopifySource("ipowerresale", "reputable", cfg, http),
        "mac_of_all_trades": lambda cfg: HtmlSearchSource(
            "mac_of_all_trades", "reputable", cfg, http
        ),
        "back_market": lambda cfg: HtmlSearchSource("back_market", "acceptable", cfg, http),
        "swappa": lambda cfg: HtmlSearchSource("swappa", "acceptable", cfg, http),
        "adorama_used": lambda cfg: HtmlSearchSource("adorama_used", "acceptable", cfg, http),
        "ebay": lambda cfg: EbaySource(cfg, http),
    }

    for name, cfg in source_config.items():
        if not cfg.get("enabled", True):
            continue
        factory = factory_map.get(name)
        if factory is None:
            continue
        source = factory(cfg)
        source.tier = cfg.get("tier", source.tier)
        built.append(source)

    # Sort reputable first, then acceptable.
    tier_order = {"reputable": 0, "acceptable": 1}
    built.sort(key=lambda src: tier_order.get(src.tier, 9))
    return built


def fetch_all(sources: list[Source]) -> list[SourceResult]:
    results: list[SourceResult] = []
    for source in sources:
        results.append(source.fetch())
    return results
