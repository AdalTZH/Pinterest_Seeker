"""Phase 3 — Re-visit a pin page and extract the full-resolution image URL.

Uses Scrapling's StealthyFetcher for anti-bot bypass when visiting pin pages.
"""

from __future__ import annotations

import base64
import os

from openai import AsyncOpenAI
from scrapling.fetchers import StealthyFetcher

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
    result: dict = {"url": None, "screenshot": None}

    async def extract(page):
        """Extract og:image or take screenshot for fallback."""
        og_image = await page.get_attribute(
            'meta[property="og:image"]', "content"
        )
        if og_image:
            result["url"] = _upgrade_to_original(og_image)
        else:
            result["screenshot"] = await page.screenshot(full_page=False)

    await StealthyFetcher.async_fetch(
        pin_url,
        headless=True,
        network_idle=True,
        page_action=extract,
    )

    if result["url"]:
        return result["url"]

    # Fallback: gpt-5.4-mini reads the page visually
    b64 = base64.b64encode(result["screenshot"]).decode()

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
    return response.choices[0].message.content.strip()
