# Pinterest AI Agent — E-Commerce Poster Generator

A fully autonomous AI agent + human-in-the-loop review system that browses Pinterest, scores product images using **gpt-5.4-mini**, and generates e-commerce posters via **nanoBanana Pro**.

## How It Works

1. **Phase 1 — Scoring**: User inputs a product category (e.g. "evening dresses"). The AI agent browses Pinterest autonomously — scrolls, screenshots each pin thumbnail, and scores them with gpt-5.4-mini. Results saved to `data/scored_results.json`.

2. **Phase 2 — Review UI**: User opens a local FastAPI web page, sees an image grid with AI scores and reasons, selects the images they want, configures product details, and clicks "Generate".

3. **Phase 3 — Poster Generation**: The agent re-visits each selected pin, extracts the full-res image URL, sends it to nanoBanana Pro, and saves posters to `output/posters/`.

## Architecture

```
User Input: "evening dresses"
        ↓
┌──────────────────────────────────────────────┐
│  PHASE 1 — Agent Scoring (automated)         │
│  Playwright → Pinterest → Scroll → Score     │
│  Guardrails: pin cap, scroll cap, timeout,   │
│  error circuit breaker, stale detector        │
└──────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────┐
│  PHASE 2 — Human Review UI                   │
│  FastAPI serves grid of scored thumbnails    │
│  User selects images → "Generate Posters"    │
└──────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────┐
│  PHASE 3 — Full-Res + Poster Gen             │
│  Extract full-res URL → nanoBanana Pro       │
│  Poster saved to /output/posters/            │
└──────────────────────────────────────────────┘
```

## Setup

```bash
# Clone & install
git clone https://github.com/AdalTZH/Pinterest_Seeker.git
cd Pinterest_Seeker
pip install -r requirements.txt
playwright install chromium

# Configure environment
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY
```

## Usage

```bash
# Run the full pipeline
python main.py

# Or run the review UI standalone (after Phase 1 has produced scored_results.json)
uvicorn server:app --host 0.0.0.0 --port 8000
```

## Guardrails

| Guardrail | Default | What it prevents |
|---|---|---|
| `max_pins` | 40 | Collecting more pins than needed |
| `max_scrolls` | 8 | Infinite scroll on a bottomless feed |
| `session_timeout_s` | 180s | Runaway session from a slow network |
| `max_error_streak` | 5 | Looping when Pinterest layout changes |
| `max_stale_scrolls` | 2 | Scrolling past the end of the feed |

All five are evaluated on every iteration via a single `guard.should_stop` check.

## Project Structure

```
pinterest-poster-agent/
├── main.py                  # Entry point
├── server.py                # FastAPI review UI + generate endpoint
├── agent/
│   ├── browser_agent.py     # Browser setup
│   ├── scorer.py            # Phase 1 scoring pipeline
│   ├── fullres_fetcher.py   # Phase 3 full-res extraction
│   ├── guardrails.py        # BrowsingGuardrail class
│   └── prompts.py           # System prompts
├── poster/
│   └── nano_banana.py       # nanoBanana Pro integration
├── db/
│   └── tracker.py           # SQLite dedup tracker
├── static/
│   └── review.html          # Review UI
├── data/                    # Scored results
└── output/posters/          # Generated posters
```

## Environment Variables

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `AGENT_MODEL` | Vision model (default: `openai/gpt-5.4-mini`) |
| `NANO_BANANA_MODEL` | Poster model (default: `nanobanana/nanobanana-pro`) |
