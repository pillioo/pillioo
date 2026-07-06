from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.db.base import TimeStampedModel


class Ticket(TimeStampedModel):
    __tablename__ = "tickets"

    # 1. 시스템 내부 티켓 식별자 및 상태
    ticket_id = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, nullable=False, default="CREATED")
    workflow_stage = Column(String, nullable=False, default="PENDING_INVENTORY")
    priority = Column(String, nullable=True)

    # 2. 약품 및 이벤트 기본 정보
    event_type = Column(String, nullable=False)
    drug_name = Column(String, nullable=False)
    ndc = Column(String, nullable=False, index=True)
    lot = Column(String, nullable=True)
    classification = Column(String, nullable=True)

    # 3. RAG/Evidence 및 외부 연동 데이터
    recall_number = Column(String, nullable=True)
    reason_for_recall = Column(String, nullable=True)
    product_description = Column(String, nullable=True)

    # 4. 중복 및 상태 변경 감지(Diff Detector)용 핵심 데이터
    openfda_id = Column(String, unique=True, index=True, nullable=True)
    source_status = Column(String, nullable=True)

    # P4 Relationships
    approvals = relationship(
        "Approval",
        back_populates="ticket"
    )

    audit_logs = relationship(
        "AuditLog",
        back_populates="ticket"
    )

    report_versions = relationship(
        "ReportVersion",
        back_populates="ticket"
    )