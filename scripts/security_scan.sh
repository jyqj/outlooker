#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Backend dependency audit (pip-audit) ==="
if command -v pip-audit >/dev/null 2>&1; then
  (cd "$PROJECT_ROOT/backend" && pip-audit)
else
  echo "pip-audit 未安装，跳过。可运行 'python -m pip install pip-audit' 后重试。" >&2
fi

echo
echo "=== Frontend dependency audit (npm audit --audit-level=high) ==="
if command -v npm >/dev/null 2>&1; then
  (cd "$PROJECT_ROOT/frontend" && npm audit --audit-level=high || true)
else
  echo "npm 未安装，跳过前端审计。" >&2
fi
