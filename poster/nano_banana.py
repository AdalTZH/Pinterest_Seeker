"""Two-step poster generation pipeline.

Step 1: GPT-5.4-mini (Image Prompt Engineer) analyzes the product image
        and crafts a detailed image generation prompt.
Step 2: GPT-5.4 Image 2 receives the crafted prompt along with the
        original image and generates the poster.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

import httpx

from agent.prompts import IMAGE_PROMPT_ENGINEER_SYSTEM, IMAGE_PROMPT_ENGINEER_USER

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
PROMPT_MODEL = os.getenv("PROMPT_MODEL", "openai/gpt-5.4-mini")
IMAGE_GEN_MODEL = os.getenv(
    "IMAGE_GEN_MODEL", "openai/gpt-5.4-image-2"
)
OUTPUT_DIR = Path("output/posters")


async def _download_image(http: httpx.AsyncClient, url: str) -> tuple[str, str]:
    """Download an image and return (base64_data, data_uri)."""
    resp = await http.get(url)
    resp.raise_for_status()
    b64 = base64.b64encode(resp.content).decode()
    ct = resp.headers.get("content-type", "image/jpeg")
    return b64, f"data:{ct};base64,{b64}"


async def _craft_poster_prompt(
    http: httpx.AsyncClient,
    data_uri: str,
) -> str:
    """Step 1: Send image to GPT-5.4-mini to craft an image generation prompt."""
    response = await http.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": PROMPT_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": IMAGE_PROMPT_ENGINEER_SYSTEM,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri},
                        },
                        {"type": "text", "text": IMAGE_PROMPT_ENGINEER_USER},
                    ],
                },
            ],
        },
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


async def _generate_image(
    http: httpx.AsyncClient,
    prompt: str,
    data_uri: str,
) -> bytes | None:
    """Step 2: Send the crafted prompt + original image to GPT-5.4 Image 2 for poster generation."""
    response = await http.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": IMAGE_GEN_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri},
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
    images = message.get("images", [])
    if images:
        data_url = images[0]["image_url"]["url"]
        _, b64_data = data_url.split(",", 1)
        return base64.b64decode(b64_data)
    return None


async def generate_poster(
    image_url: str,
    output_filename: str,
) -> str:
    """Full pipeline: download image → craft prompt → generate poster.

    Returns the path to the saved poster file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient(timeout=180) as http:
        # Download the product image (Pinterest blocks third-party fetches)
        _, data_uri = await _download_image(http, image_url)

        # Step 1: GPT-5.4-mini crafts the poster prompt
        poster_prompt = await _craft_poster_prompt(http, data_uri)
        print(f"[PromptEngineer] Crafted prompt: {poster_prompt[:200]}...")

        # Step 2: Gemini generates the poster image
        img_bytes = await _generate_image(http, poster_prompt, data_uri)

    poster_path = OUTPUT_DIR / output_filename
    if img_bytes:
        poster_path.write_bytes(img_bytes)
    else:
        poster_path.write_text(poster_prompt, encoding="utf-8")

    return str(poster_path)
