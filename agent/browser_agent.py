"""Browser-use agent setup — thin wrapper around Playwright lifecycle."""

from __future__ import annotations

from playwright.async_api import Browser, BrowserContext, async_playwright


async def launch_browser(headless: bool = False) -> tuple[Browser, BrowserContext]:
    """Launch a Chromium instance and return (browser, context)."""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=headless)
    context = await browser.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
    )
    return browser, context
