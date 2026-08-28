#!/usr/bin/env python3
"""Fail CI only when a change introduces new Mypy diagnostics.

The repository has a historical type-checking backlog. This ratchet keeps the
complete inventory visible while preventing pull requests from increasing the
backlog. Existing errors must stay stable or shrink; newly introduced errors
fail the build.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ZERO_SHA = "0" * 40
DiagnosticKey = tuple[str, str, str]
_DIAGNOSTIC_PATTERN = re.compile(
    r"^(?P<filename>.+?):(?P<line>\d+)(?::(?P<column>\d+))?: "
    r"error: (?P<message>.*?)(?:  \[(?P<code>[^\]]+)\])?$"
)


def _run(
    command: list[str],
    *,
    cwd: Path,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
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


def _relative_path(filename: str, root: Path) -> str:
    raw_path = Path(filename)
    path = raw_path if raw_path.is_absolute() else root / raw_path
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return raw_path.as_posix()


def _collect_diagnostics(root: Path) -> Counter[DiagnosticKey]:
    result = _run(
        [
            "mypy",
            "backend/app",
            "--config-file",
            "mypy.ini",
            "--show-error-codes",
            "--no-pretty",
        ],
        cwd=root,
        check=False,
    )
    if result.returncode not in {0, 1}:
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise RuntimeError(f"Mypy failed with exit code {result.returncode}")

    diagnostics: Counter[DiagnosticKey] = Counter()
    for line in f"{result.stdout}\n{result.stderr}".splitlines():
        match = _DIAGNOSTIC_PATTERN.match(line.strip())
        if not match:
            continue
        diagnostics[
            (
                _relative_path(match.group("filename"), root),
                match.group("code") or "UNKNOWN",
                match.group("message").strip(),
            )
        ] += 1

    if result.returncode == 1 and not diagnostics:
        if result.stdout:
            print(result.stdout, file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise RuntimeError("Mypy failed but no parseable diagnostics were found")
    return diagnostics


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

    with tempfile.TemporaryDirectory(prefix="outlooker-mypy-base-") as directory:
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
        "Mypy debt: "
        f"{sum(base_diagnostics.values())} -> {sum(head_diagnostics.values())}; "
        f"resolved={sum(resolved.values())}; introduced={sum(introduced.values())}"
    )

    if not introduced:
        print("Mypy ratchet passed: no new type errors were introduced.")
        return 0

    print("New Mypy diagnostics:", file=sys.stderr)
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
        print(f"Mypy ratchet error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
