#!/usr/bin/env python3
"""Compare legacy per-message cache writes with the batched transaction path."""

from __future__ import annotations

import argparse
import sqlite3
import tempfile
import time
from collections.abc import Sequence
from contextlib import closing
from pathlib import Path
from statistics import mean

SCHEMA = """
CREATE TABLE email_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    folder TEXT NOT NULL,
    message_id TEXT NOT NULL,
    subject TEXT,
    sender TEXT,
    received_date TEXT,
    body_preview TEXT,
    body_content TEXT,
    body_type TEXT DEFAULT 'text',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(email, folder, message_id)
);
"""

UPSERT = """
INSERT INTO email_cache
(email, folder, message_id, subject, sender, received_date, body_preview, body_content, body_type)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(email, folder, message_id)
DO UPDATE SET
    subject = excluded.subject,
    sender = excluded.sender,
    received_date = excluded.received_date,
    body_preview = excluded.body_preview,
    body_content = excluded.body_content,
    body_type = excluded.body_type
"""

RETENTION = """
DELETE FROM email_cache
WHERE email = ? AND folder = ?
  AND id NOT IN (
      SELECT id FROM email_cache
      WHERE email = ? AND folder = ?
      ORDER BY created_at DESC, id DESC
      LIMIT ?
  )
"""


def _rows(count: int) -> list[tuple[str, ...]]:
    return [
        (
            "bench@example.com",
            "INBOX",
            str(index),
            f"Subject {index}",
            "Sender <sender@example.com>",
            f"2026-01-01T00:00:{index % 60:02d}Z",
            "preview",
            "body",
            "text",
        )
        for index in range(1, count + 1)
    ]


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def _prepare(path: Path) -> None:
    with closing(_connect(path)) as conn:
        conn.executescript(SCHEMA)


def _legacy_write(path: Path, rows: list[tuple[str, ...]], limit: int) -> None:
    for row in rows:
        with closing(_connect(path)) as conn:
            conn.execute(UPSERT, row)
            conn.execute(
                RETENTION,
                (row[0], row[1], row[0], row[1], limit),
            )
            conn.commit()


def _batch_write(path: Path, rows: list[tuple[str, ...]], limit: int) -> None:
    with closing(_connect(path)) as conn:
        conn.executemany(UPSERT, rows)
        conn.execute(
            RETENTION,
            (rows[0][0], rows[0][1], rows[0][0], rows[0][1], limit),
        )
        conn.commit()


def _run_case(count: int, repeats: int) -> tuple[float, float]:
    rows = _rows(count)
    with tempfile.TemporaryDirectory(prefix="outlooker-cache-bench-") as directory:
        root = Path(directory)

        legacy_samples = []
        batch_samples = []
        for repeat in range(repeats):
            legacy_path = root / f"legacy-{repeat}.db"
            batch_path = root / f"batch-{repeat}.db"
            _prepare(legacy_path)
            _prepare(batch_path)
            started = time.perf_counter()
            _legacy_write(legacy_path, rows, count)
            legacy_samples.append(time.perf_counter() - started)

            started = time.perf_counter()
            _batch_write(batch_path, rows, count)
            batch_samples.append(time.perf_counter() - started)

        return mean(legacy_samples), mean(batch_samples)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--counts", nargs="+", type=int, default=[10, 50, 100])
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args(argv)

    print("messages | legacy ms | batch ms | speedup")
    print("---------|-----------|----------|--------")
    for count in args.counts:
        legacy, batch = _run_case(count, max(1, args.repeats))
        speedup = legacy / batch if batch else float("inf")
        print(f"{count:8d} | {legacy * 1000:9.2f} | {batch * 1000:8.2f} | {speedup:6.1f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
