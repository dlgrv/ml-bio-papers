"""Repo root and the Russian rules pack (translate/rules/ru.json)."""

from __future__ import annotations

import json
import os


def default_root() -> str:
    """Repo root inferred from this file's location (<root>/translate/lib/)."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load_rules(root: str | None = None) -> dict:
    """Load translate/rules/ru.json (banned calques, style markers)."""
    path = os.path.join(root or default_root(), "translate", "rules", "ru.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)
