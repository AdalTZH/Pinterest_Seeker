# Pinterest AI Agent — E-Commerce Poster Generator

A fully autonomous AI agent + human-in-the-loop review system that browses Pinterest, scores product images using **gpt-5.4-mini**, and generates e-commerce posters via **Nano Banana 2** (Gemini 3.1 Flash Image Preview).

## How It Works

1. **Search**: User opens the web UI and types what product they're looking for (e.g. "evening dresses", "silk skirts").
2. **Agent Browsing**: The AI agent uses [Scrapling](https://github.com/CYBERAD7/scrapling) (with anti-bot bypass) to browse Pinterest — extracts pin thumbnail URLs, downloads them, and scores with gpt-5.4-mini. Progress is shown in real-time.
3. **Review**: Once scoring is done, a grid of scored images appears. User reviews the AI scores and reasons, selects the images they like.
4. **Poster Generation**: User fills in product details (name, price, tagline) and clicks "Generate". The agent extracts full-res images and generates posters via Nano Banana 2.

## Architecture

```
┌──────────────────────────────────────────────┐
│  WEB UI — User types product keyword         │
│  "evening dresses" → clicks Search Pinterest │
└──────────────────────────────────────────────┘
        ↓
┌──────────────────────────────────────────────┐
│  PHASE 1 — Agent Scoring (automated)         │
│  Scrapling → Pinterest → Extract → Score     │
│  Guardrails: pin cap, timeout,               │
│  error circuit breaker                        │
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
│  Extract full-res URL → Nano Banana 2         │
│  Poster saved to /output/posters/            │
└──────────────────────────────────────────────┘
```

## Setup

```bash
# Clone & install
git clone https://github.com/AdalTZH/Pinterest_Seeker.git
cd Pinterest_Seeker
pip install -r requirements.txt
scrapling install

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
| `session_timeout_s` | 180s | Runaway session from a slow network |
| `max_error_streak` | 5 | Looping when Pinterest layout changes |

All three are evaluated via a single `guard.should_stop` check. Configurable from the search panel UI.

## Project Structure

```
pinterest-poster-agent/
├── main.py                  # Entry point — launches FastAPI server
├── server.py                # FastAPI: search, scoring, review, generate
├── agent/
│   ├── browser_agent.py     # Scrapling StealthyFetcher wrapper
│   ├── scorer.py            # Phase 1 scoring pipeline
│   ├── fullres_fetcher.py   # Phase 3 full-res extraction
│   ├── guardrails.py        # BrowsingGuardrail class
│   └── prompts.py           # System prompts
├── poster/
│   └── nano_banana.py       # Nano Banana 2 integration
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
| `NANO_BANANA_MODEL` | Poster model (default: `google/gemini-3.1-flash-image-preview`) |
