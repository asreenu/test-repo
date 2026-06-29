from __future__ import annotations

import logging
import time
from typing import Any

from .config import config_summary
from .filters import configure_logging, filter_listings
from .http_client import HttpClient
from .models import SearchRun, utc_now_iso
from .notifier import notify_listings
from .sources import build_sources, fetch_all
from .storage import SeenStore, write_results

logger = logging.getLogger(__name__)


def run_search(config: dict[str, Any], *, verbose: bool = False) -> SearchRun:
    output_cfg = config.get("output", {})
    configure_logging(output_cfg.get("log_file"), verbose=verbose)
    started_at = utc_now_iso()

    http = HttpClient(timeout_seconds=float(config.get("request", {}).get("timeout_seconds", 30)))
    sources = build_sources(config, http)
    delay = float(config.get("request", {}).get("delay_between_sources_seconds", 1.5))

    source_results = []
    warnings: list[str] = []
    for index, source in enumerate(sources):
        logger.info("Fetching source: %s (%s)", source.name, source.tier)
        result = source.fetch()
        source_results.append(result)
        if result.error:
            warnings.append(f"{source.name}: {result.error}")
            logger.error("Source %s failed: %s", source.name, result.error)
        else:
            logger.info("Source %s returned %s listings", source.name, len(result.listings))
        warnings.extend(result.warnings)
        if index + 1 < len(sources):
            time.sleep(delay)

    all_listings = [listing for result in source_results for listing in result.listings]
    matched = filter_listings(all_listings, config)

    store = SeenStore(output_cfg.get("data_dir", "~/.mac-studio-finder"))
    _, new_listings = store.split_new(matched)
    store.save()

    finished_at = utc_now_iso()
    run = SearchRun(
        started_at=started_at,
        finished_at=finished_at,
        config_summary=config_summary(config),
        source_results=source_results,
        matched_listings=matched,
        new_listings=new_listings,
        warnings=warnings,
    )

    results_path = write_results(
        output_cfg.get("results_file", "~/.mac-studio-finder/latest_results.json"),
        run.to_dict(),
    )
    logger.info("Wrote results to %s", results_path)

    notifications = config.get("notifications", {})
    if notifications.get("macos", True):
        notify_listings(
            matched,
            only_new=bool(notifications.get("notify_only_new", True)),
            new_listings=new_listings,
        )

    return run
