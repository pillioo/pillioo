from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# 사전 정의된 표준 스키마를 가져온다.
from app.schemas.event import EventNormalized
from app.schemas.common import EventType, Classification

# --- 최종 티켓 모델 ---
class Ticket(BaseModel):
    ticket_id: str
    event_type: EventType
    drug_name: str
    ndc: str
    lot: Optional[str] = None
    classification: Optional[Classification] = None
    priority: Optional[str] = None
    status: str = "CREATED"
    created_at: datetime

class DedupResponse(BaseModel):
    duplicated: bool