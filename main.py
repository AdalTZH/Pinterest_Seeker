"""Entry point — launches the FastAPI review UI server."""

from __future__ import annotations

import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    print("🌐 Starting Pinterest Poster Agent at http://localhost:8000\n")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
