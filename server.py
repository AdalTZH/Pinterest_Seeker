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


# ── In-memory search state ───────────────────────────────────────────

_search_state: dict = {
    "status": "idle",       # idle | searching | done | error
    "keyword": "",
    "category": "",
    "progress": "",
    "error": None,
}


# ── Models ───────────────────────────────────────────────────────────


class SearchRequest(BaseModel):
    keyword: str
    category: str = ""
    max_pins: int = 40
    session_timeout_s: int = 180


class GenerateRequest(BaseModel):
    selected_ids: list[int]
    product_name: str = "Product"
    price: str = ""
    tagline: str = ""
    logo_url: str = ""


# ── Background scoring task ──────────────────────────────────────────


async def _run_search(req: SearchRequest) -> None:
    """Run Phase 1 scoring in the background, updating _search_state."""
    global _search_state
    _search_state["status"] = "searching"
    _search_state["keyword"] = req.keyword
    _search_state["category"] = req.category or req.keyword
    _search_state["progress"] = "Starting Pinterest search..."
    _search_state["error"] = None

    def _update_progress(msg: str) -> None:
        _search_state["progress"] = msg

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
    }


@app.get("/api/results")
async def get_results():
    """Return scored results as JSON."""
    if not DATA_FILE.exists():
        return JSONResponse(content=[], status_code=200)
    with open(DATA_FILE) as f:
        return json.load(f)


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    """Fetch full-res images for selected pins and generate posters."""
    if not DATA_FILE.exists():
        return JSONResponse(
            content={"error": "No scored results found"}, status_code=404
        )

    with open(DATA_FILE) as f:
        all_results = json.load(f)

    selected = [r for r in all_results if r["id"] in req.selected_ids]
    if not selected:
        return JSONResponse(
            content={"error": "No matching pins found"}, status_code=400
        )

    generated: list[dict] = []

    for item in selected:
        try:
            full_res = await fetch_full_res_url(item["pin_url"])
            item["full_res_url"] = full_res

            poster_filename = f"poster_{item['id']}.txt"
            poster_path = await generate_poster(
                image_url=full_res,
                product_name=req.product_name,
                price=req.price,
                tagline=req.tagline,
                output_filename=poster_filename,
            )
            item["poster_path"] = poster_path
            generated.append(
                {
                    "id": item["id"],
                    "full_res_url": full_res,
                    "poster_path": poster_path,
                }
            )
        except Exception as e:
            generated.append(
                {"id": item["id"], "error": str(e)}
            )

    # Persist updated results
    with open(DATA_FILE, "w") as f:
        json.dump(all_results, f, indent=2)

    return {"generated": generated}
