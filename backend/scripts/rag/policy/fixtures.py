from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.rag.common import load_yaml_documents


POLICY_DOCUMENTS_PATH = Path(__file__).with_name("policy_documents.yaml")


def load_policy_documents(path: Path = POLICY_DOCUMENTS_PATH) -> list[dict[str, Any]]:
    return load_yaml_documents(path, "Policy")


POLICY_DOCUMENTS = load_policy_documents()