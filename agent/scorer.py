"""Phase 1 — Thumbnail scoring pipeline using Scrapling + gpt-5.4-mini.

Uses Scrapling's StealthyFetcher to browse Pinterest (with anti-bot bypass),
extract pin thumbnail URLs, then downloads and scores each image.
"""

from __future__ import annotations

import asyncio
import base64
import json
import os

import httpx
from openai import AsyncOpenAI
from scrapling.fetchers import StealthyFetcher

from agent.guardrails import BrowsingGuardrail
from agent.prompts import THUMBNAIL_SCORING_PROMPT

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
)

MODEL = os.getenv("AGENT_MODEL", "openai/gpt-5.4-mini")


async def score_thumbnail(img_bytes: bytes, category: str) -> dict:
    """Send a thumbnail image to the vision model and return a score."""
    b64 = base64.b64encode(img_bytes).decode()
    prompt = THUMBNAIL_SCORING_PROMPT.format(category=category)

    response = await client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    )
    return json.loads(response.choices[0].message.content)


async def run_scoring_phase(
    keyword: str,
    category: str,
    max_pins: int = 40,
    session_timeout_s: int = 180,
) -> list[dict]:
    """Use Scrapling to browse Pinterest, extract pin data, and score thumbnails."""

    guard = BrowsingGuardrail(
        max_pins=max_pins,
        session_timeout_s=session_timeout_s,
        max_error_streak=5,
    )

    collected_pins: list[dict] = []

    async def extract_pins(page):
        """Extract pin data from the rendered Pinterest page."""
        await page.wait_for_timeout(3000)

        pin_cards = await page.query_selector_all('[data-test-id="pin"]')
        print(f"  Found {len(pin_cards)} pin cards on page")

        for card in pin_cards[:max_pins]:
            try:
                img_el = await card.query_selector("img")
                thumb_url = (
                    await img_el.get_attribute("src") if img_el else None
                )

                link_el = await card.query_selector("a")
                href = (
                    await link_el.get_attribute("href") if link_el else None
                )
                pin_url = (
                    f"https://www.pinterest.com{href}" if href else None
                )

                if thumb_url and pin_url:
                    collected_pins.append(
                        {"thumbnail_url": thumb_url, "pin_url": pin_url}
                    )
            except Exception:
                continue

    search_url = (
        f"https://www.pinterest.com/search/pins/"
        f"?q={keyword.replace(' ', '+')}"
    )

    print(f"  Fetching {search_url} with Scrapling StealthyFetcher...")
    await StealthyFetcher.async_fetch(
        search_url,
        headless=True,
        network_idle=True,
        page_action=extract_pins,
        timeout=session_timeout_s * 1000,
    )

    print(f"\n  Extracted {len(collected_pins)} pins. Scoring with {MODEL}...\n")

    results: list[dict] = []

    async with httpx.AsyncClient() as http:
        for i, pin in enumerate(collected_pins):
            if guard.should_stop:
                print(f"\n  Stopped: {guard.stop_reason}")
                break

            try:
                img_resp = await http.get(pin["thumbnail_url"])
                img_bytes = img_resp.content
                score_result = await score_thumbnail(img_bytes, category)

                results.append(
                    {
                        "id": i + 1,
                        "thumbnail_url": pin["thumbnail_url"],
                        "pin_url": pin["pin_url"],
                        "full_res_url": None,
                        "score": score_result["score"],
                        "reason": score_result["reason"],
                        "approve": score_result["approve"],
                        "selected": False,
                        "poster_path": None,
                    }
                )

                guard.record_pin_collected()
                print(
                    f"  [{guard._pins_collected}/{max_pins}] "
                    f"Score {score_result['score']}/10 — "
                    f"{score_result['reason']}"
                )
                await asyncio.sleep(0.3)

            except Exception as e:
                guard.record_error()
                print(
                    f"  [{i + 1}] Error: {e}  "
                    f"(streak={guard._error_streak})"
                )
                continue

    print(f"\n  Finished — {guard.stop_reason or 'all pins scored'}")
    print(f"   {guard.status_line()}")

    os.makedirs("data", exist_ok=True)
    with open("data/scored_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"   Saved {len(results)} results to data/scored_results.json")
    return results
