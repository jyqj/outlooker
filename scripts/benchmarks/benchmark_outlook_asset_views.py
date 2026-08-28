#!/usr/bin/env python3
"""Benchmark legacy Outlook asset fan-out against the joined read projection."""

from __future__ import annotations

import argparse
import sqlite3
import tempfile
import time
from pathlib import Path
from statistics import median
from typing import Callable, Sequence


ACCOUNT_SELECT = """
SELECT email, status, account_type, source_account_email, default_channel_id,
       notes, last_synced_at, created_at, updated_at
FROM outlook_accounts
ORDER BY updated_at DESC, email ASC
LIMIT ? OFFSET ?
"""

JOINED_SELECT = """
SELECT
    account.email,
    account.status,
    account.account_type,
    capability.graph_ready,
    token.id AS token_id,
    token.expires_at,
    token.status AS token_status,
    CASE WHEN token.refresh_token <> '' THEN 1 ELSE 0 END AS has_refresh_token
FROM outlook_accounts AS account
LEFT JOIN account_capabilities AS capability ON capability.email = account.email
LEFT JOIN oauth_tokens AS token ON token.id = (
    SELECT candidate.id
    FROM oauth_tokens AS candidate
    WHERE candidate.email = account.email AND candidate.status = 'active'
    ORDER BY candidate.id DESC
    LIMIT 1
)
ORDER BY account.updated_at DESC, account.email ASC
LIMIT ? OFFSET ?
"""


def percentile(samples: Sequence[float], value: float) -> float:
    ordered = sorted(samples)
    if not ordered:
        return 0.0
    position = int(round((len(ordered) - 1) * value))
    return ordered[position]


def timed(handler: Callable[[], None], iterations: int) -> tuple[float, float]:
    samples: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        handler()
        samples.append((time.perf_counter() - started) * 1000)
    return median(samples), percentile(samples, 0.95)


def connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def seed(path: Path, accounts: int) -> None:
    conn = connect(path)
    try:
        conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE outlook_accounts (
                email TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                account_type TEXT NOT NULL,
                source_account_email TEXT,
                default_channel_id INTEGER,
                notes TEXT,
                last_synced_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE account_capabilities (
                email TEXT PRIMARY KEY,
                imap_ready INTEGER,
                graph_ready INTEGER,
                protocol_ready INTEGER,
                browser_fallback_ready INTEGER,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE oauth_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                oauth_config_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                access_token TEXT,
                refresh_token TEXT,
                expires_at TEXT,
                scopes_granted TEXT,
                status TEXT,
                last_error TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX idx_outlook_accounts_updated_email
            ON outlook_accounts(updated_at DESC, email ASC);
            CREATE INDEX idx_oauth_tokens_email_status_id
            ON oauth_tokens(email, status, id DESC);
            """
        )
        account_rows = [
            (f"user-{index:06d}@example.com", "active", "consumer")
            for index in range(accounts)
        ]
        conn.executemany(
            "INSERT INTO outlook_accounts(email, status, account_type) VALUES (?, ?, ?)",
            account_rows,
        )
        conn.executemany(
            """
            INSERT INTO account_capabilities(
                email, imap_ready, graph_ready, protocol_ready, browser_fallback_ready
            ) VALUES (?, 1, 1, 0, 1)
            """,
            [(row[0],) for row in account_rows],
        )
        conn.executemany(
            """
            INSERT INTO oauth_tokens(
                oauth_config_id, email, access_token, refresh_token, expires_at, status
            ) VALUES (1, ?, 'encrypted-access', 'encrypted-refresh', '2030-01-01', 'active')
            """,
            [(row[0],) for row in account_rows],
        )
        conn.commit()
    finally:
        conn.close()


def legacy_read(path: Path, page_size: int) -> None:
    conn = connect(path)
    try:
        accounts = conn.execute(ACCOUNT_SELECT, (page_size, 0)).fetchall()
    finally:
        conn.close()

    for account in accounts:
        conn = connect(path)
        try:
            conn.execute(
                """
                SELECT id, expires_at, status
                FROM oauth_tokens
                WHERE email = ? AND status = 'active'
                ORDER BY id DESC
                LIMIT 1
                """,
                (account["email"],),
            ).fetchone()
        finally:
            conn.close()

        conn = connect(path)
        try:
            conn.execute(
                "SELECT graph_ready FROM account_capabilities WHERE email = ?",
                (account["email"],),
            ).fetchone()
        finally:
            conn.close()

    conn = connect(path)
    try:
        conn.execute("SELECT COUNT(*) FROM outlook_accounts").fetchone()
    finally:
        conn.close()


def projection_read(path: Path, page_size: int) -> None:
    conn = connect(path)
    try:
        conn.execute("BEGIN")
        conn.execute("SELECT COUNT(*) FROM outlook_accounts").fetchone()
        conn.execute(JOINED_SELECT, (page_size, 0)).fetchall()
        conn.rollback()
    finally:
        conn.close()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--accounts", type=int, default=10_000)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--iterations", type=int, default=20)
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="outlooker-asset-bench-") as directory:
        path = Path(directory) / "assets.sqlite3"
        seed(path, max(args.accounts, args.page_size))

        # Warm the OS and SQLite page caches before collecting samples.
        legacy_read(path, args.page_size)
        projection_read(path, args.page_size)

        legacy_median, legacy_p95 = timed(
            lambda: legacy_read(path, args.page_size),
            args.iterations,
        )
        projection_median, projection_p95 = timed(
            lambda: projection_read(path, args.page_size),
            args.iterations,
        )

    speedup = legacy_median / projection_median if projection_median else float("inf")
    legacy_tasks = 2 * args.page_size + 2
    print(f"accounts={args.accounts} page_size={args.page_size} iterations={args.iterations}")
    print(
        f"legacy:     median={legacy_median:.3f}ms p95={legacy_p95:.3f}ms "
        f"db_tasks={legacy_tasks}"
    )
    print(
        f"projection: median={projection_median:.3f}ms p95={projection_p95:.3f}ms "
        "db_tasks=1"
    )
    print(f"median_speedup={speedup:.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
