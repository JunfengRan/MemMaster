from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_catalog() -> dict:
    return yaml.safe_load((ROOT / "experiments" / "catalog.yaml").read_text(encoding="utf-8"))


def load_questions(dev: bool = False) -> list[dict]:
    data = yaml.safe_load  # noqa - keep yaml imported for configs
    import json

    payload = json.loads((ROOT / "datasets" / "tob-memory-v1" / "questions.json").read_text(encoding="utf-8"))
    return payload["dev_items"] if dev else payload["items"]
