from __future__ import annotations

import logging
import platform
import subprocess
import textwrap

from .models import Listing

logger = logging.getLogger(__name__)


def notify_macos(title: str, message: str) -> None:
    if platform.system() != "Darwin":
        logger.info("Skipping macOS notification on %s", platform.system())
        return
    safe_title = title.replace('"', "'")
    safe_message = message.replace('"', "'")
    script = f'display notification "{safe_message}" with title "{safe_title}"'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        logger.warning("macOS notification failed: %s", exc.stderr or exc)


def format_listing_line(listing: Listing) -> str:
    price = f"${listing.price:,.0f}" if listing.price is not None else "price n/a"
    memory = f"{listing.memory_gb}GB" if listing.memory_gb else "RAM n/a"
    return f"[{listing.tier}] {listing.source}: {listing.title[:90]} — {memory}, {price}"


def notify_listings(listings: list[Listing], *, only_new: bool, new_listings: list[Listing]) -> None:
    target = new_listings if only_new else listings
    if not target:
        notify_macos("Mac Studio Finder", "No new matching listings today.")
        return

    lines = [format_listing_line(item) for item in target[:8]]
    body = "\n".join(lines)
    if len(target) > 8:
        body += f"\n…and {len(target) - 8} more (see latest_results.json)"
    notify_macos(
        f"Mac Studio Finder ({len(target)} new)",
        textwrap.shorten(body, width=250, placeholder="…"),
    )
