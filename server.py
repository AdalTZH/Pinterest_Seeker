"""FastAPI app — Phase 2 review UI and Phase 3 generate endpoint."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.fullres_fetcher import fetch_full_res_url
from poster.nano_banana import generate_poster

app = FastAPI(title="Pinterest Poster Agent — Review UI")

DATA_FILE = Path("data/scored_results.json")

app.mount("/output", StaticFiles(directory="output"), name="output")


# ── Models ───────────────────────────────────────────────────────────


class GenerateRequest(BaseModel):
    selected_ids: list[int]
    product_name: str = "Product"
    price: str = ""
    tagline: str = ""
    logo_url: str = ""


# ── Routes ───────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the review UI."""
    html_path = Path("static/review.html")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


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
