#!/usr/bin/env python3
"""\
SQLite 邮件缓存性能压测脚本

目标:
- 在 10万/50万/100万记录规模下，评估 email_cache 相关查询的延迟
- 输出建议的索引/结构优化方向

使用方法:
    python scripts/benchmark_email_cache.py

可选参数:
    python scripts/benchmark_email_cache.py --sizes 100000 500000 1000000 --sample 200
    python scripts/benchmark_email_cache.py --db-dir /tmp/outlooker-bench --with-extra-indexes
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Iterable, Sequence


EMAIL_CACHE_SCHEMA = """
CREATE TABLE IF NOT EXISTS email_cache (
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


EMAIL_CACHE_META_SCHEMA = """
CREATE TABLE IF NOT EXISTS email_cache_meta (
    email TEXT NOT NULL,
    folder TEXT NOT NULL,
    last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (email, folder)
);
"""


EXTRA_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_email_cache_email_folder_id_desc ON email_cache(email, folder, id DESC);",
    "CREATE INDEX IF NOT EXISTS idx_email_cache_email_folder_received_id_desc ON email_cache(email, folder, received_date DESC, id DESC);",
]


GET_CACHED_MESSAGES_SQL = """
SELECT message_id, subject, sender, received_date, body_preview, body_content, body_type
FROM email_cache
WHERE email = ? AND folder = ?
ORDER BY
  CASE WHEN message_id GLOB '[0-9]*' THEN CAST(message_id AS INTEGER) ELSE 0 END DESC,
  received_date DESC,
  id DESC
LIMIT ?
"""


GET_CACHED_EMAIL_SQL = """
SELECT *
FROM email_cache
WHERE email = ? AND folder = ? AND message_id = ?
LIMIT 1
"""


GET_CACHE_STATE_SQL = """
SELECT
  COUNT(*) AS cached_count,
  MAX(CASE WHEN message_id GLOB '[0-9]*' THEN CAST(message_id AS INTEGER) ELSE NULL END) AS max_uid
FROM email_cache
WHERE email = ? AND folder = ?
"""


GET_CACHE_META_SQL = """
SELECT last_checked_at
FROM email_cache_meta
WHERE email = ? AND folder = ?
"""


@dataclass(frozen=True)
class QueryStats:
    count: int
    avg_ms: float
    median_ms: float
    p95_ms: float


@dataclass(frozen=True)
class BenchResult:
    total_rows: int
    accounts: int
    per_account: int
    sqlite_version: str
    python: str
    insert_seconds: float
    cached_messages: QueryStats
    cached_email: QueryStats
    cache_state: QueryStats
    cache_meta: QueryStats


def _percentile(sorted_values: Sequence[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    if p <= 0:
        return sorted_values[0]
    if p >= 100:
        return sorted_values[-1]
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return d0 + d1


def _time_many(fn, *, count: int) -> QueryStats:
    samples: list[float] = []
    for _ in range(count):
        start = time.perf_counter()
        fn()
        elapsed = (time.perf_counter() - start) * 1000.0
        samples.append(elapsed)
    samples.sort()
    return QueryStats(
        count=len(samples),
        avg_ms=mean(samples),
        median_ms=median(samples),
        p95_ms=_percentile(samples, 95),
    )


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA cache_size=-200000;")  # ~200MB cache (best effort)


def _create_schema(conn: sqlite3.Connection, *, with_extra_indexes: bool) -> None:
    conn.executescript(EMAIL_CACHE_SCHEMA)
    conn.executescript(EMAIL_CACHE_META_SCHEMA)
    if with_extra_indexes:
        for stmt in EXTRA_INDEXES:
            conn.execute(stmt)
    conn.commit()


def _iter_accounts(total_rows: int, per_account: int) -> list[str]:
    accounts = max(1, total_rows // per_account)
    return [f"user{idx}@example.com" for idx in range(accounts)]


def _populate(conn: sqlite3.Connection, *, total_rows: int, per_account: int, folder: str) -> float:
    emails = _iter_accounts(total_rows, per_account)
    started = time.perf_counter()
    cursor = conn.cursor()

    # 同步插入更快：一次事务 + 批量 executemany
    rows: list[tuple[str, str, str, str, str, str, str, str, str]] = []
    body_preview = "preview"
    body_content = "content"
    body_type = "text"
    sender = "Sender <sender@example.com>"

    for email in emails:
        cursor.execute(
            """
            INSERT OR REPLACE INTO email_cache_meta (email, folder, last_checked_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (email, folder),
        )
        for idx in range(1, per_account + 1):
            message_id = str(idx)
            subject = f"Subject {idx}"
            received_date = f"2025-01-01T00:{idx % 60:02d}:00"
            rows.append(
                (
                    email,
                    folder,
                    message_id,
                    subject,
                    sender,
                    received_date,
                    body_preview,
                    body_content,
                    body_type,
                )
            )

    cursor.executemany(
        """
        INSERT OR REPLACE INTO email_cache
        (email, folder, message_id, subject, sender, received_date, body_preview, body_content, body_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return time.perf_counter() - started


def _sample_items(items: Sequence[str], sample_size: int) -> list[str]:
    if sample_size <= 0 or sample_size >= len(items):
        return list(items)
    step = max(1, len(items) // sample_size)
    return [items[i] for i in range(0, len(items), step)][:sample_size]


def run_benchmark(
    *,
    db_path: Path,
    total_rows: int,
    per_account: int,
    folder: str,
    sample: int,
    with_extra_indexes: bool,
) -> BenchResult:
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        _apply_pragmas(conn)
        _create_schema(conn, with_extra_indexes=with_extra_indexes)
        insert_seconds = _populate(conn, total_rows=total_rows, per_account=per_account, folder=folder)

        emails = _iter_accounts(total_rows, per_account)
        sample_emails = _sample_items(emails, sample)

        def bench_cached_messages() -> None:
            email = sample_emails[int(time.time_ns()) % len(sample_emails)]
            conn.execute(GET_CACHED_MESSAGES_SQL, (email, folder, 50)).fetchall()

        def bench_cached_email() -> None:
            email = sample_emails[int(time.time_ns()) % len(sample_emails)]
            message_id = str((int(time.time_ns()) % per_account) + 1)
            conn.execute(GET_CACHED_EMAIL_SQL, (email, folder, message_id)).fetchone()

        def bench_cache_state() -> None:
            email = sample_emails[int(time.time_ns()) % len(sample_emails)]
            conn.execute(GET_CACHE_STATE_SQL, (email, folder)).fetchone()

        def bench_cache_meta() -> None:
            email = sample_emails[int(time.time_ns()) % len(sample_emails)]
            conn.execute(GET_CACHE_META_SQL, (email, folder)).fetchone()

        queries = max(100, len(sample_emails))
        return BenchResult(
            total_rows=total_rows,
            accounts=len(emails),
            per_account=per_account,
            sqlite_version=sqlite3.sqlite_version,
            python=os.sys.version.split()[0],
            insert_seconds=insert_seconds,
            cached_messages=_time_many(bench_cached_messages, count=queries),
            cached_email=_time_many(bench_cached_email, count=queries),
            cache_state=_time_many(bench_cache_state, count=queries),
            cache_meta=_time_many(bench_cache_meta, count=queries),
        )
    finally:
        conn.close()


def _format_stats(stats: QueryStats) -> str:
    return f"avg={stats.avg_ms:.3f}ms median={stats.median_ms:.3f}ms p95={stats.p95_ms:.3f}ms (n={stats.count})"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SQLite email_cache benchmark")
    parser.add_argument(
        "--sizes",
        nargs="+",
        type=int,
        default=[100_000, 500_000, 1_000_000],
        help="记录数规模列表（默认: 100000 500000 1000000）",
    )
    parser.add_argument(
        "--per-account",
        type=int,
        default=100,
        help="每个邮箱保留的缓存邮件数量（默认: 100，与实现保持一致）",
    )
    parser.add_argument(
        "--folder",
        type=str,
        default="INBOX",
        help="文件夹名（默认: INBOX）",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=200,
        help="抽样邮箱数量（默认: 200）",
    )
    parser.add_argument(
        "--db-dir",
        type=Path,
        default=Path("/tmp/outlooker-bench"),
        help="生成的 SQLite 文件目录（默认: /tmp/outlooker-bench）",
    )
    parser.add_argument(
        "--with-extra-indexes",
        action="store_true",
        help="创建额外索引用于对比",
    )
    args = parser.parse_args(argv)

    print("SQLite email_cache benchmark")
    print(f"- sqlite: {sqlite3.sqlite_version}")
    print(f"- python: {os.sys.version.split()[0]}")
    print(f"- per_account: {args.per_account}")
    print(f"- folder: {args.folder}")
    print(f"- sample emails: {args.sample}")
    print(f"- extra indexes: {args.with_extra_indexes}")
    print("")

    results: list[BenchResult] = []
    for size in args.sizes:
        db_path = args.db_dir / f"email_cache_{size}.db"
        print("=" * 72)
        print(f"Preparing {size:,} rows -> {db_path}")
        result = run_benchmark(
            db_path=db_path,
            total_rows=size,
            per_account=args.per_account,
            folder=args.folder,
            sample=args.sample,
            with_extra_indexes=args.with_extra_indexes,
        )
        results.append(result)
        print(f"insert: {result.insert_seconds:.2f}s (accounts={result.accounts}, per_account={result.per_account})")
        print(f"get_cached_messages: {_format_stats(result.cached_messages)}")
        print(f"get_cached_email:    {_format_stats(result.cached_email)}")
        print(f"get_cache_state:     {_format_stats(result.cache_state)}")
        print(f"get_cache_meta:      {_format_stats(result.cache_meta)}")
        print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
