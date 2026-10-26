"""Local JSON persistence helpers for property and habitat state."""

import json
from pathlib import Path
from typing import Optional

from backend import config


def read_data(data_file: Optional[Path] = None) -> dict:
    """Read persisted property data from JSON storage."""
    target = data_file or config.DATA_FILE
    if target.exists():
        try:
            return json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def write_data(data: dict, data_file: Optional[Path] = None) -> None:
    """Write property data dictionary to JSON storage."""
    target = data_file or config.DATA_FILE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")
