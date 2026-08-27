#!/usr/bin/env python3
"""Fail CI only when a change introduces new Ruff diagnostics.

The repository has a historical lint backlog. This ratchet keeps the complete
inventory visible while allowing the backlog to shrink incrementally instead
of making every unrelated pull request repair the entire codebase.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ZERO_SHA = "0" * 40
DiagnosticKey = tuple[str, str, str]


def _run(command: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(command)}")
    return result


def _diagnostic_key(diagnostic: dict[str, Any], root: Path) -> DiagnosticKey:
    raw_filename = Path(str(diagnostic.get("filename") or ""))
    filename = raw_filename if raw_filename.is_absolute() else root / raw_filename
    try:
        relative = filename.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        relative = raw_filename.as_posix()

    return (
        relative,
        str(diagnostic.get("code") or "UNKNOWN"),
        str(diagnostic.get("message") or ""),
    )


def _collect_diagnostics(root: Path) -> Counter[DiagnosticKey]:
    config = root / "backend" / "pyproject.toml"
    result = _run(
        [
            "ruff",
            "check",
            "--no-fix",
            "--config",
            str(config),
            "--output-format=json",
            "backend/app",
            "tests/backend",
        ],
        cwd=root,
        check=False,
    )
    if result.returncode not in {0, 1}:
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Ruff failed with exit code {result.returncode}")

    try:
        payload = json.loads(result.stdout or "[]")
    except json.JSONDecodeError as exc:
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise RuntimeError("Ruff did not return valid JSON") from exc

    return Counter(_diagnostic_key(item, root) for item in payload)


def _resolve_base_ref(candidate: str) -> str:
    candidate = candidate.strip()
    if not candidate or candidate == ZERO_SHA:
        candidate = "HEAD^"

    probe = _run(
        ["git", "cat-file", "-e", f"{candidate}^{{commit}}"],
        cwd=REPOSITORY_ROOT,
        check=False,
    )
    if probe.returncode != 0:
        raise RuntimeError(f"Unable to resolve base commit: {candidate}")
    return candidate


def compare_with_base(base_candidate: str) -> int:
    base_ref = _resolve_base_ref(base_candidate)
    head_diagnostics = _collect_diagnostics(REPOSITORY_ROOT)

    with tempfile.TemporaryDirectory(prefix="outlooker-ruff-base-") as directory:
        base_root = Path(directory) / "repository"
        _run(
            ["git", "worktree", "add", "--detach", str(base_root), base_ref],
            cwd=REPOSITORY_ROOT,
        )
        try:
            base_diagnostics = _collect_diagnostics(base_root)
        finally:
            _run(
                ["git", "worktree", "remove", "--force", str(base_root)],
                cwd=REPOSITORY_ROOT,
                check=False,
            )

    introduced = head_diagnostics - base_diagnostics
    resolved = base_diagnostics - head_diagnostics

    print(
        "Ruff debt: "
        f"{sum(base_diagnostics.values())} -> {sum(head_diagnostics.values())}; "
        f"resolved={sum(resolved.values())}; introduced={sum(introduced.values())}"
    )

    if not introduced:
        print("Ruff ratchet passed: no new diagnostics were introduced.")
        return 0

    print("New Ruff diagnostics:", file=sys.stderr)
    for (path, code, message), count in sorted(introduced.items()):
        suffix = f" (x{count})" if count > 1 else ""
        print(f"- {path}: {code}: {message}{suffix}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", help="Base commit SHA/ref used for the diagnostic baseline")
    args = parser.parse_args()

    try:
        return compare_with_base(args.base)
    except RuntimeError as exc:
        print(f"Ruff ratchet error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
