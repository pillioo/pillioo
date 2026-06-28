from __future__ import annotations

from pathlib import Path

from scripts.rag.policy.fixtures import POLICY_DOCUMENTS
from scripts.rag.policy.rendering import render_policy_document, slugify


ROOT_DIR = Path(__file__).resolve().parents[3]
POLICY_DIR = ROOT_DIR / "data" / "rag" / "documents" / "policy"


def write_policy_documents() -> None:
    POLICY_DIR.mkdir(parents=True, exist_ok=True)

    for existing_path in POLICY_DIR.glob("*.md"):
        existing_path.unlink(missing_ok=True)

    for policy in POLICY_DOCUMENTS:
        document_id = policy["document_id"]
        path = POLICY_DIR / f"{slugify(document_id)}.md"

        path.write_text(
            render_policy_document(policy),
            encoding="utf-8",
        )

        print(f"[OK] Saved policy document: {path.name}")

    print()
    print("[SUMMARY]")
    print(f"saved={len(POLICY_DOCUMENTS)}")
    print(f"doc_dir={POLICY_DIR}")


if __name__ == "__main__":
    write_policy_documents()