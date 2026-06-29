from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session

from app.event.normalizer import normalize_event
from app.event.dedup import check_and_save_event
from app.event.ticket_creator import create_ticket
from app.schemas.io import EventUploadRequest, EventUploadResponse

router = APIRouter(prefix="/events", tags=["events"])


@router.post("/upload", response_model=EventUploadResponse)
async def upload_event(payload: EventUploadRequest) -> EventUploadResponse:
    try:
        # 1. 정규화
        event = normalize_event(payload.model_dump())

        # 2. 중복 체크
        dedup_result = check_and_save_event(event.event_id)
        if dedup_result.duplicated:
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "DUPLICATE_EVENT",
                    "message": "Event already processed",
                    "detail": {"event_id": event.event_id}
                }
            )

        # 3. 티켓 생성
        ticket = create_ticket(event)

        return EventUploadResponse(
            event_id=event.event_id,
            status="received",
            ticket_id=ticket.ticket_id,
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/latest")
async def get_latest_events():
    """
    TODO: 2주차에 구현 (P5 DB 준비 완료 후)
    """
    return {"message": "Not implemented yet"}