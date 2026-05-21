"""Phase 1 — Thumbnail scoring pipeline using gpt-5.4-mini."""

from __future__ import annotations

import asyncio
import base64
import json
import os

from openai import AsyncOpenAI
from playwright.async_api import async_playwright

from agent.guardrails import BrowsingGuardrail
from agent.prompts import THUMBNAIL_SCORING_PROMPT

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY", ""),
)

MODEL = os.getenv("AGENT_MODEL", "openai/gpt-5.4-mini")


async def score_thumbnail(img_bytes: bytes, category: str) -> dict:
    """Send a thumbnail screenshot to the vision model and return a score."""
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
    max_scrolls: int = 8,
    session_timeout_s: int = 180,
) -> list[dict]:
    """Browse Pinterest, scroll the feed, screenshot & score each pin card."""

    guard = BrowsingGuardrail(
        max_pins=max_pins,
        max_scrolls=max_scrolls,
        session_timeout_s=session_timeout_s,
        max_error_streak=5,
        max_stale_scrolls=2,
    )

    results: list[dict] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto("https://www.pinterest.com")
        await page.wait_for_timeout(2000)
        await page.fill('[data-test-id="search-box-input"]', keyword)
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000)

        # ── Scroll loop with guardrail ───────────────────────────────
        while not guard.should_stop:
            pin_cards = await page.query_selector_all('[data-test-id="pin"]')
            guard.record_scroll(len(pin_cards))

            print(
                f"  [scroll {guard._scroll_count}] "
                f"{len(pin_cards)} pins visible  |  {guard.status_line()}"
            )

            if guard.should_stop:
                break

            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1500)

        # ── Pin scoring loop ─────────────────────────────────────────
        pin_cards = await page.query_selector_all('[data-test-id="pin"]')
        print(
            f"\nScoring up to {max_pins} pins from "
            f"{len(pin_cards)} visible...\n"
        )

        for i, card in enumerate(pin_cards):
            if guard.should_stop:
                print(f"\n⛔ Stopped: {guard.stop_reason}")
                break

            try:
                img_el = await card.query_selector("img")
                thumbnail_url = (
                    await img_el.get_attribute("src") if img_el else None
                )

                link_el = await card.query_selector("a")
                pin_href = (
                    await link_el.get_attribute("href") if link_el else None
                )
                pin_url = (
                    f"https://www.pinterest.com{pin_href}"
                    if pin_href
                    else None
                )

                if not thumbnail_url or not pin_url:
                    guard.record_error()
                    continue

                img_bytes = await card.screenshot()
                score_result = await score_thumbnail(img_bytes, category)

                results.append(
                    {
                        "id": i + 1,
                        "thumbnail_url": thumbnail_url,
                        "pin_url": pin_url,
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
                await asyncio.sleep(0.5)

            except Exception as e:
                guard.record_error()
                print(
                    f"  [{i + 1}] Error: {e}  "
                    f"(streak={guard._error_streak})"
                )
                continue

        await browser.close()

    print(f"\n✅ Finished — {guard.stop_reason or 'all pins scored'}")
    print(f"   {guard.status_line()}")

    os.makedirs("data", exist_ok=True)
    with open("data/scored_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"   Saved {len(results)} results to data/scored_results.json")
    return results
