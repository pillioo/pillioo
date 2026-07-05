import logging
from typing import Optional, Tuple
from app.schemas.event import EventNormalized

from app.event.schema import Ticket
from app.schemas.common import TicketStatus

logger = logging.getLogger(__name__)

class DiffDetector:
    def __init__(self, repository):
        """
        repository: DB 대신 1주차에 사용하기로 한 Local Mock Repository 
        또는 나중에 교체될 DB 세션 객체입니다.
        """
        self.repo = repository

    def detect_difference(self, incoming_event: EventNormalized) -> Tuple[str, Optional[Ticket]]:
        """
        새로 수집된 이벤트와 기존 저장된 데이터를 비교하여 분기 결과를 반환합니다.
        반환값: (분기 결과['NEW', 'DUPLICATE', 'STATUS_CHANGED'], 관련 티켓 객체)
        """
        event_id = incoming_event.recall_number  # 식별자로 recall_number 사용
        
        # 1. 로컬 저장소(DB)에서 기존에 저장된 동일한 티켓이 있는지 조회
        existing_ticket = self.repo.find_by_recall_number(event_id)
        
        # [Case 1] 완전 신규: DB에 기존 기록이 없는 경우
        if not existing_ticket:
            logger.info(f"[DiffDetector] 완전 신규 이벤트 감지: {event_id}")
            return "NEW", None
            
        # [Case 2] 단순 중복: 기존에 있고, 리콜의 핵심 상태가 일치하는 경우
        # (incoming_event의 status와 기존 ticket의 속성을 비교합니다)
        # ⚠️ 스키마 테스트에서 발견했듯, 내부 티켓 status(CREATED 등)와 외부 status를 구분해서 비교해야 합니다.
        if existing_ticket.status == TicketStatus.CREATED: 
            # 예시: 기존 티켓이 이미 처리 중이고 변경 사항이 없는 경우
            # 실제 구현 시에는 incoming_event.reason_for_recall 등을 비교하여 디테일한 중복을 체크할 수 있습니다.
            if existing_ticket.reason_for_recall == incoming_event.reason_for_recall:
                logger.info(f"[DiffDetector] 단순 중복 이벤트 감지 (Skip): {event_id}")
                return "DUPLICATE", existing_ticket

        # [Case 3] 상태 변경: 기존에 존재하지만 내용이나 상태가 바뀐 경우
        logger.info(f"[DiffDetector] 상태 변경 이벤트 감지 (Update 필요): {event_id}")
        return "STATUS_CHANGED", existing_ticket

    def process_by_result(self, result_type: str, incoming_event: EventNormalized, existing_ticket: Optional[Ticket] = None):
        """
        판정된 결과에 따라 실제 데이터를 생성하거나 수정하는 파이프라인 트리거 함수입니다.
        """
        if result_type == "NEW":
            # TODO: 새 티켓 생성 로직 호출
            # new_ticket = Ticket(...)
            # self.repo.save(new_ticket)
            pass
        elif result_type == "STATUS_CHANGED":
            # TODO: 기존 티켓 정보 업데이트 및 워크플로우 재시작 로직 호출
            pass
        elif result_type == "DUPLICATE":
            # 무시하고 다음 단계로 진행하지 않음
            pass