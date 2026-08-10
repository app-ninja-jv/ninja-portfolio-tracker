"""SQLite cache. The web layer reads this and never calls yfinance."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS bars (
  ticker      TEXT NOT NULL,
  week_start  TEXT NOT NULL,
  open REAL, high REAL, low REAL, close REAL, adj_close REAL,
  volume      REAL NOT NULL,
  fetched_at  TEXT NOT NULL,
  PRIMARY KEY (ticker, week_start)
);
CREATE TABLE IF NOT EXISTS meta (
  ticker TEXT PRIMARY KEY,
  name TEXT, exchange TEXT, currency TEXT, sector TEXT,
  added_on TEXT, added_reason TEXT
);
CREATE TABLE IF NOT EXISTS quality (
  ticker TEXT, checked_at TEXT, n_bars INTEGER,
  first_bar TEXT, last_bar TEXT, staleness_days INTEGER,
  passed INTEGER, failures TEXT, warnings TEXT,
  PRIMARY KEY (ticker, checked_at)
);
CREATE INDEX IF NOT EXISTS idx_bars_week ON bars(week_start);
"""


class Cache:
    def __init__(self, path: str | Path = "data/bars.sqlite"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.conn.close()

    # ---------------------------------------------------------------- write
    def put_bars(self, ticker: str, bars: list[dict]) -> int:
        now = datetime.utcnow().isoformat(timespec="seconds")
        rows = [
            (ticker, b["date"], b.get("open"), b["high"], b["low"], b["close"],
             b.get("adj_close", b["close"]), b["volume"], now)
            for b in bars
        ]
        self.conn.executemany(
            "INSERT OR REPLACE INTO bars "
            "(ticker,week_start,open,high,low,close,adj_close,volume,fetched_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)", rows,
        )
        self.conn.commit()
        return len(rows)

    def put_quality(self, rep) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO quality "
            "(ticker,checked_at,n_bars,first_bar,last_bar,staleness_days,passed,failures,warnings) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (rep.ticker, datetime.utcnow().isoformat(timespec="seconds"), rep.n_bars,
             rep.first_bar, rep.last_bar, rep.staleness_days, int(rep.passed),
             "; ".join(rep.failures), "; ".join(rep.warnings)),
        )
        self.conn.commit()

    def put_meta(self, ticker: str, **kw) -> None:
        cols = ["name", "exchange", "currency", "sector", "added_on", "added_reason"]
        vals = [kw.get(c) for c in cols]
        self.conn.execute(
            f"INSERT OR REPLACE INTO meta (ticker,{','.join(cols)}) "
            f"VALUES (?,{','.join('?' * len(cols))})", (ticker, *vals),
        )
        self.conn.commit()

    # ---------------------------------------------------------------- read
    def get_bars(self, ticker: str, weeks: int | None = None,
                 upto: str | None = None) -> list[dict]:
        q = "SELECT * FROM bars WHERE ticker=?"
        args: list = [ticker]
        if upto:
            q += " AND week_start<=?"
            args.append(upto)
        q += " ORDER BY week_start"
        rows = [dict(r) for r in self.conn.execute(q, args)]
        for r in rows:
            r["date"] = r.pop("week_start")
        return rows[-weeks:] if weeks else rows

    def tickers(self) -> list[str]:
        return [r[0] for r in self.conn.execute(
            "SELECT DISTINCT ticker FROM bars ORDER BY ticker")]

    def last_quality(self) -> dict[str, dict]:
        rows = self.conn.execute(
            "SELECT * FROM quality q WHERE checked_at = "
            "(SELECT MAX(checked_at) FROM quality WHERE ticker=q.ticker)")
        return {r["ticker"]: dict(r) for r in rows}

    def stats(self) -> dict:
        row = self.conn.execute(
            "SELECT COUNT(*) n, COUNT(DISTINCT ticker) t, "
            "MIN(week_start) a, MAX(week_start) b FROM bars").fetchone()
        return {"bars": row[0], "tickers": row[1], "first": row[2], "last": row[3]}
