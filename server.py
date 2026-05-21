"""FastAPI app — drives the full pipeline from the browser UI.

Flow:
  1. User opens /, sees a search form
  2. User types a product keyword → POST /api/search
  3. Server runs Phase 1 scoring in a background task
  4. UI polls GET /api/search/status for progress
  5. Once done, UI loads scored results via GET /api/results
  6. User selects images → POST /api/generate triggers Phase 3
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.fullres_fetcher import fetch_full_res_url
from agent.scorer import run_scoring_phase
from poster.nano_banana import generate_poster

app = FastAPI(title="Pinterest Poster Agent")

DATA_FILE = Path("data/scored_results.json")

app.mount("/output", StaticFiles(directory="output"), name="output")


# ── Warmup StealthyFetcher on startup ────────────────────────────────

async def _warmup_task():
    """Pre-launch camoufox so the first search doesn't wait 30-90s."""
    from scrapling.fetchers import StealthyFetcher

    async def _noop(page):
        pass

    try:
        print("[warmup] Pre-launching stealth browser...")
        await StealthyFetcher.async_fetch(
            "https://www.google.com",
            headless=True,
            page_action=_noop,
            timeout=60_000,
        )
        print("[warmup] Stealth browser ready.")
    except Exception as e:
        print(f"[warmup] Browser warmup failed (non-fatal): {e}")


@app.on_event("startup")
async def _schedule_warmup():
    asyncio.create_task(_warmup_task())


# ── In-memory search state ───────────────────────────────────────────

_search_state: dict = {
    "status": "idle",       # idle | searching | done | error
    "keyword": "",
    "category": "",
    "progress": "",
    "error": None,
    "images_ready": False,
}


# ── Models ───────────────────────────────────────────────────────────


class SearchRequest(BaseModel):
    keyword: str
    category: str = ""
    max_pins: int = 40
    session_timeout_s: int = 180


class GenerateRequest(BaseModel):
    selected_ids: list[int]


# ── Background scoring task ──────────────────────────────────────────


async def _run_search(req: SearchRequest) -> None:
    """Run Phase 1 scoring in the background, updating _search_state."""
    global _search_state
    _search_state["status"] = "searching"
    _search_state["keyword"] = req.keyword
    _search_state["category"] = req.category or req.keyword
    _search_state["progress"] = "Starting Pinterest search..."
    _search_state["error"] = None
    _search_state["images_ready"] = False

    def _update_progress(msg: str) -> None:
        _search_state["progress"] = msg
        if msg.startswith("images_extracted:"):
            _search_state["images_ready"] = True

    try:
        results = await run_scoring_phase(
            keyword=req.keyword,
            category=req.category or req.keyword,
            max_pins=req.max_pins,
            session_timeout_s=req.session_timeout_s,
            progress_callback=_update_progress,
        )
        _search_state["status"] = "done"
        _search_state["progress"] = f"Scored {len(results)} pins"
    except Exception as e:
        _search_state["status"] = "error"
        _search_state["error"] = str(e)
        _search_state["progress"] = f"Error: {e}"


# ── Routes ───────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the review UI."""
    html_path = Path("static/review.html")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/search")
async def search(req: SearchRequest):
    """Start Phase 1 — browse Pinterest and score images."""
    if _search_state["status"] == "searching":
        return JSONResponse(
            content={"error": "A search is already in progress"},
            status_code=409,
        )

    # Clear previous results
    if DATA_FILE.exists():
        DATA_FILE.unlink()

    asyncio.create_task(_run_search(req))
    return {"status": "searching", "keyword": req.keyword}


@app.get("/api/search/status")
async def search_status():
    """Poll for search progress."""
    return {
        "status": _search_state["status"],
        "keyword": _search_state["keyword"],
        "progress": _search_state["progress"],
        "error": _search_state["error"],
        "images_ready": _search_state["images_ready"],
    }


@app.get("/api/results")
async def get_results():
    """Return scored results as JSON."""
    if not DATA_FILE.exists():
        return JSONResponse(content=[], status_code=200)
    with open(DATA_FILE) as f:
        return json.load(f)


class GenerateOneRequest(BaseModel):
    pin_id: int


@app.post("/api/generate-one")
async def generate_one(req: GenerateOneRequest):
    """Generate a poster for a single pin. Called concurrently by the frontend."""
    if not DATA_FILE.exists():
        return JSONResponse(
            content={"error": "No scored results found"}, status_code=404
        )

    with open(DATA_FILE) as f:
        all_results = json.load(f)

    item = next((r for r in all_results if r["id"] == req.pin_id), None)
    if not item:
        return JSONResponse(
            content={"error": "Pin not found"}, status_code=404
        )

    try:
        full_res = await fetch_full_res_url(item["pin_url"])
        item["full_res_url"] = full_res

        # Use full-res URL for generation; fall back to thumbnail if download fails
        image_url = full_res
        poster_filename = f"poster_{item['id']}.png"
        try:
            poster_path = await generate_poster(
                image_url=image_url,
                output_filename=poster_filename,
            )
        except Exception:
            print(f"[generate_one] Full-res failed, falling back to thumbnail for pin {item['id']}")
            image_url = item["thumbnail_url"]
            poster_path = await generate_poster(
                image_url=image_url,
                output_filename=poster_filename,
            )
        item["poster_path"] = poster_path

        # Persist updated result
        with open(DATA_FILE, "w") as f:
            json.dump(all_results, f, indent=2)

        return {
            "id": item["id"],
            "full_res_url": full_res,
            "poster_path": poster_path,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            content={"id": req.pin_id, "error": str(e)}, status_code=500
        )
