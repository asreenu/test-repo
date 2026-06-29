from mac_studio_finder.filters import listing_matches, parse_memory_gb
from mac_studio_finder.models import Listing


def test_parse_memory_gb():
    assert parse_memory_gb("Mac Studio M2 Ultra 128GB RAM 2TB") == 128
    assert parse_memory_gb("512GB SSD 128GB unified memory") == 128


def test_listing_matches_high_memory():
    listing = Listing(
        source="test",
        tier="reputable",
        title="Mac Studio M2 Ultra 128GB 2TB",
        url="https://example.com",
        price=3999.0,
        currency="USD",
        memory_gb=128,
        available=True,
    )
    assert listing_matches(
        listing,
        min_memory_gb=128,
        max_price_usd=5500,
        chip_keywords=["m2 ultra"],
        exclude_title_keywords=["display"],
    )


def test_search_link_always_included():
    listing = Listing(
        source="ebay",
        tier="acceptable",
        title="Manual eBay search",
        url="https://ebay.com/sch/...",
        price=None,
        currency="USD",
        memory_gb=None,
        available=True,
        condition="Search link",
    )
    assert listing_matches(
        listing,
        min_memory_gb=128,
        max_price_usd=5500,
        chip_keywords=[],
        exclude_title_keywords=[],
    )
