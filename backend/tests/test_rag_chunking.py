from __future__ import annotations

from pathlib import Path

import pytest

from scripts.rag.chunking.document import parse_markdown_document, split_markdown_sections
from scripts.rag.chunking.merging import merge_small_chunks
from scripts.rag.chunking.records import build_chunk_record, chunk_document


def write_document(path: Path, *, frontmatter: str, body: str) -> Path:
    path.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8", newline="\n")
    return path


def test_parse_markdown_document_accepts_bom_and_crlf(tmp_path: Path) -> None:
    path = tmp_path / "doc.md"
    text = (
        "\ufeff---\r\n"
        "document_id: doc-1\r\n"
        "document_type: policy\r\n"
        "event_type: shortage\r\n"
        "event_types: [shortage]\r\n"
        "title: CRLF Policy\r\n"
        "---\r\n"
        "# CRLF Policy\r\n\r\n"
        "Body text.\r\n"
    )
    path.write_text(text, encoding="utf-8")

    document = parse_markdown_document(path)

    assert document.frontmatter["document_id"] == "doc-1"
    assert document.title == "CRLF Policy"
    assert "\r" not in document.body


def test_split_markdown_sections_preserves_preamble() -> None:
    sections = split_markdown_sections("# Title\n\nIntro summary.\n\n## First\nBody.")

    assert [(section.section, section.section_title, section.content) for section in sections] == [
        ("overview", "Overview", "Intro summary."),
        ("first", "First", "Body."),
    ]


def test_merge_small_chunks_checks_actual_merged_token_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "scripts.rag.chunking.merging.count_tokens",
        lambda content: len(content.split()) + content.count("\n\n"),
    )
    chunks = [
        {
            "chunk_id": "doc::section::0000",
            "document_id": "doc",
            "document_type": "policy",
            "section": "section",
            "token_count": 1,
            "content": "left",
            "metadata": {"chunk_tokens_estimate": 1},
        },
        {
            "chunk_id": "doc::section::0001",
            "document_id": "doc",
            "document_type": "policy",
            "section": "section",
            "token_count": 1,
            "content": "right",
            "metadata": {"chunk_tokens_estimate": 1},
        },
    ]

    merged = merge_small_chunks(chunks, min_tokens=2, max_tokens=2)

    assert len(merged) == 2


def test_build_chunk_record_normalizes_ndc_to_list(tmp_path: Path) -> None:
    document = parse_markdown_document(
        write_document(
            tmp_path / "label.md",
            frontmatter=(
                "document_id: label-1\n"
                "document_type: label\n"
                "event_type: label_update\n"
                "event_types: [label_update]\n"
                "title: Label\n"
                "product_ndc: 12345-6789\n"
                "package_ndc:\n"
                "  - 12345-6789-01\n"
                "  - 12345-6789-01"
            ),
            body="# Label\n\n## Warnings\nUse with care.",
        )
    )
    section = split_markdown_sections(document.body)[0]

    chunk = build_chunk_record(document, section, "Use with care.", 0)

    assert chunk["ndc"] == ["12345-6789", "12345-6789-01"]


def test_chunk_document_enforces_prefixed_token_limit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("scripts.rag.chunking.records.count_tokens", lambda content: len(content.split()))
    monkeypatch.setattr(
        "scripts.rag.chunking.records.split_section_content",
        lambda content, max_chars, max_tokens: [content],
    )
    document = parse_markdown_document(
        write_document(
            tmp_path / "policy.md",
            frontmatter=(
                "document_id: policy-1\n"
                "document_type: policy\n"
                "event_type: shortage\n"
                "event_types: [shortage]\n"
                "title: Policy"
            ),
            body="# Policy\n\n## Policy Statement\n" + "word " * 700,
        )
    )

    with pytest.raises(ValueError, match="exceeded token limit"):
        chunk_document(document)
