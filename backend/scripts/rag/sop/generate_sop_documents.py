from __future__ import annotations

from pathlib import Path

from scripts.rag.sop.fixtures import SOP_DOCUMENTS
from scripts.rag.sop.rendering import render_sop_document, slugify


ROOT_DIR = Path(__file__).resolve().parents[3]
SOP_DIR = ROOT_DIR / "data" / "rag" / "documents" / "sop"


def write_sop_documents() -> None:
    SOP_DIR.mkdir(parents=True, exist_ok=True)

    for existing_path in SOP_DIR.glob("*.md"):
        existing_path.unlink()

    for sop in SOP_DOCUMENTS:
        document_id = sop["document_id"]
        path = SOP_DIR / f"{slugify(document_id)}.md"

        path.write_text(
            render_sop_document(sop),
            encoding="utf-8",
        )

        print(f"[OK] Saved SOP document: {path.name}")

    print()
    print("[SUMMARY]")
    print(f"saved={len(SOP_DOCUMENTS)}")
    print(f"doc_dir={SOP_DIR}")


if __name__ == "__main__":
    write_sop_documents()
