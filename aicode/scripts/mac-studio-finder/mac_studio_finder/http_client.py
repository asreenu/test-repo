from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Callable

import requests

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


class HttpClient:
    def __init__(self, timeout_seconds: float = 30.0) -> None:
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)

    def get_text(self, url: str, *, params: dict | None = None) -> str:
        response = self.session.get(
            url,
            params=params,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.text

    def get_json(self, url: str, *, params: dict | None = None) -> dict | list:
        response = self.session.get(
            url,
            params=params,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        return response.json()


def retry_get(fetch: Callable[[], str], *, attempts: int = 3, pause: float = 2.0) -> str:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return fetch()
        except Exception as exc:  # noqa: BLE001 - surface source-level failures
            last_error = exc
            logger.warning("Fetch attempt %s failed: %s", attempt, exc)
            if attempt < attempts:
                time.sleep(pause * attempt)
    raise RuntimeError(str(last_error))


def extract_json_object_after_marker(html: str, marker: str) -> dict:
    start = html.find(marker)
    if start < 0:
        raise ValueError(f"Marker not found: {marker}")
    eq = html.find("=", start)
    if eq < 0:
        raise ValueError(f"Assignment not found after marker: {marker}")

    depth = 0
    started = False
    for idx in range(eq + 1, len(html)):
        char = html[idx]
        if char == "{":
            depth += 1
            started = True
        elif char == "}":
            depth -= 1
            if started and depth == 0:
                blob = html[eq + 1 : idx + 1].strip()
                if blob.endswith(";"):
                    blob = blob[:-1]
                return json.loads(blob)
    raise ValueError(f"Could not parse JSON object for marker: {marker}")
