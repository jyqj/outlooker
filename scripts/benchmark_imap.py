#!/usr/bin/env python3
"""\
IMAP 拉取性能基准（PERF-001）

该脚本用于评估 “复用 IMAPEmailClient” vs “每次新建 IMAPEmailClient” 的延迟差异，
从而判断是否值得进一步引入连接池/更复杂的复用策略。

注意:
- 需要联网访问 Outlook IMAP / OAuth token endpoint
- 需要提供可用的邮箱与 refresh_token（以及可选 password/client_id）
- 会写入本地 SQLite 缓存（与服务端行为一致）

使用方法:
    python3 scripts/benchmark_imap.py --email user@example.com --refresh-token "M.C123..." --iterations 10
    python3 scripts/benchmark_imap.py --mode new-client --iterations 5

参数也可通过环境变量提供:
    OUTLOOK_BENCH_EMAIL
    OUTLOOK_BENCH_REFRESH_TOKEN
    OUTLOOK_BENCH_PASSWORD (可选)
    OUTLOOK_BENCH_CLIENT_ID (可选)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from statistics import mean, median
from typing import Optional, Sequence


# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))


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


async def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IMAP benchmark (reuse vs new-client)")
    parser.add_argument("--email", type=str, default=os.getenv("OUTLOOK_BENCH_EMAIL", "").strip())
    parser.add_argument(
        "--refresh-token",
        type=str,
        default=os.getenv("OUTLOOK_BENCH_REFRESH_TOKEN", "").strip(),
    )
    parser.add_argument("--password", type=str, default=os.getenv("OUTLOOK_BENCH_PASSWORD", ""))
    parser.add_argument("--client-id", type=str, default=os.getenv("OUTLOOK_BENCH_CLIENT_ID", ""))
    parser.add_argument(
        "--database-path",
        type=str,
        default=os.getenv("OUTLOOK_BENCH_DATABASE_PATH", "").strip(),
        help="可选：使用独立的 SQLite DB（会设置环境变量 DATABASE_PATH）",
    )
    parser.add_argument("--folder", type=str, default="INBOX")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1, help="预热次数（不计入统计）")
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument(
        "--mode",
        choices=["reuse-client", "new-client"],
        default="reuse-client",
        help="reuse-client: 复用同一个 IMAPEmailClient；new-client: 每次新建",
    )
    parser.add_argument("--redact", action="store_true", help="输出中脱敏 email（便于粘贴到文档）")
    parser.add_argument("--json", action="store_true", help="额外输出一段 JSON 结果摘要")
    args = parser.parse_args(argv)

    if not args.email or not args.refresh_token:
        print("缺少必填参数：--email 与 --refresh-token（或设置 OUTLOOK_BENCH_EMAIL / OUTLOOK_BENCH_REFRESH_TOKEN）")
        return 2

    if args.database_path:
        os.environ["DATABASE_PATH"] = args.database_path

    iterations = max(1, int(args.iterations or 0))
    top = max(1, int(args.top or 0))
    folder = (args.folder or "INBOX").strip() or "INBOX"
    warmup = max(0, int(args.warmup or 0))

    account_info = {
        "password": args.password or "",
        "refresh_token": args.refresh_token,
    }
    if args.client_id:
        account_info["client_id"] = args.client_id

    from app.imap_client import IMAPEmailClient  # type: ignore

    async def _run_once(*, reuse_client: Optional[IMAPEmailClient] = None) -> None:
        client = reuse_client or IMAPEmailClient(args.email, account_info)
        try:
            await client.get_messages_with_content(folder_id=folder, top=top)
        finally:
            if reuse_client is None:
                await client.cleanup()

    reuse = args.mode == "reuse-client"
    client: Optional[IMAPEmailClient] = IMAPEmailClient(args.email, account_info) if reuse else None

    email_for_output = "<redacted>" if args.redact else args.email

    if warmup:
        print(f"Warmup: {warmup} iterations (excluded)")
        for idx in range(1, warmup + 1):
            try:
                await _run_once(reuse_client=client)
                print(f"[warmup {idx}/{warmup}] ok")
            except Exception as exc:
                print(f"[warmup {idx}/{warmup}] failed: {type(exc).__name__}: {exc}")

    success_latencies_ms: list[float] = []
    failure_latencies_ms: list[float] = []
    failure_reasons: list[str] = []
    total_start = time.perf_counter()
    try:
        for idx in range(1, iterations + 1):
            start = time.perf_counter()
            try:
                await _run_once(reuse_client=client)
                duration_ms = (time.perf_counter() - start) * 1000.0
                success_latencies_ms.append(duration_ms)
            except Exception as exc:
                duration_ms = (time.perf_counter() - start) * 1000.0
                failure_latencies_ms.append(duration_ms)
                reason = f"{type(exc).__name__}: {exc}"
                failure_reasons.append(reason)
                print(f"[{idx}/{iterations}] failed ({duration_ms:.0f}ms): {reason}")
    finally:
        if client is not None:
            await client.cleanup()
    total_time_s = max(0.0, time.perf_counter() - total_start)

    success = len(success_latencies_ms)
    failures = len(failure_latencies_ms)
    qps = (success / total_time_s) if total_time_s > 0 else 0.0

    success_latencies_ms.sort()
    if success_latencies_ms:
        avg = mean(success_latencies_ms)
        med = median(success_latencies_ms)
        p95 = _percentile(success_latencies_ms, 95)
        min_ms = success_latencies_ms[0]
        max_ms = success_latencies_ms[-1]
    else:
        avg = med = p95 = min_ms = max_ms = 0.0

    print("")
    print("IMAP benchmark result")
    print(f"- mode: {args.mode}")
    print(f"- email: {email_for_output}")
    print(f"- folder: {folder}")
    print(f"- top: {top}")
    print(f"- warmup: {warmup}")
    if args.database_path:
        print(f"- database_path: {args.database_path}")
    print(f"- iterations: {iterations}")
    print(f"- success: {success} / {iterations}")
    if success_latencies_ms:
        print(
            f"- avg: {avg:.0f}ms  median: {med:.0f}ms  p95: {p95:.0f}ms  min: {min_ms:.0f}ms  max: {max_ms:.0f}ms"
        )
    else:
        print("- avg/median/p95: n/a (no successful runs)")
    print(f"- total: {total_time_s*1000:.0f}ms  qps: {qps:.2f}")
    if failures:
        sample = "; ".join(failure_reasons[:3])
        print(f"- failures: {failures} (sample: {sample})")

    if args.json:
        summary = {
            "mode": args.mode,
            "email": email_for_output,
            "folder": folder,
            "top": top,
            "warmup": warmup,
            "iterations": iterations,
            "success": success,
            "failures": failures,
            "avg_ms": round(avg, 2) if success_latencies_ms else None,
            "median_ms": round(med, 2) if success_latencies_ms else None,
            "p95_ms": round(p95, 2) if success_latencies_ms else None,
            "min_ms": round(min_ms, 2) if success_latencies_ms else None,
            "max_ms": round(max_ms, 2) if success_latencies_ms else None,
            "total_ms": round(total_time_s * 1000.0, 2),
            "qps": round(qps, 4),
            "database_path": (args.database_path or None),
        }
        print("")
        print(json.dumps(summary, ensure_ascii=False))

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
