"""Entry point — starts Phase 1 scoring, then launches the review UI."""

from __future__ import annotations

import asyncio

import uvicorn
from dotenv import load_dotenv

from agent.scorer import run_scoring_phase

load_dotenv()


async def main() -> None:
    keyword = input("Search keyword for Pinterest: ")
    category = input("Product category: ")
    max_pins = int(input("Max pins to score?         [40]:  ") or 40)
    max_scrolls = int(input("Max scroll iterations?     [8]:   ") or 8)
    session_timeout = int(input("Session timeout (seconds)? [180]: ") or 180)

    print("\n🤖 Phase 1: Browsing Pinterest with guardrails active...\n")
    await run_scoring_phase(
        keyword,
        category,
        max_pins=max_pins,
        max_scrolls=max_scrolls,
        session_timeout_s=session_timeout,
    )

    print("\n✅ Scoring complete.")
    print("🌐 Opening review UI at http://localhost:8000\n")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)


asyncio.run(main())
