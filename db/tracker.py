"""SQLite-based deduplication tracker for seen Pinterest pins."""

from __future__ import annotations

import aiosqlite

DB_PATH = "db/pins_seen.sqlite"


async def init_db() -> None:
    """Create the pins table if it doesn't already exist."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS pins (
                pin_url   TEXT PRIMARY KEY,
                keyword   TEXT,
                score     INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.commit()


async def is_seen(pin_url: str) -> bool:
    """Return True if pin_url has already been recorded."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT 1 FROM pins WHERE pin_url = ?", (pin_url,)
        )
        row = await cursor.fetchone()
        return row is not None


async def mark_seen(pin_url: str, keyword: str, score: int) -> None:
    """Insert a pin into the tracker (ignores duplicates)."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO pins (pin_url, keyword, score)
            VALUES (?, ?, ?)
            """,
            (pin_url, keyword, score),
        )
        await db.commit()
