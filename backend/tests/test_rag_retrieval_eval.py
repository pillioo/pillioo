from __future__ import annotations

from scripts.rag.eval.run_retrieval_eval import (
    dedupe_hits,
    evaluate_empty_hits,
    evaluate_hit_set,
    evaluate_hits,
    matches_expected,
)


def test_matches_expected_supports_content_contains_and_any_section() -> None:
    hit = {
        "document_type": "recall_notice",
        "event_type": "recall",
        "section": "recall_notice",
        "recall_number": "D-0277-2024",
        "content": "Reason for recall: Superpotent drug product.",
    }

    assert matches_expected(
        hit,
        {
            "document_type": "recall_notice",
            "event_type": "recall",
            "recall_number": "D-0277-2024",
            "any_section": ["recall_notice", "reason_for_recall"],
            "content_contains": ["superpotent", "drug"],
        },
    )


def test_evaluate_hits_returns_first_matching_rank() -> None:
    hits = [
        {"chunk_id": "wrong", "document_type": "label", "score": 0.9},
        {"chunk_id": "right", "document_type": "policy", "score": 0.8},
    ]

    result = evaluate_hits(hits, {"document_type": "policy"})

    assert result["passed"] is True
    assert result["rank"] == 2
    assert result["top_chunk_id"] == "wrong"
    assert result["top_score"] == 0.9
    assert result["failures"] == []


def test_evaluate_hits_reports_failure_without_match() -> None:
    result = evaluate_hits(
        [{"chunk_id": "wrong", "document_type": "label", "score": 0.7}],
        {"document_type": "recall_notice"},
    )

    assert result["passed"] is False
    assert result["rank"] is None
    assert result["top_chunk_id"] == "wrong"
    assert result["failures"] == ["no hit matched expected.any_hit"]


def test_dedupe_hits_keeps_first_hit_for_repeated_field() -> None:
    hits = [
        {"chunk_id": "first", "content_hash": "same", "score": 0.9},
        {"chunk_id": "duplicate", "content_hash": "same", "score": 0.8},
        {"chunk_id": "second", "content_hash": "other", "score": 0.7},
        {"chunk_id": "missing_hash", "score": 0.6},
    ]

    deduped = dedupe_hits(hits, "content_hash")

    assert [hit["chunk_id"] for hit in deduped] == ["first", "second", "missing_hash"]


def test_evaluate_hits_supports_nested_any_hit_and_set_expectations() -> None:
    hits = [
        {
            "chunk_id": "chunk-1",
            "source_path": "source.md",
            "content": "Recall number D-0277-2024. Superpotent drug.",
            "document_type": "recall_notice",
            "section": "recall_notice",
            "recall_number": "D-0277-2024",
            "ndc": ["71449-072-41"],
            "lot": "2331062",
        }
    ]

    result = evaluate_hits(
        hits,
        {
            "any_hit": {
                "document_type": "recall_notice",
                "recall_number": "D-0277-2024",
                "content_contains": "superpotent",
            },
            "set": {
                "required_document_types": ["recall_notice"],
                "required_sections": ["recall_notice"],
                "min_evidence_count": 1,
                "must_have_citations": True,
                "ndc_match": ["71449-072-41"],
                "lot_match": ["2331062"],
            },
        },
    )

    assert result["passed"] is True
    assert result["rank"] == 1
    assert result["failures"] == []


def test_evaluate_hit_set_reports_missing_coverage() -> None:
    result = evaluate_hit_set(
        [{"chunk_id": "chunk-1", "source_path": "", "content": "body", "document_type": "label", "section": "warnings"}],
        {
            "required_document_types": ["recall_notice"],
            "required_sections": ["recall_notice"],
            "min_evidence_count": 2,
            "must_have_citations": True,
        },
    )

    assert result["passed"] is False
    assert "min_evidence_count 1 < 2" in result["failures"]
    assert "missing document_types: ['recall_notice']" in result["failures"]
    assert "missing sections: ['recall_notice']" in result["failures"]
    assert "one or more hits missing citation fields" in result["failures"]


def test_evaluate_empty_hits_can_mark_zero_evidence_as_expected() -> None:
    result = evaluate_empty_hits([], {"set": {"min_evidence_count": 0}})

    assert result == {
        "passed": True,
        "rank": None,
        "top_chunk_id": None,
        "top_score": None,
        "failures": [],
    }
