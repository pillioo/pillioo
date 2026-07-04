from __future__ import annotations

import pytest

from scripts.rag.embedding.load_milvus import to_milvus_row, truncate


def make_embedded_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "chunk_id": "chunk-1",
        "embedding": [0.1, 0.2],
        "content": "body",
        "document_id": "doc-1",
        "document_type": "label",
        "event_type": "label_update",
        "event_types": ["label_update"],
        "section": "warnings",
        "section_title": "warnings",
        "title": "Label",
        "source_path": "data/rag/documents/label/doc.md",
        "drug_name": "drug",
        "normalized_drug_name": "drug",
        "rxnorm_rxcui": "123",
        "classification": None,
        "ndc": ["12345-6789-01"],
        "lot": None,
        "recall_number": None,
        "metadata": {},
        "embedding_model": "text-embedding-3-small",
        "content_hash": "hash",
    }
    record.update(overrides)
    return record


def test_to_milvus_row_uses_filterable_ndc_array() -> None:
    row = to_milvus_row(make_embedded_record(ndc="12345-6789-01"))

    assert row["ndc"] == ["12345-6789-01"]
    assert "ndc_json" not in row


def test_to_milvus_row_rejects_truncated_primary_key() -> None:
    record = make_embedded_record(chunk_id="x" * 513)

    with pytest.raises(ValueError, match="field=chunk_id"):
        to_milvus_row(record)


def test_truncate_logs_non_strict_truncation(capsys: pytest.CaptureFixture[str]) -> None:
    value = truncate("abcdef", 3, field="content", chunk_id="chunk-1")

    assert value == "abc"
    assert "field=content chunk_id=chunk-1 truncated 6 -> 3 chars" in capsys.readouterr().out
