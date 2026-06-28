import uuid
from datetime import datetime, timezone

# 앞서 작성한 schema.py에서 데이터 모델들을 가져옵니다.
from app.event.schema import EventNormalized, Ticket

# 1주차 MVP용 임시 데이터베이스 (메모리에 티켓 저장)
# 실제 2주차에 DB가 붙으면 이 딕셔너리 대신 PostgreSQL에 INSERT 하게 됩니다.
_mock_tickets_db = {}

def create_ticket(event_data: EventNormalized) -> Ticket:
    """
    정규화된 이벤트 데이터를 받아 시스템의 공식 티켓을 발행하고 저장합니다.
    """
    # 1. 고유한 티켓 ID 생성 (예: T- + 고유번호 앞 8자리)
    ticket_id = f"T-{str(uuid.uuid4())[:8].upper()}"

    # 2. 현재 시간 기록 (UTC 기준)
    created_at = datetime.now(timezone.utc)

    # 3. 티켓 데이터 조립 (P2에서 처리할 priority는 비워둡니다)
    new_ticket = Ticket(
        ticket_id=ticket_id,
        event_type=event_data.event_type,
        drug_name=event_data.drug_name,
        ndc=event_data.ndc,
        lot=event_data.lot,
        classification=event_data.classification,
        priority=None,  
        status="CREATED",
        created_at=created_at
    )

    # 4. 임시 DB에 저장
    _mock_tickets_db[ticket_id] = new_ticket

    return new_ticket


# --- 개발자용 로컬 테스트 코드 ---
if __name__ == "__main__":
    from datetime import date
    from app.event.schema import EventType, Classification

    # 테스트를 위해 팀원 2의 normalizer가 넘겨줬다고 가정한 가짜 데이터를 만듭니다.
    mock_event = EventNormalized(
        event_id="FDA-2026-001",
        event_type=EventType.RECALL,
        drug_name="midazolam",
        ndc="00641601441",
        lot="LOT-A",
        classification=Classification.CLASS_I,
        status="ongoing",
        recall_initiation_date=date(2026, 6, 1)
    )
    
    print("=== 티켓 생성 테스트 ===")
    ticket_result = create_ticket(mock_event)
    
    # Pydantic 객체를 JSON 문자열로 예쁘게 출력
    print(ticket_result.model_dump_json(indent=2))