# PILLIOO Backend

AI-powered pharmaceutical recall workflow engine built with FastAPI.

FDA 의약품 리콜 데이터를 기반으로 AI가 리콜을 분석하고 보고서를 생성하며 약사 검토 Workflow를 지원하는 백엔드 시스템입니다.

---

# Overview | 프로젝트 소개

## English

PILLIOO Backend is an AI-driven pharmaceutical recall workflow platform designed to automate recall analysis and report generation.

The system retrieves pharmaceutical evidence through Retrieval-Augmented Generation (RAG), generates structured reports using LLMs, and supports pharmacist review before final approval.

The backend emphasizes explainability, auditability, and safe AI-assisted pharmaceutical workflows.

---

## 한국어

PILLIOO Backend는 AI 기반 의약품 리콜 분석 및 보고서 생성 시스템입니다.

FDA 리콜 데이터를 기반으로 관련 근거 문서를 검색(RAG)하고, LLM을 활용하여 구조화된 보고서를 생성하며, 약사의 검토를 거쳐 최종 보고서를 관리합니다.

설명 가능성과 감사 가능성을 고려한 안전한 AI Workflow를 목표로 개발되었습니다.

---

# Features | 주요 기능

- Event normalization
- Inventory matching
- Evidence retrieval (RAG)
- AI report generation
- Safety validation
- Pharmacist review workflow
- Report version management
- Audit logging

---

# Tech Stack

## Backend

- FastAPI
- Python
- SQLAlchemy
- Alembic

## Database

- PostgreSQL
- Milvus

## AI

- OpenAI GPT
- Retrieval-Augmented Generation (RAG)

## Infrastructure

- Docker
- Docker Compose
- AWS EC2

---

# Architecture

```text
FDA Recall Data
        │
        ▼
 Event Normalization
        │
        ▼
 Inventory Matching
        │
        ▼
 Evidence Retrieval
        │
        ▼
 AI Draft Generation
        │
        ▼
 Safety Validation
        │
        ▼
 Pharmacist Review
        │
        ▼
 Final Report
```

---

# Project Structure

```text
app/
├── audit/
├── dashboard/
├── db/
├── orchestration/
├── rag/
├── report/
├── review/
├── workflow/
├── schemas/
└── main.py
```

---

# Getting Started

Install dependencies

```bash
pip install -r requirements.txt
```

Run services

```bash
docker compose up -d
```

Run server

```bash
uvicorn app.main:app --reload
```

---

# Deployment

Backend is deployed on AWS EC2.

Core infrastructure includes:

- FastAPI
- PostgreSQL
- Milvus
- Docker Compose

---

# Team

| Name | Role |
|------|------|
| Jihee Bang | Backend · Infrastructure |
| Jimin Kim | Frontend |
| Yoon Kong | AI · Backend |

---

# License

This project was developed for academic and hackathon purposes.
