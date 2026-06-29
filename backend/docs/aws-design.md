# PharmaOps AWS 인프라 설계 문서

담당: 윤아 (P5)

---

## 1. IAM 설계

### Role 목록

| Role 이름 | 용도 | 주요 권한 |
|---|---|---|
| `pharmaops-ec2-role` | EC2 인스턴스용 | S3 읽기/쓰기, CloudWatch 로그 쓰기 |
| `pharmaops-deploy-role` | 배포 자동화용 | EC2 재시작, S3 업로드 |
| `pharmaops-readonly-role` | 모니터링/조회용 | CloudWatch 읽기, S3 읽기 |

### IAM User

| User 이름 | 용도 |
|---|---|
| `pharmaops-admin` | 전체 인프라 관리 |
| `pharmaops-deploy` | 배포 전용 (CI/CD) |

### 권한 정책

```
EC2 인스턴스 → S3 접근: s3:GetObject, s3:PutObject
EC2 인스턴스 → CloudWatch: logs:CreateLogGroup, logs:PutLogEvents
배포 User → EC2: ec2:RebootInstances, ec2:DescribeInstances
```

---

## 2. S3 버킷 설계

### 버킷 목록

| 버킷 이름 | 용도 |
|---|---|
| `pharmaops-rag-documents` | RAG 문서 원본 저장 (DailyMed, SOP, Policy) |
| `pharmaops-reports` | 승인된 보고서 최종본 저장 |
| `pharmaops-logs` | 애플리케이션 로그 백업 |

### 버킷 정책

```
pharmaops-rag-documents
  → EC2 인스턴스만 읽기 가능
  → 외부 접근 차단 (Block Public Access ON)

pharmaops-reports
  → EC2 인스턴스 읽기/쓰기
  → 외부 접근 차단

pharmaops-logs
  → CloudWatch → S3 자동 export
  → 보존 기간: 90일
```

### 폴더 구조 (pharmaops-rag-documents)

```
pharmaops-rag-documents/
├── dailymed/        ← DailyMed 라벨 원문
├── sop/             ← recall/shortage SOP
├── policy/          ← 병원 내부 정책 문서
└── recall_notice/   ← recall notice 문서
```

---

## 3. EC2 Security Group 설계

### Security Group: `pharmaops-sg`

#### Inbound 규칙

| 포트 | 프로토콜 | 허용 대상 | 용도 |
|---|---|---|---|
| 22 | TCP | 개발자 IP만 | SSH 접속 |
| 8000 | TCP | 0.0.0.0/0 | FastAPI (외부 접근) |
| 5432 | TCP | EC2 내부만 | PostgreSQL |
| 19530 | TCP | EC2 내부만 | Milvus |

#### Outbound 규칙

| 포트 | 프로토콜 | 허용 대상 | 용도 |
|---|---|---|---|
| 443 | TCP | 0.0.0.0/0 | HTTPS (외부 API 호출) |
| 80 | TCP | 0.0.0.0/0 | HTTP |

### 네트워크 정책 원칙
- PostgreSQL, Milvus는 외부에서 직접 접근 불가
- FastAPI만 외부에 노출
- SSH는 개발자 IP 화이트리스트만 허용

---

## 4. CloudWatch 설계

### 수집 로그 목록

| 로그 그룹 | 수집 대상 | 보존 기간 |
|---|---|---|
| `/pharmaops/fastapi` | FastAPI 애플리케이션 로그 | 30일 |
| `/pharmaops/workflow` | Workflow 실행 로그 | 30일 |
| `/pharmaops/audit` | Audit log (티켓 처리 기록) | 90일 |
| `/pharmaops/error` | 에러 로그만 별도 수집 | 90일 |

### 알람 기준

| 알람 이름 | 조건 | 액션 |
|---|---|---|
| `high-error-rate` | 5분간 에러 로그 10건 이상 | 이메일 알림 |
| `api-latency-high` | API 응답시간 3초 초과 | 이메일 알림 |
| `workflow-failure` | workflow 실패율 20% 초과 | 이메일 알림 |

### 대시보드 구성

```
CloudWatch Dashboard: pharmaops-dashboard
├── API 응답시간 (평균/최대)
├── 에러 발생 건수 (시간별)
├── Workflow 처리 건수
└── EC2 CPU/메모리 사용률
```

---

## 5. 장애 대응 기준

### 장애 등급

| 등급 | 기준 | 대응 시간 |
|---|---|---|
| P1 (Critical) | API 전체 다운 | 즉시 |
| P2 (High) | 특정 기능 장애 | 1시간 이내 |
| P3 (Medium) | 성능 저하 | 24시간 이내 |

### 1차 대응 순서

```
1. CloudWatch 알람 확인
2. /pharmaops/error 로그 조회
3. EC2 인스턴스 상태 확인
4. docker-compose logs -f fastapi 확인
5. 재현 시나리오 작성 후 팀 공유
```

---

## 6. 비용 최적화 계획

| 항목 | 선택 | 이유 |
|---|---|---|
| EC2 인스턴스 타입 | t3.medium | Milvus 메모리 요구사항 (최소 4GB) |
| S3 스토리지 클래스 | Standard → 30일 후 IA | 오래된 로그 비용 절감 |
| CloudWatch 로그 보존 | 30~90일 | 불필요한 장기 보존 방지 |

---

## 7. 구현 일정

| 주차 | 작업 |
|---|---|
| 3주차 | AWS 계정 세팅, IAM/S3/EC2 생성, EC2 배포 시도 |
| 4주차 | CloudWatch 연결, 장애 모니터링 안정화 |
