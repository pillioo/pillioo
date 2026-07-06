from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy import func

Base = declarative_base()
class TimeStampedModel(Base):
    __abstract__ = True
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

from app.db.models.ticket import Ticket
from app.db.models.approval_model import Approval
from app.db.models.audit_log_model import AuditLog
from app.db.models.report_version_model import ReportVersion