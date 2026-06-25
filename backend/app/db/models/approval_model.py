from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.db.base import TimeStampedModel


class Approval(TimeStampedModel):
    __tablename__ = "approvals"

    ticket_id = Column(
        ForeignKey("tickets.id"),
        nullable=False
    )

    reviewer = Column(
        String,
        nullable=False
    )

    status = Column(
        String,
        nullable=False
    )
    # approved / rejected / revised

    comment = Column(
        Text,
        nullable=True
    )

    ticket = relationship(
        "Ticket",
        back_populates="approvals"
    )