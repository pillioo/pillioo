# Pillioo Backend

## Overview

Pillioo Backend는 의약품 리콜 및 안전 이벤트를 티켓 기반 워크플로우로 처리하는 백엔드 시스템입니다.

재고 영향 확인, RAG 기반 근거 검색, 보고서 초안 생성, 약사 검토, 티켓 기반 채팅, 감사 이력 관리를 지원합니다.

The backend is designed as a decision-support system. Generated drafts and workflow outputs are reviewable artifacts, not autonomous medical or operational decisions.

## Project Structure

```text
backend/
├─ app/
│  ├─ event/
│  ├─ inventory/
│  ├─ orchestration/
│  ├─ rag/
│  ├─ review/
│  ├─ chat/
│  └─ db/
├─ scripts/rag/
├─ tests/
└─ docker-compose.yml
```

| Path | Responsibility |
|---|---|
| `app/event/` | 안전 이벤트 수집, 정규화 및 중복 처리 |
| `app/inventory/` | 내부 재고 매칭 및 영향 확인 |
| `app/orchestration/` | 티켓 기반 워크플로우 실행 |
| `app/rag/` | 근거 검색, reranking, 충분성 평가 및 evidence snapshot 관리 |
| `app/review/` | 약사 검토, 승인, 보고서 버전 및 감사 이력 처리 |
| `app/chat/` | 티켓 범위의 근거 기반 채팅 |
| `app/db/` | SQLAlchemy session 및 database model 관리 |
| `scripts/rag/` | Chunking, embedding, Milvus loading 및 retrieval evaluation |
| `tests/` | Backend test suite |

## Getting Started

```powershell
cd backend
Copy-Item .env.example .env
docker compose up -d postgres fastapi
```

위 명령은 PostgreSQL과 FastAPI를 포함한 core backend runtime을 실행합니다.

## Environment Variables

백엔드 실행 전 `.env.example`을 복사해 환경변수를 설정합니다.

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection URL |
| `OPENAI_API_KEY` | LLM API key |
| `LLM_MODEL` | 보고서 초안, 채팅 및 수정에 사용하는 model |
| `EMBEDDING_MODEL` | Evidence embedding model |
| `MILVUS_URI` | Milvus connection URI |
| `MILVUS_COLLECTION` | Evidence collection name |

실제 API key, password, deployment URL은 Git에 커밋하지 않습니다.

## RAG Setup

RAG workflow를 실행하려면 Milvus, MinIO, etcd가 필요합니다.

```powershell
docker compose --profile rag up -d etcd minio milvus
```

Chunking, embedding, Milvus loading, retrieval evaluation 관련 스크립트는 `scripts/rag/`에서 확인할 수 있습니다.

Milvus collection이 비어 있으면 evidence retrieval과 grounded report generation이 정상적으로 동작하지 않을 수 있습니다.

## API Overview

| Group | Purpose |
|---|---|
| Events | 안전 이벤트 수집 및 정규화 |
| Tickets | Workflow 실행 및 ticket 상태 조회 |
| Inventory | 내부 재고 영향 확인 |
| Evidence | Evidence snapshot 및 retrieval trace 조회 |
| Reports | 생성된 보고서와 version history 조회 |
| Review | 약사 검토, 승인, 반려 및 수정 |
| Chat | 티켓 범위의 evidence-grounded chat |
| Audit | Workflow 및 review history 조회 |

Detailed request and response schemas are available through the FastAPI Swagger UI in the running environment.

## Testing

```powershell
cd backend
pytest
```

The test suite covers workflow orchestration, RAG retrieval, evidence sufficiency, report generation, review, chat, safety checks, and audit logging.
