from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.db.base import TimeStampedModel


class Ticket(TimeStampedModel):
    __tablename__ = "tickets"

    title = Column(String, nullable=False)
    description = Column(String, nullable=True)

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