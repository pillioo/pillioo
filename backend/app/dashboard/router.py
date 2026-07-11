from datetime import date
from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from sqlalchemy import cast, Date, func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models.ticket import Ticket
from app.db.models.approval import Approval

# TODO: 아래 두 모델 import 경로/클래스명이 실제 프로젝트랑 다르면 알려줘
from app.db.models.evidence import TicketEvidenceSnapshot
from app.db.models.report_version import ReportVersion
from app.db.models.audit_log import AuditLog

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _safe(obj, field, default=None):
    return getattr(obj, field, default) if hasattr(obj, field) else default


@router.get("/summary")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """
    전체 티켓 현황 + 운영 큐(Evidence / Review·Approval / Inventory) 반환
    """

    # ==========================================
    # 기존 통계 (변경 없음)
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
        .filter(Ticket.status != "CLOSED", Ticket.priority == "HIGH")
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
        {
            "ticket_id": t.ticket_id,
            "drug_name": t.drug_name,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
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
        # 티켓별 최신 snapshot 1개 (snapshot_version 최대)
        try:
            snapshot = (
                db.query(TicketEvidenceSnapshot)
                .filter(TicketEvidenceSnapshot.ticket_id == t.id)  # TODO: FK 컬럼명 확인 (ticket_id vs public_ticket_id)
                .order_by(TicketEvidenceSnapshot.snapshot_version.desc())
                .first()
            )
        except Exception:
            snapshot = None

        sufficiency = _safe(snapshot, "sufficiency_result", {}) or {}
        weak_sources = sufficiency.get("weak_sources", [])
        failure_reasons = sufficiency.get("failure_reasons", [])
        citation_ready = sufficiency.get("citation_ready", None)  # TODO: 실제 키명 확인

        if weak_sources:
            weak_sources_count += 1
        if citation_ready is False:
            citation_not_ready_count += 1

        evidence_queue.append({
            "ticket_id": t.ticket_id,
            "drug_name": t.drug_name,
            "weak_sources": weak_sources,
            "failure_reasons": failure_reasons,
            "citation_ready": citation_ready,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    # ==========================================
    # 2. Review / Approval queue
    # ==========================================
    try:
        pending_approval_list_q = db.query(Approval).filter(Approval.status == "pending").all()
    except Exception:
        pending_approval_list_q = []

    pending_approval_list = [
        {
            "ticket_id": _safe(a, "public_ticket_id") or _safe(a, "ticket_id"),
            "reviewer": _safe(a, "reviewer"),
            "created_at": a.created_at.isoformat() if _safe(a, "created_at") else None,
        }
        for a in pending_approval_list_q
    ]

    # draft_v2는 있는데 final_v1은 없는 티켓 = revision 대상
    try:
        draft_v2_ticket_ids = {
            r.ticket_id for r in db.query(ReportVersion).filter(ReportVersion.version == "draft_v2").all()
        }
        final_v1_ticket_ids = {
            r.ticket_id for r in db.query(ReportVersion).filter(ReportVersion.version == "final_v1").all()
        }
        revision_ticket_ids = draft_v2_ticket_ids - final_v1_ticket_ids
        revision_requested_tickets = [
            {"ticket_id": t.ticket_id, "drug_name": t.drug_name}
            for t in db.query(Ticket).filter(Ticket.id.in_(revision_ticket_ids)).all()
        ] if revision_ticket_ids else []
    except Exception:
        revision_requested_tickets = []

    # safety check 실패 이력 (audit log에서 step="safety_check", status="failed" 조회)
    # TODO: AuditLog 컬럼명(step/status/action 등) 실제 모델과 확인 필요
    try:
        safety_failed_ticket_ids = {
            log.ticket_id
            for log in db.query(AuditLog)
            .filter(AuditLog.step == "safety_check", AuditLog.status == "failed")
            .all()
        }
        safety_check_failed_tickets = [
            {"ticket_id": t.ticket_id, "drug_name": t.drug_name}
            for t in db.query(Ticket).filter(Ticket.id.in_(safety_failed_ticket_ids)).all()
        ] if safety_failed_ticket_ids else []
    except Exception:
        safety_check_failed_tickets = []

    # ==========================================
    # 3. Inventory impact
    # ==========================================
    # TODO: Ticket에 match_type/total_quantity가 실제로 저장되는 컬럼인지 확인
    # (TicketState -> report 필드로 grounding된다고 문서에 나와있어서 컬럼 존재 가능성 높음)
    inventory_impacted_count = 0
    exact_match_count = 0
    possible_match_count = 0
    high_impact_tickets: List[Dict[str, Any]] = []

    all_tickets = db.query(Ticket).all()
    for t in all_tickets:
        match_type = _safe(t, "match_type")
        total_quantity = _safe(t, "total_quantity", 0) or 0

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

    high_impact_tickets = sorted(
        high_impact_tickets, key=lambda x: x["total_quantity"], reverse=True
    )[:5]

    # ==========================================
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