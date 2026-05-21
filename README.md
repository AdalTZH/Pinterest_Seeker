# Pinterest AI Agent — E-Commerce Poster Generator

A fully autonomous AI agent + human-in-the-loop review system that browses Pinterest, scores product images using **gpt-5.4-mini**, and generates e-commerce posters via **nanoBanana Pro**.

## How It Works

1. **Search**: User opens the web UI and types what product they're looking for (e.g. "evening dresses", "silk skirts").
2. **Agent Browsing**: The AI agent autonomously browses Pinterest — scrolls the feed, screenshots each pin thumbnail, and scores them with gpt-5.4-mini. Progress is shown in real-time.
3. **Review**: Once scoring is done, a grid of scored images appears. User reviews the AI scores and reasons, selects the images they like.
4. **Poster Generation**: User fills in product details (name, price, tagline) and clicks "Generate". The agent extracts full-res images and generates posters via nanoBanana Pro.

## Architecture

```
┌──────────────────────────────────────────────┐
│  WEB UI — User types product keyword         │
│  "evening dresses" → clicks Search Pinterest │
└──────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────┐
│  PHASE 1 — Agent Scoring (automated)         │
│  Playwright → Pinterest → Scroll → Score     │
│  Guardrails: pin cap, scroll cap, timeout,   │
│  error circuit breaker, stale detector        │
│  UI shows real-time progress                 │
└──────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────┐
│  PHASE 2 — Human Review                      │
│  Scored image grid appears                   │
│  User selects images → fills product info    │
│  → clicks "Generate Posters"                 │
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
# Start the server
python main.py

# Or with uvicorn directly
uvicorn server:app --host 0.0.0.0 --port 8000
```

Then open http://localhost:8000 — type a product keyword and the agent will handle the rest.

## Guardrails

| Guardrail | Default | What it prevents |
|---|---|---|
| `max_pins` | 40 | Collecting more pins than needed |
| `max_scrolls` | 8 | Infinite scroll on a bottomless feed |
| `session_timeout_s` | 180s | Runaway session from a slow network |
| `max_error_streak` | 5 | Looping when Pinterest layout changes |
| `max_stale_scrolls` | 2 | Scrolling past the end of the feed |

All five are evaluated on every iteration via a single `guard.should_stop` check. Configurable from the search panel UI.

## Project Structure

```
pinterest-poster-agent/
├── main.py                  # Entry point — launches FastAPI server
├── server.py                # FastAPI: search, scoring, review, generate
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
│   └── review.html          # Single-page UI (search → review → generate)
├── data/                    # Scored results
└── output/posters/          # Generated posters
```

## Environment Variables

| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `AGENT_MODEL` | Vision model (default: `openai/gpt-5.4-mini`) |
| `NANO_BANANA_MODEL` | Poster model (default: `nanobanana/nanobanana-pro`) |
