# 테스트 계획서 및 케이스 정의서 — MetricLens AI

테스트는 경계값 분석(BVA)과 동등 분할(EP)에 기반한다. 순수 Core 로직은 DB 없이
단위 테스트하고, API는 인메모리 리포지토리로 Controller→Service→Core 전 경로를
구동하는 통합 테스트로 검증한다. 실행: `cd backend && pytest -q` (총 27건).

## 1. 단위 테스트 — 예측기 (`tests/test_forecaster.py`, 8건)

대상: `core/forecaster.py` (STL식 분해 + 외삽 + 백테스트 MAPE).

| 케이스 | 분류 | 입력 | 기대 |
|---|---|---|---|
| 빈 시계열 거부 | 경계 | `[]` | `ValueError` |
| 0 지평 거부 | 경계 | `horizon=0` | `ValueError` |
| 단일 표본 | 경계 | `[42.0]` | 예측=42, 밴드폭 0, MAPE None |
| 상수 시계열 | 동등분할 | `[50]*48` | 예측≈50, MAPE≈0 |
| 순수 추세 외삽 | 동등분할 | `1..24` | 예측≈25 |
| 계절 패턴 복원 | 동등분할 | 주기 4 파형×4 | 위상0 레벨≈10 |
| 신뢰구간 포함 | 불변식 | 변동 시계열 | `lower ≤ pred ≤ upper` |
| MAPE 비음수 | 불변식 | 주기 6 | `mape ≥ 0`, 유한 |

## 2. 단위 테스트 — 최적화기 (`tests/test_optimizer.py`, 9건)

대상: `core/optimizer.py` (정수 계획 리사이징 + p95 피크).

| 케이스 | 분류 | 입력 | 기대 |
|---|---|---|---|
| 저부하 다운사이즈 | 동등분할 | 16vCPU, 피크 20% | 권장 < 현재, 절감 > 0 |
| 포화 유지 | 경계 | 피크 100% | 권장=현재, 절감=0 |
| 헤드룸 제약 | 불변식 | 50%, margin 1.2 | `load ≤ target×rec_vcpu` |
| 최소 할당 바닥 | 경계 | 1vCPU/256MB | 권장=1/256 |
| 잘못된 vCPU | 경계 | `vcpu=0` | `ValueError` |
| 잘못된 메모리 | 경계 | `mem=128` | `ValueError` |
| 잘못된 목표가동률 | 경계 | `target=1.5` | `ValueError` |
| SLO 전달 | 동등분할 | `slo=99.9` | 그대로 반영 |
| p95 피크 | 경계 | 99×10 + 1×100 | p95=10, p100=100 |

## 3. 통합 테스트 — API (`tests/test_api.py`, 10건)

대상: `api/routes_*` 전 경로 (인메모리 리포지토리).

| 케이스 | 분류 | 검증 |
|---|---|---|
| 헬스 DB-free | 정상 | `GET /health` = `{status: ok}` |
| 호스트 생성/조회 | 정상 | 201 → 200, 필드 일치 |
| 중복 hostname | 경계 | 두 번째 생성 409 |
| 사이징 경계 | 경계 | `vcpu_count=0` → 422 |
| 미존재 호스트 | 경계 | `GET` 404 |
| 적재/조회 | 정상 | 48건 적재 후 48건 조회 |
| 미존재 호스트 적재 | 경계 | 404 |
| 예측 엔드투엔드 | 정상 | 200, `lower≤pred≤upper`, `mape≥0` |
| 데이터 없는 예측 | 경계 | 422 |
| 다운사이즈 권장 | 정상 | `rec_vcpu ≤ cur_vcpu`, SLO 99.9 |

## 4. 데이터 무결성 테스트 (시드/스키마)

- **결정론**: `generate_test_data.sh` 2회 실행 산출 SQL 바이트 동일.
- **멱등성**: 모든 INSERT가 `ON CONFLICT DO NOTHING` → 반복 적재 동일 상태.
- **경계 데이터**: CPU 0.00%/100.00%, BIGINT 최대 size, 최소 사이징 호스트,
  ENUM 전 클래스(PROD/STAGING/DEV, CPU/MEM/NET_IN/NET_OUT).

## 5. 합격 기준 (Definition of Done)

- `ruff check .` 무결, `pytest` **27/27 통과**.
- 프론트엔드 `npm run lint && npm run build` 성공.
- Cloud Build 9-스테이지 통과 + 배포 후 `/health` 200.
