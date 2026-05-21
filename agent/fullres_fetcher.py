"""Phase 3 — Re-visit a pin page and extract the full-resolution image URL."""

from __future__ import annotations

import base64
import os

from openai import AsyncOpenAI
from playwright.async_api import async_playwright

from agent.prompts import FULLRES_EXTRACTION_PROMPT

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
)

MODEL = os.getenv("AGENT_MODEL", "openai/gpt-5.4-mini")


def _upgrade_to_original(url: str) -> str:
    """Replace Pinterest CDN size prefixes with /originals/."""
    for prefix in ("/236x/", "/474x/", "/736x/"):
        url = url.replace(prefix, "/originals/")
    return url


async def fetch_full_res_url(pin_url: str) -> str:
    """Open a pin page and return the highest-resolution image URL."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(pin_url, wait_until="networkidle")
        await page.wait_for_timeout(2000)

        # Strategy 1: og:image meta tag (covers ~90% of cases)
        og_image = await page.get_attribute(
            'meta[property="og:image"]', "content"
        )
        if og_image:
            await browser.close()
            return _upgrade_to_original(og_image)

        # Strategy 2: gpt-5.4-mini reads the page visually
        screenshot = await page.screenshot(full_page=False)
        b64 = base64.b64encode(screenshot).decode()

        response = await client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}"
                            },
                        },
                        {"type": "text", "text": FULLRES_EXTRACTION_PROMPT},
                    ],
                }
            ],
        )

        await browser.close()
        return response.choices[0].message.content.strip()
