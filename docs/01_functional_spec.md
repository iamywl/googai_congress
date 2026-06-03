# 기능명세서 — MetricLens AI

## 1. 상위/하위 기능 트리 구조

- [x] **호스트 인벤토리 관리**
    - [x] 호스트 등록 (hostname, environment, vCPU, memory)
    - [x] 호스트 목록/단건 조회
    - [x] 중복 hostname 거부, 사이징 경계 검증
- [x] **메트릭 수집 (시계열 적재)**
    - [x] 배치 적재 (CPU·Memory·Network I/O, 타임스탬프)
    - [x] 시간 범위 조회 (start/end)
    - [x] 멱등 적재 (`UNIQUE(host_id, ts)`)
- [x] **부하 예측 (경량 시계열)**
    - [x] STL식 계절-추세 분해 + Holt-Winters 가산 외삽
    - [x] 메트릭별 예측 (CPU/MEM/NET_IN/NET_OUT)
    - [x] 95% 신뢰구간 + 백테스트 MAPE 산출
- [x] **리사이징 최적화 (정수 계획)**
    - [x] p95 피크 기반 헤드룸 제약 충족 최소 자원 산출
    - [x] vCPU 정수 / 메모리 256MB 블록 단위
    - [x] 비용 절감률·SLO 신뢰수준 제시
- [x] **웹 대시보드**
    - [x] 멀티시리즈 시계열 시각화 (ECharts)
    - [x] 예측 밴드 + MAPE 패널
    - [x] 리사이징 권장 카드, 호스트 전환 탭

## 2. 요구사항 추적 매트릭스 (RTM)

| ID | 요구사항 | 구현 위치 | 검증 (테스트) |
|---|---|---|---|
| FR-01 | 호스트 등록/조회 | `api/routes_hosts.py`, `services.HostService` | `test_api::test_create_and_fetch_host` |
| FR-02 | 중복 hostname 거부 | `HostService.create_host` | `test_api::test_duplicate_hostname_conflicts` |
| FR-03 | 사이징 경계 검증 | `schemas.HostCreate` | `test_api::test_host_validation_boundary` |
| FR-04 | 메트릭 배치 적재 | `MetricService.ingest` | `test_api::test_metric_ingest_and_query` |
| FR-05 | 시계열 범위 조회 | `MetricRepository.list_by_host` | `test_api::test_metric_ingest_and_query` |
| FR-06 | 경량 예측 + MAPE | `core/forecaster.py` | `test_forecaster::*` (8) |
| FR-07 | 신뢰구간 산출 | `forecaster.forecast` | `test_forecaster::test_prediction_interval_brackets_point_estimate` |
| FR-08 | 정수 계획 리사이징 | `core/optimizer.py` | `test_optimizer::*` (9) |
| FR-09 | 피크 기반 안전 사이징 | `optimizer.peak` | `test_optimizer::test_peak_percentile_ignores_single_spike` |
| FR-10 | 예측/권장 API | `api/routes_analysis.py` | `test_api::test_forecast_endpoint`, `test_recommendation_proposes_downsize` |
| NFR-01 | MAPE ≤ 15% | `forecaster` 백테스트 | 시드/데모 11.3% |
| NFR-02 | non-root 컨테이너 | `*/Dockerfile` | uid 10001 / nginx-unprivileged |
| NFR-03 | 멱등 시드/DDL | `scripts/schema.sql`, `generate_test_data.sh` | 2회 실행 바이트 동일 |

## 3. 사용자 스토리

- **US-1**: 인프라 관리자로서, 호스트의 48시간 CPU·메모리·네트워크 추이를 한
  화면에서 보고 과/저프로비저닝 여부를 판단하고 싶다.
- **US-2**: 관리자로서, "A 서버 vCPU를 50% 축소해도 99.9% SLO 유지 가능"과 같은
  정량 근거를 받아 자원 재배치를 결정하고 싶다.
- **US-3**: 운영자로서, 단발 스파이크 때문에 과도하게 자원을 잡지 않도록 p95
  기반의 안정적 권장을 받고 싶다.

## 4. 에지 케이스별 상태 전이 매트릭스

### 4.1 예측 요청 상태 전이

| 현재 상태 | 입력/조건 | 다음 상태 | 응답 |
|---|---|---|---|
| Idle | 호스트 없음 | Error | 404 |
| Idle | 표본 < 2 | Error | 422 |
| Idle | 표본 ≥ 2 | Forecasting | — |
| Forecasting | 분해·외삽 완료 | Persisted | 200 (ForecastOut) |

### 4.2 리사이징 권장 상태 전이

| 현재 상태 | 입력/조건 | 다음 상태 | 응답 |
|---|---|---|---|
| Idle | 호스트 없음 | Error | 404 |
| Idle | 메트릭 없음 | Error | 422 |
| Idle | 피크 < 목표 가동률 | Downsize 권장 | 200 (절감 > 0) |
| Idle | 피크 ≥ 용량 | Hold (유지) | 200 (절감 = 0) |
