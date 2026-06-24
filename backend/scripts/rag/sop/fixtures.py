from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


SOP_DOCUMENTS_PATH = Path(__file__).with_name("sop_documents.yaml")


def load_sop_documents(path: Path = SOP_DOCUMENTS_PATH) -> list[dict[str, Any]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))

    if not isinstance(payload, list):
        raise ValueError("SOP fixture file must contain a list of SOP documents.")

    for index, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"SOP fixture at index {index} must be an object.")

    return payload


SOP_DOCUMENTS = load_sop_documents()
