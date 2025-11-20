from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from ..config import DEFAULT_EMAIL_LIMIT, MAX_EMAIL_LIMIT as CONFIG_MAX_EMAIL_LIMIT

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "backend" / "configs"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)

ACCOUNTS_CONFIG_FILES: List[Path] = [
    CONFIG_DIR / "config.txt",
    CONFIG_DIR / "accounts.txt",
]

SYSTEM_CONFIG_FILE = CONFIG_DIR / "system_config.json"
SYSTEM_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

SYSTEM_CONFIG_DEFAULTS: Dict[str, Any] = {
    "email_limit": DEFAULT_EMAIL_LIMIT,
}

VALID_MERGE_MODES = {"update", "skip", "replace"}
MIN_EMAIL_LIMIT = 1
MAX_EMAIL_LIMIT = CONFIG_MAX_EMAIL_LIMIT
