# API 명세서 — MetricLens AI

기준: OpenAPI 3.1 스타일. 모든 엔드포인트는 백엔드 Cloud Run 서비스
(`metriclens-backend`) 루트 기준이며, 대화형 문서는 런타임에 `/docs`(Swagger UI)로
제공된다. 모든 본문은 `application/json`이다.

## 0. 공통 에러 카탈로그

| 상태 코드 | 의미 | 발생 조건 |
|---|---|---|
| `400 Bad Request` | 잘못된 요청 | 파싱 불가 본문 |
| `404 Not Found` | 리소스 없음 | 존재하지 않는 `host_id` |
| `409 Conflict` | 중복 | 이미 존재하는 `hostname`으로 호스트 생성 |
| `422 Unprocessable Entity` | 검증 실패 | 스키마 경계 위반, 예측/권장에 필요한 데이터 부족 |
| `500 Internal Server Error` | 서버 오류 | 예기치 못한 예외 |

표준 에러 응답 형식(FastAPI):
```json
{ "detail": "Host not found." }
```

---

## 1. 메타 / 헬스

### 1.1 `GET /health` — 라이브니스 (DB 미접근)
- **응답 200**: `{ "status": "ok" }`

### 1.2 `GET /health/db` — 레디니스 (DB 접근)
- **응답 200**: `{ "status": "ok", "database": "reachable" }`

---

## 2. 호스트 인벤토리 API

### 2.1 `POST /api/v1/hosts` — 호스트 등록
- **요청 페이로드**:
```json
{
  "hostname": "web-prod-01",
  "environment": "PROD",
  "vcpu_count": 16,
  "memory_mb": 32768
}
```
- **JSON Schema(요청)**:
  - `hostname`: string, 1–255자, 필수, 유일
  - `environment`: enum `PROD|STAGING|DEV`, 기본 `PROD`
  - `vcpu_count`: integer, 1–256
  - `memory_mb`: integer, 256–4194304
- **응답 201 Created**:
```json
{
  "id": "f1e2...-uuid",
  "hostname": "web-prod-01",
  "environment": "PROD",
  "vcpu_count": 16,
  "memory_mb": 32768,
  "created_at": "2024-01-01T00:00:00Z"
}
```
- **에러**: `409` 중복 hostname, `422` 경계 위반.

### 2.2 `GET /api/v1/hosts` — 호스트 목록
- **응답 200**: `HostOut[]` (hostname 오름차순).

### 2.3 `GET /api/v1/hosts/{host_id}` — 단건 조회
- **응답 200**: `HostOut` · **에러**: `404`.

---

## 3. 메트릭 API

### 3.1 `POST /api/v1/hosts/{host_id}/metrics` — 시계열 적재 (배치)
- **요청 페이로드** (`MetricIn[]`):
```json
[
  {
    "ts": "2024-01-01T00:00:00Z",
    "cpu_pct": 42.5,
    "mem_pct": 50.0,
    "net_in_kbps": 5100.0,
    "net_out_kbps": 3430.0
  }
]
```
- **JSON Schema(요소)**: `cpu_pct`/`mem_pct` 0–100, `net_*_kbps` ≥ 0, `ts` ISO-8601.
- **응답 202 Accepted**:
```json
{ "host_id": "f1e2...", "ingested": 48 }
```
- **에러**: `404` 미존재 호스트, `422` 범위 위반.

### 3.2 `GET /api/v1/hosts/{host_id}/metrics` — 시계열 조회
- **쿼리**: `start`, `end` (ISO-8601, 선택, 포함 경계)
- **응답 200**: `MetricOut[]` (`ts` 오름차순) · **에러**: `404`.

---

## 4. 분석 API

### 4.1 `POST /api/v1/hosts/{host_id}/forecast` — 부하 예측
- **쿼리**: `metric` = `CPU|MEM|NET_IN|NET_OUT` (기본 `CPU`),
  `horizon_minutes` integer 1–10080 (기본 60).
- **응답 200 (`ForecastOut`)**:
```json
{
  "id": "uuid",
  "host_id": "f1e2...",
  "metric": "CPU",
  "generated_at": "2024-01-03T00:00:00Z",
  "horizon_minutes": 60,
  "model": "STL_HOLTWINTERS",
  "predicted_value": 16.0,
  "lower_bound": 9.4,
  "upper_bound": 22.6,
  "mape": 11.3
}
```
- **에러**: `404` 미존재 호스트, `422` 표본 2개 미만.

### 4.2 `POST /api/v1/hosts/{host_id}/recommendation` — 리사이징 권장
- **응답 200 (`RecommendationOut`)**:
```json
{
  "id": "uuid",
  "host_id": "f1e2...",
  "generated_at": "2024-01-03T00:00:00Z",
  "current_vcpu": 16,
  "recommended_vcpu": 8,
  "current_memory_mb": 32768,
  "recommended_memory_mb": 16384,
  "est_cost_saving_pct": 50.0,
  "slo_confidence": 99.9
}
```
- **의미**: 예측 피크(p95) 기반 정수 계획으로, 목표 가동률·안전 마진 제약 하
  최소 자원을 산출한다. `slo_confidence`는 권장 적용 시 보장 가용성이다.
- **에러**: `404` 미존재 호스트, `422` 메트릭 없음.
