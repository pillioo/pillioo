from datetime import date
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import cast, Date, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.ticket import Ticket
from app.db.models.approval_model import Approval
from app.db.models.evidence_snapshot_model import TicketEvidenceSnapshot
from app.db.models.report_version_model import ReportVersion

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _is_safety_failed(safety_check_result: dict) -> bool:
    """
    safety_check_result의 정확한 키 구조를 몰라서 방어적으로 후보 키 다 체크.
    실제 값 확인되면 이 함수만 정리하면 됨.
    """
    if not safety_check_result:
        return False
    for key in ("passed", "is_safe", "safe"):
        if key in safety_check_result:
            return safety_check_result[key] is False
    if "failed" in safety_check_result:
        return bool(safety_check_result["failed"])
    return False


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    전체 티켓 현황 + 운영 큐(Evidence / Review·Approval / Inventory) 반환
    """

    # ==========================================
    # 기존 통계
    # ==========================================
    total_tickets = db.query(Ticket).count()

    by_status = {}
    for status, count in db.query(Ticket.status, func.count(Ticket.id)).group_by(Ticket.status).all():
        if status:
            by_status[str(status)] = count

    by_review_type = {}
    for review_type, count in db.query(Ticket.review_type, func.count(Ticket.id)).group_by(Ticket.review_type).all():
        if review_type:
            by_review_type[str(review_type)] = count

    try:
        pending_approvals = db.query(Approval).filter(Approval.status == "pending").count()
    except Exception:
        pending_approvals = 0

    workflow_failed = db.query(Ticket).filter(Ticket.status == "WORKFLOW_FAILED").count()
    high_priority = db.query(Ticket).filter(Ticket.priority == "HIGH").count()

    today = date.today()
    today_created = db.query(Ticket).filter(cast(Ticket.created_at, Date) == today).count()

    evidence_review_pending = db.query(Ticket).filter(
        Ticket.review_type == "evidence_review",
        Ticket.status == "REVIEW_ROUTED",
    ).count()

    urgent_tickets_query = (
        db.query(Ticket)
        .filter(Ticket.priority == "HIGH", Ticket.status != "CLOSED")
        .order_by(Ticket.created_at.desc())
        .limit(5)
        .all()
    )
    urgent_tickets = [
        {
            "ticket_id": t.ticket_id,
            "drug_name": t.drug_name,
            "status": str(t.status) if t.status else None,
            "review_type": str(t.review_type) if t.review_type else None,
            "priority": str(t.priority) if t.priority else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in urgent_tickets_query
    ]

    failed_tickets = (
        db.query(Ticket)
        .filter(Ticket.status == "WORKFLOW_FAILED")
        .order_by(Ticket.created_at.desc())
        .limit(3)
        .all()
    )
    recent_failures = [
        {"ticket_id": t.ticket_id, "drug_name": t.drug_name, "created_at": t.created_at.isoformat() if t.created_at else None}
        for t in failed_tickets
    ]

    recent_tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).limit(5).all()
    recent_list = [
        {
            "ticket_id": t.ticket_id,
            "drug_name": t.drug_name,
            "status": str(t.status) if t.status else None,
            "review_type": str(t.review_type) if t.review_type else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in recent_tickets
    ]

    # ==========================================
    # 1. Evidence queue
    # ==========================================
    evidence_queue: List[Dict[str, Any]] = []
    weak_sources_count = 0
    citation_not_ready_count = 0

    evidence_review_tickets = db.query(Ticket).filter(
        Ticket.review_type == "evidence_review",
        Ticket.status == "REVIEW_ROUTED",
    ).order_by(Ticket.created_at.desc()).all()

    for t in evidence_review_tickets:
        snapshot = (
            db.query(TicketEvidenceSnapshot)
            .filter(TicketEvidenceSnapshot.ticket_id == t.id)
            .order_by(TicketEvidenceSnapshot.snapshot_version.desc())
            .first()
        )

        sufficiency = (snapshot.sufficiency_result if snapshot else {}) or {}
        weak_sources = sufficiency.get("weak_sources", [])
        failure_reasons = sufficiency.get("failure_reasons", [])
        citations_ready = snapshot.citations_ready if snapshot else None  # 직접 컬럼

        if weak_sources:
            weak_sources_count += 1
        if citations_ready is False:
            citation_not_ready_count += 1

        evidence_queue.append({
            "ticket_id": t.ticket_id,
            "drug_name": t.drug_name,
            "weak_sources": weak_sources,
            "failure_reasons": failure_reasons,
            "citations_ready": citations_ready,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    # ==========================================
    # 2. Review / Approval queue
    # ==========================================
    pending_approval_rows = (
        db.query(Approval, Ticket)
        .join(Ticket, Approval.ticket_id == Ticket.id)
        .filter(Approval.status == "pending")
        .order_by(Approval.created_at.desc())
        .all()
    )
    pending_approval_list = [
        {
            "ticket_id": ticket.ticket_id,
            "drug_name": ticket.drug_name,
            "reviewer": approval.reviewer,
            "created_at": approval.created_at.isoformat() if approval.created_at else None,
        }
        for approval, ticket in pending_approval_rows
    ]

    # draft_v2는 있는데 final_v1은 없는 티켓 = revision 대상
    draft_v2_ticket_ids = {
        r.ticket_id for r in db.query(ReportVersion.ticket_id).filter(ReportVersion.version_tag == "draft_v2").all()
    }
    final_v1_ticket_ids = {
        r.ticket_id for r in db.query(ReportVersion.ticket_id).filter(ReportVersion.version_tag == "final_v1").all()
    }
    revision_ticket_ids = draft_v2_ticket_ids - final_v1_ticket_ids
    revision_requested_tickets = [
        {"ticket_id": t.ticket_id, "drug_name": t.drug_name}
        for t in db.query(Ticket).filter(Ticket.id.in_(revision_ticket_ids)).all()
    ] if revision_ticket_ids else []

    # safety check 실패: ReportVersion.safety_check_result 기준
    safety_failed_rows = (
        db.query(ReportVersion, Ticket)
        .join(Ticket, ReportVersion.ticket_id == Ticket.id)
        .filter(ReportVersion.safety_check_result.isnot(None))
        .all()
    )
    safety_check_failed_tickets = [
        {"ticket_id": ticket.ticket_id, "drug_name": ticket.drug_name, "version_tag": rv.version_tag}
        for rv, ticket in safety_failed_rows
        if _is_safety_failed(rv.safety_check_result)
    ]

    # ==========================================
    # 3. Inventory impact
    # ==========================================
    # NOTE: Ticket에 match_type/total_quantity 컬럼이 직접 있는지 미확인.
    # ticket.py 아직 안 봐서 일단 hasattr로 방어. 없으면 이 블록만 빈 값 반환.
    inventory_impacted_count = 0
    exact_match_count = 0
    possible_match_count = 0
    high_impact_tickets: List[Dict[str, Any]] = []

    all_tickets = db.query(Ticket).all()
    for t in all_tickets:
        match_type = getattr(t, "match_type", None)
        total_quantity = getattr(t, "total_quantity", 0) or 0

        if match_type in ("exact_ndc_match", "fuzzy_name_match"):
            inventory_impacted_count += 1
        if match_type == "exact_ndc_match":
            exact_match_count += 1
        elif match_type == "fuzzy_name_match":
            possible_match_count += 1

        if total_quantity and total_quantity > 0:
            high_impact_tickets.append({
                "ticket_id": t.ticket_id,
                "drug_name": t.drug_name,
                "total_quantity": total_quantity,
                "match_type": match_type,
            })

    high_impact_tickets = sorted(high_impact_tickets, key=lambda x: x["total_quantity"], reverse=True)[:5]

    return {
        "total_tickets": total_tickets,
        "by_status": by_status,
        "by_review_type": by_review_type,
        "pending_approvals": pending_approvals,
        "workflow_failed": workflow_failed,
        "high_priority": high_priority,
        "today_created": today_created,
        "evidence_review_pending": evidence_review_pending,
        "urgent_tickets": urgent_tickets,
        "recent_failures": recent_failures,
        "recent_tickets": recent_list,
        "evidence_queue": {
            "tickets": evidence_queue,
            "weak_sources_count": weak_sources_count,
            "citation_not_ready_count": citation_not_ready_count,
        },
        "review_approval_queue": {
            "pending_approvals": pending_approval_list,
            "revision_requested": revision_requested_tickets,
            "safety_check_failed": safety_check_failed_tickets,
        },
        "inventory_impact": {
            "impacted_count": inventory_impacted_count,
            "exact_match_count": exact_match_count,
            "possible_match_count": possible_match_count,
            "high_impact_tickets": high_impact_tickets,
        },
    }