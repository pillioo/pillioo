from app.event.dedup import is_duplicate, save_event

@router.post("/upload", response_model=EventUploadResponse)
async def upload_event(payload: EventUploadRequest) -> EventUploadResponse:
    try:
        # 1. 정규화
        event = normalize_event(payload.model_dump())

        # 2. 중복 여부만 확인 (아직 저장 안 함)
        if is_duplicate(event.event_id):
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "DUPLICATE_EVENT",
                    "message": "Event already processed",
                    "detail": {"event_id": event.event_id}
                }
            )

        # 3. 티켓 생성 (성공해야만 저장)
        ticket = create_ticket(event)

        # 4. 티켓 생성 성공 후에 저장
        save_event(event.event_id)

        # 5. duplicated: False 명시
        return EventUploadResponse(
            event_id=event.event_id,
            status="received",
            ticket_id=ticket.ticket_id,
            duplicated=False,
        )

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))