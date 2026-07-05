import json
from datetime import datetime
from pydantic import ValidationError

# 수진님의 실제 프로젝트 경로에 맞게 임포트 해주세요. (예: app.schemas 등)
# 여기서는 schema.py 파일 안에 Ticket 모델이 있다고 가정합니다.
from app.event.schema import Ticket 
from app.schemas.common import TicketStatus  # Enum이 있다면 임포트

# 1. 방금 만든 극한의 복합 JSON 데이터 불러오기
# (경로는 파일 위치에 맞게 수정해주세요)
with open('app/event/complex_edge_case.json', 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

# 2. Ticket 스키마 검증 테스트
print("🔍 스키마 검증 테스트를 시작합니다...\n")

try:
    # 💡 주의: 원본 JSON에는 ticket_id나 event_type 같은 Ticket의 '필수 필드'가 없습니다.
    # 실제 파이프라인에서는 Normalizer(정규화기)가 이 뼈대를 만들어 줍니다.
    # 테스트를 위해 필수 뼈대만 임시로 만들어주고, 복합 데이터를 밀어 넣습니다.
    
    test_payload = {
        "ticket_id": "TICKET-TEST-001",
        "event_type": "recall",         # 기본 이벤트 타입 지정
        "drug_name": "Midazolam HCl",   # 테스트용 약물명
        "ndc": raw_data.get("product_ndc", "0000-0000-00"),
        "created_at": datetime.now(),
        **raw_data  # 🌟 핵심: 여기에 우리가 만든 복합 엣지 케이스 데이터를 통째로 엎어버립니다!
    }

    # Pydantic 스키마에 데이터 통과시키기
    ticket = Ticket(**test_payload)
    
    print("✅ 테스트 성공! 엣지 케이스 데이터가 스키마를 무사히 통과했습니다.")
    print("--- 생성된 Ticket 객체 ---")
    print(ticket.model_dump_json(indent=2))  # Pydantic v2 기준 (v1은 json() 사용)

except ValidationError as e:
    print("❌ 삐빅! 에러 발생 (ValidationError): 스키마가 이 데이터를 거부했습니다.")
    print(e)