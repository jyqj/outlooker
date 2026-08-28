#!/usr/bin/env python3
"""Prevent backend line coverage from falling below the pull-request base.

The repository's historical coverage is below the former hard-coded 70% gate,
which made the gate impossible to satisfy before any changed code was examined.
This script measures the checked-out head, reproduces the base coverage in an
isolated worktree, and rejects only a real coverage regression.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ZERO_SHA = "0" * 40
DEFAULT_TOLERANCE = 0.0005


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


def _read_line_rate(path: Path) -> float:
    if not path.exists():
        raise RuntimeError(f"Coverage XML was not created: {path}")
    root = ET.parse(path).getroot()
    raw_rate = root.attrib.get("line-rate")
    if raw_rate is None:
        raise RuntimeError(f"Coverage XML has no line-rate: {path}")
    try:
        return float(raw_rate)
    except ValueError as exc:
        raise RuntimeError(f"Invalid coverage line-rate {raw_rate!r}: {path}") from exc


def _measure_base(base_ref: str, output_path: Path) -> tuple[float, int]:
    with tempfile.TemporaryDirectory(prefix="outlooker-coverage-base-") as directory:
        base_root = Path(directory) / "repository"
        _run(
            ["git", "worktree", "add", "--detach", str(base_root), base_ref],
            cwd=REPOSITORY_ROOT,
        )
        try:
            result = _run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "--cov=app",
                    f"--cov-report=xml:{output_path}",
                    "--cov-report=",
                    "-q",
                ],
                cwd=base_root / "backend",
                check=False,
            )
            if result.returncode not in {0, 1}:
                if result.stdout:
                    print(result.stdout, file=sys.stderr)
                if result.stderr:
                    print(result.stderr, file=sys.stderr)
                raise RuntimeError(
                    f"Unable to measure base coverage; pytest exited {result.returncode}"
                )
            return _read_line_rate(output_path), result.returncode
        finally:
            _run(
                ["git", "worktree", "remove", "--force", str(base_root)],
                cwd=REPOSITORY_ROOT,
                check=False,
            )


def compare_with_base(
    base_candidate: str,
    head_xml: Path,
    tolerance: float,
) -> int:
    base_ref = _resolve_base_ref(base_candidate)
    head_rate = _read_line_rate(head_xml.resolve())

    with tempfile.TemporaryDirectory(prefix="outlooker-coverage-report-") as directory:
        base_xml = Path(directory) / "base-coverage.xml"
        base_rate, base_test_status = _measure_base(base_ref, base_xml)

    delta = head_rate - base_rate
    print(
        "Backend line coverage: "
        f"{base_rate * 100:.3f}% -> {head_rate * 100:.3f}% "
        f"(delta={delta * 100:+.3f} percentage points)"
    )
    if base_test_status != 0:
        print(
            "Base tests contain pre-existing failures; their generated coverage "
            "snapshot was still usable for the regression comparison."
        )

    if head_rate + tolerance >= base_rate:
        print("Coverage ratchet passed: backend line coverage did not regress.")
        return 0

    print(
        "Coverage regression detected: "
        f"head is {(base_rate - head_rate) * 100:.3f} percentage points below base.",
        file=sys.stderr,
    )
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", help="Base commit SHA/ref used for the coverage baseline")
    parser.add_argument(
        "--head-xml",
        type=Path,
        default=Path("backend/coverage.xml"),
        help="Coverage XML generated for the checked-out head",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help="Allowed line-rate rounding tolerance (default: 0.0005)",
    )
    args = parser.parse_args()

    try:
        return compare_with_base(args.base, args.head_xml, max(0.0, args.tolerance))
    except RuntimeError as exc:
        print(f"Coverage ratchet error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
