"""Browser agent setup — thin wrapper around Scrapling's StealthyFetcher.

Provides a convenience helper for one-off page visits with anti-bot bypass.
The main scraping loops in scorer.py and fullres_fetcher.py call
StealthyFetcher directly via page_action callbacks.
"""

from __future__ import annotations

from scrapling.fetchers import StealthyFetcher


async def fetch_page(url: str, **kwargs):
    """Fetch a page using StealthyFetcher with sensible defaults."""
    defaults = {
        "headless": True,
        "network_idle": True,
    }
    defaults.update(kwargs)
    return await StealthyFetcher.async_fetch(url, **defaults)
