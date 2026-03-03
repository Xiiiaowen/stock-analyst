"""
Portfolio database — SQLite-backed CRUD for holdings.

Designed for single-user now; user_id column is present
for future multi-user support without schema migration.
"""

import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent / "portfolio.db"


def _conn():
    return sqlite3.connect(str(_DB_PATH))


def init_db():
    """Create tables if they don't exist."""
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS holdings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     TEXT    NOT NULL DEFAULT 'default',
                ticker      TEXT    NOT NULL,
                entry_price REAL    NOT NULL,
                quantity    REAL    NOT NULL,
                entry_date  TEXT,
                notes       TEXT,
                added_at    TEXT    DEFAULT (datetime('now'))
            )
        """)
        con.commit()


def get_holdings(user_id: str = "default") -> list[dict]:
    """Return all holdings for a user as a list of dicts."""
    with _conn() as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM holdings WHERE user_id = ? ORDER BY added_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_holding(
    ticker: str,
    entry_price: float,
    quantity: float,
    entry_date: str | None = None,
    notes: str | None = None,
    user_id: str = "default",
) -> int:
    """Insert a new holding, return its id."""
    with _conn() as con:
        cur = con.execute(
            """
            INSERT INTO holdings (user_id, ticker, entry_price, quantity, entry_date, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, ticker.upper().strip(), entry_price, quantity, entry_date, notes),
        )
        con.commit()
        return cur.lastrowid


def update_holding(
    holding_id: int,
    entry_price: float | None = None,
    quantity: float | None = None,
    entry_date: str | None = None,
    notes: str | None = None,
):
    """Update one or more fields on an existing holding."""
    fields, values = [], []
    if entry_price is not None:
        fields.append("entry_price = ?")
        values.append(entry_price)
    if quantity is not None:
        fields.append("quantity = ?")
        values.append(quantity)
    if entry_date is not None:
        fields.append("entry_date = ?")
        values.append(entry_date)
    if notes is not None:
        fields.append("notes = ?")
        values.append(notes)
    if not fields:
        return
    values.append(holding_id)
    with _conn() as con:
        con.execute(
            f"UPDATE holdings SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        con.commit()


def delete_holding(holding_id: int):
    """Remove a holding by id."""
    with _conn() as con:
        con.execute("DELETE FROM holdings WHERE id = ?", (holding_id,))
        con.commit()
