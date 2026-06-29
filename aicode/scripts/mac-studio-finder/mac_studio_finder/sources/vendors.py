from __future__ import annotations

import json
import logging
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..filters import parse_memory_gb, parse_price
from ..http_client import extract_json_object_after_marker, retry_get
from ..models import Listing
from .base import Source

logger = logging.getLogger(__name__)


class AppleRefurbSource(Source):
    name = "apple_refurb"
    tier = "reputable"

    def fetch(self):
        url = self.config.get("url", "https://www.apple.com/shop/refurbished/mac/mac-desktops")
        warnings: list[str] = []
        try:
            html = retry_get(lambda: self.http.get_text(url))
            bootstrap = extract_json_object_after_marker(html, "window.REFURB_GRID_BOOTSTRAP")
            tiles = bootstrap.get("tiles", [])
            listings: list[Listing] = []
            for tile in tiles:
                dimensions = (
                    tile.get("filters", {}).get("dimensions", {})
                    if isinstance(tile.get("filters"), dict)
                    else {}
                )
                if dimensions.get("refurbClearModel") != "macstudio":
                    continue

                title = tile.get("title") or "Refurbished Mac Studio"
                memory_raw = dimensions.get("tsMemorySize", "")
                memory_gb = parse_memory_gb(str(memory_raw)) or parse_memory_gb(title)
                price_info = tile.get("price") or {}
                raw_amount = None
                if isinstance(price_info, dict):
                    raw_amount = price_info.get("rawAmount") or price_info.get("raw_amount")
                    if raw_amount is None and "currentPrice" in price_info:
                        raw_amount = price_info["currentPrice"].get("raw_amount")
                price = float(raw_amount) if raw_amount else None
                rel_path = tile.get("productDetailsUrl") or ""
                full_url = urljoin("https://www.apple.com", rel_path)

                listings.append(
                    Listing(
                        source=self.name,
                        tier=self.tier,
                        title=title,
                        url=full_url,
                        price=price,
                        currency="USD",
                        memory_gb=memory_gb,
                        available=True,
                        condition="Apple Certified Refurbished",
                        raw={"partNumber": tile.get("partNumber"), "dimensions": dimensions},
                    )
                )

            if not listings:
                warnings.append(
                    "No Mac Studio tiles in Apple refurb feed (often out of stock)."
                )
            return self._result(listings, warnings=warnings)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Apple refurb source failed")
            return self._result(error=str(exc), warnings=warnings)


class RefurbMeSource(Source):
    name = "refurb_me"
    tier = "reputable"

    def fetch(self):
        url = self.config.get("url", "https://www.refurb.me/refurbished/mac-studio")
        warnings: list[str] = []
        try:
            html = retry_get(lambda: self.http.get_text(url))
            listings = self._parse_cards(html, base_url="https://www.refurb.me")
            if not listings:
                listings = self._parse_nuxt(html)
            if not listings:
                warnings.append("Could not parse Refurb.me cards; site layout may have changed.")
            return self._result(listings, warnings=warnings)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Refurb.me source failed")
            return self._result(error=str(exc), warnings=warnings)

    def _parse_cards(self, html: str, base_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings: list[Listing] = []
        for anchor in soup.select("a[href*='/refurbished/mac-studio']"):
            href = anchor.get("href", "")
            if "/sku/" not in href:
                continue
            text = anchor.get_text(" ", strip=True)
            if not text:
                continue
            memory_gb = parse_memory_gb(text)
            price = parse_price(text)
            listings.append(
                Listing(
                    source=self.name,
                    tier=self.tier,
                    title=text[:240],
                    url=urljoin(base_url, href),
                    price=price,
                    currency="USD",
                    memory_gb=memory_gb,
                    available="sold out" not in text.lower(),
                    condition="Refurbished",
                )
            )
        return _dedupe_listings(listings)

    def _parse_nuxt(self, html: str) -> list[Listing]:
        match = re.search(r"window\.__NUXT__=\(function\([^)]*\)\{return (\{.*?\})\}\(", html)
        if not match:
            return []
        warnings: list[str] = []
        warnings.append("Refurb.me fallback parser used.")
        # Keep fallback lightweight: extract sku links + nearby text snippets.
        listings: list[Listing] = []
        for href in set(re.findall(r'"/refurbished/mac-studio/sku/[^"]+"', html)):
            path = href.strip('"')
            idx = html.find(path)
            snippet = html[max(0, idx - 250) : idx + 350]
            text = BeautifulSoup(snippet, "html.parser").get_text(" ", strip=True)
            listings.append(
                Listing(
                    source=self.name,
                    tier=self.tier,
                    title=text[:240] or path,
                    url=urljoin("https://www.refurb.me", path),
                    price=parse_price(snippet),
                    currency="USD",
                    memory_gb=parse_memory_gb(snippet),
                    available="sold out" not in snippet.lower(),
                    condition="Refurbished",
                )
            )
        return _dedupe_listings(listings)


class ShopifySource(Source):
    """Generic Shopify products.json source."""

    def __init__(self, name: str, tier: str, config: dict, http) -> None:
        super().__init__(config, http)
        self.name = name
        self.tier = tier

    def fetch(self):
        url = self.config["shopify_products_url"]
        currency = self.config.get("currency", "USD")
        warnings: list[str] = []
        try:
            listings: list[Listing] = []
            page = 1
            while page <= 5:
                payload = self.http.get_json(url, params={"limit": 250, "page": page})
                products = payload.get("products", []) if isinstance(payload, dict) else []
                if not products:
                    break
                for product in products:
                    title = product.get("title", "")
                    if "studio" not in title.lower():
                        continue
                    if "display" in title.lower() and "mac studio" not in title.lower():
                        continue
                    handle = product.get("handle", "")
                    shop_base = re.sub(r"/products\.json$", "", url.split("/collections/")[0])
                    product_url = f"{shop_base}/products/{handle}" if handle else shop_base

                    for variant in product.get("variants", []):
                        variant_title = variant.get("title") or title
                        combined = f"{title} {variant_title} {product.get('body_html', '')}"
                        memory_gb = parse_memory_gb(combined)
                        if memory_gb is None and "configurable" not in combined.lower():
                            # Skip Shopify parent/configurator SKUs without explicit RAM.
                            if "default title" in variant_title.lower():
                                continue
                        price = float(variant.get("price")) if variant.get("price") else None
                        listings.append(
                            Listing(
                                source=self.name,
                                tier=self.tier,
                                title=combined[:240],
                                url=product_url,
                                price=price,
                                currency=currency,
                                memory_gb=memory_gb,
                                available=bool(variant.get("available")),
                                condition=self.config.get("condition"),
                                raw={"variant_id": variant.get("id")},
                            )
                        )
                if len(products) < 250:
                    break
                page += 1
            return self._result(_dedupe_listings(listings), warnings=warnings)
        except Exception as exc:  # noqa: BLE001
            logger.exception("%s source failed", self.name)
            return self._result(error=str(exc), warnings=warnings)


class HtmlSearchSource(Source):
    """Best-effort HTML search/listing parser for retailer pages."""

    def __init__(self, name: str, tier: str, config: dict, http) -> None:
        super().__init__(config, http)
        self.name = name
        self.tier = tier

    def fetch(self):
        url = self.config.get("url") or self.config.get("search_url")
        if not url:
            return self._result(error="No URL configured")
        warnings: list[str] = []
        try:
            html = retry_get(lambda: self.http.get_text(url))
            listings = self._parse_html(html, base_url=url)
            if not listings:
                warnings.append(
                    f"No parseable listings from HTML for {self.name}. "
                    "Site may require a home IP or layout changed."
                )
            return self._result(listings, warnings=warnings)
        except Exception as exc:  # noqa: BLE001
            logger.exception("%s source failed", self.name)
            fallback = self._search_link_fallback(url)
            if fallback:
                warnings.append(f"{self.name} fetch failed ({exc}); included manual search link.")
                return self._result([fallback], warnings=warnings)
            return self._result(error=str(exc), warnings=warnings)

    def _search_link_fallback(self, url: str) -> Listing | None:
        if self.tier != "acceptable":
            return None
        return Listing(
            source=self.name,
            tier=self.tier,
            title=f"Manual search link ({self.name})",
            url=url,
            price=None,
            currency="USD",
            memory_gb=None,
            available=True,
            condition="Search link",
        )

    def _parse_html(self, html: str, base_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings: list[Listing] = []
        for anchor in soup.find_all("a", href=True):
            text = anchor.get_text(" ", strip=True)
            href = anchor["href"]
            blob = f"{text} {href}"
            lower = blob.lower()
            if "mac studio" not in lower and "studio" not in lower:
                continue
            if "display" in lower and "mac studio" not in lower:
                continue
            memory_gb = parse_memory_gb(blob)
            if memory_gb is None and "128" not in lower and "192" not in lower:
                continue
            price = parse_price(text)
            listings.append(
                Listing(
                    source=self.name,
                    tier=self.tier,
                    title=text[:240] or href,
                    url=urljoin(base_url, href),
                    price=price,
                    currency="USD",
                    memory_gb=memory_gb,
                    available="sold out" not in lower,
                )
            )
        return _dedupe_listings(listings)


class EbaySource(Source):
    name = "ebay"
    tier = "acceptable"

    def fetch(self):
        app_id = self.config.get("app_id") or __import__("os").environ.get("EBAY_APP_ID")
        warnings: list[str] = []
        if app_id:
            try:
                return self._fetch_api(app_id)
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"eBay API failed: {exc}")

        search_url = self.config.get("search_url")
        if not search_url:
            return self._result(error="No eBay search URL configured", warnings=warnings)

        try:
            html = retry_get(lambda: self.http.get_text(search_url))
            if "captcha" in html.lower() or "error page" in html.lower():
                warnings.append(
                    "eBay blocked automated HTML fetch. Set EBAY_APP_ID for API access."
                )
                return self._result(
                    [
                        Listing(
                            source=self.name,
                            tier=self.tier,
                            title="Manual eBay search (automated fetch blocked)",
                            url=search_url,
                            price=None,
                            currency="USD",
                            memory_gb=None,
                            available=True,
                            condition="Search link",
                        )
                    ],
                    warnings=warnings,
                )
            parser = HtmlSearchSource(self.name, self.tier, {"url": search_url}, self.http)
            listings = parser._parse_html(html, base_url="https://www.ebay.com")
            return self._result(listings, warnings=warnings)
        except Exception as exc:  # noqa: BLE001
            logger.exception("eBay source failed")
            if search_url:
                warnings.append(f"eBay fetch failed ({exc}); included manual search link.")
                return self._result(
                    [
                        Listing(
                            source=self.name,
                            tier=self.tier,
                            title="Manual eBay search (set EBAY_APP_ID for API)",
                            url=search_url,
                            price=None,
                            currency="USD",
                            memory_gb=None,
                            available=True,
                            condition="Search link",
                        )
                    ],
                    warnings=warnings,
                )
            return self._result(error=str(exc), warnings=warnings)

    def _fetch_api(self, app_id: str):
        query = self.config.get(
            "query",
            "mac studio (128gb,192gb,256gb) (m2 ultra,m3 ultra,m4 max)",
        )
        url = "https://svcs.ebay.com/services/search/FindingService/v1"
        params = {
            "OPERATION-NAME": "findItemsAdvanced",
            "SERVICE-VERSION": "1.0.0",
            "SECURITY-APPNAME": app_id,
            "RESPONSE-DATA-FORMAT": "JSON",
            "REST-PAYLOAD": "",
            "keywords": query,
            "paginationInput.entriesPerPage": "50",
            "itemFilter(0).name": "ListingType",
            "itemFilter(0).value": "FixedPrice",
            "itemFilter(1).name": "MinPrice",
            "itemFilter(1).value": "1500",
            "itemFilter(2).name": "MaxPrice",
            "itemFilter(2).value": str(self.config.get("max_price", 8000)),
            "sortOrder": "StartTimeNewest",
        }
        payload = self.http.get_json(url, params=params)
        items = (
            payload.get("findItemsAdvancedResponse", [{}])[0]
            .get("searchResult", [{}])[0]
            .get("item", [])
        )
        listings: list[Listing] = []
        for item in items:
            title = item.get("title", [""])[0]
            view_url = item.get("viewItemURL", [""])[0]
            price_value = item.get("sellingStatus", [{}])[0].get("currentPrice", [{}])[0].get("__value__")
            listings.append(
                Listing(
                    source=self.name,
                    tier=self.tier,
                    title=title,
                    url=view_url,
                    price=float(price_value) if price_value else None,
                    currency="USD",
                    memory_gb=parse_memory_gb(title),
                    available=True,
                    condition=item.get("condition", [{}])[0].get("conditionDisplayName", [None])[0],
                )
            )
        return self._result(_dedupe_listings(listings))


def _dedupe_listings(listings: list[Listing]) -> list[Listing]:
    seen: set[str] = set()
    unique: list[Listing] = []
    for listing in listings:
        key = listing.listing_id
        if key in seen:
            continue
        seen.add(key)
        unique.append(listing)
    return unique
