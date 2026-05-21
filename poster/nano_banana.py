"""Poster generation via Nano Banana 2 (Gemini 3.1 Flash) through OpenRouter."""

from __future__ import annotations

import base64
import os
from pathlib import Path

import httpx

from agent.prompts import POSTER_GENERATION_PROMPT

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
NANO_BANANA_MODEL = os.getenv(
    "NANO_BANANA_MODEL", "google/gemini-3.1-flash-image-preview"
)
OUTPUT_DIR = Path("output/posters")


async def generate_poster(
    image_url: str,
    product_name: str,
    price: str,
    tagline: str,
    output_filename: str,
) -> str:
    """Send a full-res image to Nano Banana 2 and save the poster locally.

    Returns the path to the saved poster file (PNG image).
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    prompt = POSTER_GENERATION_PROMPT.format(
        product_name=product_name,
        price=price,
        tagline=tagline,
    )

    async with httpx.AsyncClient(timeout=120) as http:
        response = await http.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": NANO_BANANA_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url},
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                "modalities": ["image", "text"],
            },
        )
        response.raise_for_status()
        data = response.json()

    message = data["choices"][0]["message"]

    # Extract generated image from response
    images = message.get("images", [])
    if images:
        data_url = images[0]["image_url"]["url"]
        # Strip data URI prefix (e.g. "data:image/png;base64,")
        header, b64_data = data_url.split(",", 1)
        img_bytes = base64.b64decode(b64_data)
        poster_path = OUTPUT_DIR / output_filename
        poster_path.write_bytes(img_bytes)
    else:
        # Fallback: save text content if no image returned
        content = message.get("content", "")
        poster_path = OUTPUT_DIR / output_filename
        poster_path.write_text(content, encoding="utf-8")

    return str(poster_path)
