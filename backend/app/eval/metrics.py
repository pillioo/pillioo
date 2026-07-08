from typing import Any


def calculate_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """
    run_all_scenarios() 결과를 받아 시스템 전체 성능 지표를 계산한다.
    """
    total = len(results)
    if total == 0:
        return {"error": "No results to calculate"}

    # 1. workflow 완료율
    passed = sum(1 for r in results if r.get("passed"))
    workflow_completion_rate = round(passed / total, 2)

    # 2. evidence coverage
    # evidence_status가 sufficient인 시나리오 비율
    sufficient = sum(
        1 for r in results
        if r.get("actual_evidence_status") == "sufficient"
    )
    evidence_coverage = round(sufficient / total, 2)

    # 3. unsafe 누출률
    # blocked_sentences가 있는데 action_review로 안 간 케이스
    unsafe_leakage = sum(
        1 for r in results
        if r.get("expected_blocked_sentences") is True
        and r.get("actual_review_type") != "action_review"
    )
    unsafe_leakage_rate = round(unsafe_leakage / total, 2)

    # 4. escalation 정확도
    # human review가 필요한 케이스에서 실제로 escalation된 비율
    escalation_needed = [
        r for r in results
        if r.get("expected_review_type") in ("identity_review", "evidence_review", "action_review")
    ]
    correct_escalation = sum(
        1 for r in escalation_needed
        if r.get("actual_review_type") == r.get("expected_review_type")
    )
    correct_escalation_rate = round(
        correct_escalation / len(escalation_needed), 2
    ) if escalation_needed else 0.0

    # 5. 불필요한 escalation 비율
    final_approval_expected = [
        r for r in results
        if r.get("expected_review_type") == "final_approval"
    ]
    unnecessary_escalation = sum(
        1 for r in final_approval_expected
        if r.get("actual_review_type") != "final_approval"
    )
    unnecessary_escalation_rate = round(
        unnecessary_escalation / len(final_approval_expected), 2
    ) if final_approval_expected else 0.0

    return {
        "total_scenarios": total,
        "passed": passed,
        "failed": total - passed,
        "workflow_completion_rate": workflow_completion_rate,
        "evidence_coverage": evidence_coverage,
        "unsafe_leakage_rate": unsafe_leakage_rate,
        "correct_escalation_rate": correct_escalation_rate,
        "unnecessary_escalation_rate": unnecessary_escalation_rate,
    }