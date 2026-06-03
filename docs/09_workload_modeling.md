# 워크로드 모델링 및 시험 데이터의 통계적 대표성 — MetricLens AI

본 문서는 MetricLens의 데모/시드 데이터와 시험 시나리오가 임의로 작성된 것이
아니라, **공개된 대규모 데이터센터 트레이스의 실측 통계에 근거(calibration)** 하여
구성되었음을 기술한다. 목적은 시험 데이터가 실제 서버 플릿을 **통계적으로
대표(representative)** 하도록 보장하는 것이다.

생성 코드: [`backend/app/core/workload.py`](../backend/app/core/workload.py),
검증 시험: [`backend/tests/test_workload.py`](../backend/tests/test_workload.py).

---

## 1. 근거 자료 (실측 데이터센터 통계)

| 출처 | 핵심 실측치 | 본 프로젝트 반영 |
|---|---|---|
| **Microsoft Azure VM 트레이스** — *Resource Central* (Cortez et al., SOSP 2017). 2,013,767 VM · 12.5억 CPU 측정치 · 30일 | VM의 **60%가 평균 CPU < 20%**, **40%가 95퍼센타일 CPU < 50%**. VM은 *대화형(interactive, 일주기성)* 과 *지연무관(delay-insensitive, 배치·개발/테스트)* 으로 분류. 주기성은 **3일 이상** 구동 시 탐지 가능(>3일 VM이 코어-시간의 94% 차지). 대화형은 야간보다 주간 CPU가 높음 | 저활용(과프로비저닝) 호스트를 다수 배치, 대화형/지연무관 두 클래스를 모두 모델링, 시드 길이를 **14일**(≥3일)로 설정 |
| **Barroso & Hölzle**, *The Datacenter as a Computer* (Google) | 서버는 대부분의 시간을 **10–50% 활용 구간**에서 보내며 포화(saturated)되는 일은 드묾 | 모든 대화형 아키타입의 평균·피크를 10–50% 대역에 정렬 |
| **Alibaba 2018 클러스터 트레이스** | 배치 전용 서버 평균 **29.3% CPU**, 서비스 전용 서버 평균 **7.4% CPU**. 클러스터는 시간의 80% 이상을 **10–30% CPU**에서 운용 | 배치 아키타입 평균≈30%(버스트), 과프로비저닝 서비스 아키타입 평균≈10% |

세 출처가 공통적으로 가리키는 사실: **실제 서버는 만성적으로 저활용**이며,
워크로드는 *대화형(일주기)* · *배치(버스트)* · *정상상태(steady)* 로 나뉜다.
MetricLens의 시드는 이 세 축을 모두 재현한다.

---

## 2. 워크로드 아키타입 (6종)

3개였던 데모 호스트를 **6개**로 확장하여, 위 문헌의 워크로드 클래스·환경·자원
바운드(CPU vs 메모리)·프로비저닝 상태를 고르게 포괄한다. 표본 크기는 호스트당
**14일 × 시간단위 = 336 표본**(총 2,016 표본)으로, 3일 주기성 임계치를 크게
상회하고 확장 윈도우 백테스트에 충분한 통계력을 제공한다.

| 호스트 | 환경 | 사양 | 클래스 | 평균 CPU | p95 | 근거 |
|---|---|---|---|---|---|---|
| `web-prod-01` | PROD | 16 vCPU / 32 GB | 대화형(과프로비저닝) | ~16% | ~29% | Azure 저활용 60%, Barroso 10–50% |
| `api-prod-04` | PROD | 8 vCPU / 16 GB | 대화형(중부하) | ~28% | ~51% | Barroso 10–50% |
| `cache-prod-05` | PROD | 8 vCPU / 64 GB | 정상상태(메모리 바운드) | ~12% | ~16% | 캐시/DB: 낮은 CPU·높은 메모리 |
| `batch-etl-01` | STAGING | 16 vCPU / 32 GB | 배치(버스트) | ~31% | ~90% | Alibaba 배치 29.3% |
| `api-staging-02` | STAGING | 8 vCPU / 16 GB | 서비스(과프로비저닝) | ~10% | ~18% | Alibaba 서비스 7.4% |
| `batch-dev-03` | DEV | 4 vCPU / 8 GB | 지연무관(산발적) | ~11% | ~20% | Azure 개발/테스트 |

### 생성 모델
- **일주기 형상**: 야간 저점 → 오전 상승 → 오후 피크 → 저녁 하강의 정규화 24시간
  곡선(대화형/정상상태 공유). Azure의 "네트워크 바운드 대화형" 일주기 곡선에 해당.
- **주간 효과**: 대화형은 주말 계수(0.6–0.9)로 완만히 감쇠.
- **배치**: 낮은 기저 + 고정 크론 시간대(예: 01–04시, 13–15시)의 스파이크(~90%).
- **결정론적 잡음**: `md5(seed, index)` 기반 의사난수로 ±진폭 한정. → **완전 결정론·멱등**.

---

## 3. 검증 결과 (대표성 자동 시험)

[`test_workload.py`](../backend/tests/test_workload.py)가 생성 데이터가 위
실측 특성을 재현하는지 단언한다.

| 시험 | 단언 | 결과 |
|---|---|---|
| 결정론성 | 동일 시드 → 동일 시계열 | ✅ |
| 일주기성 | 대화형: 주간 평균 > 야간 평균 ×1.5 | ✅ |
| 버스트성 | 배치: p95 > 평균 ×2, 표준편차 > 15 | ✅ |
| 정상상태 | 캐시: CPU σ < 5, 메모리 평균 > 60% | ✅ |
| 저활용 | 서비스·개발: 평균 CPU < 15% | ✅ |
| 예측가능성 | 대화형: 백테스트 MAPE ≤ 15% | ✅ |
| 물리 경계 | 모든 값 [1, 100] | ✅ |

### 플릿 분석 결과 (대표성 + 신뢰성)
- 과프로비저닝 호스트는 정확히 다운사이징됨: `web-prod-01` 16→9 vCPU(절감 36%),
  `api-staging-02` 8→3 vCPU(54%), `batch-dev-03` 4→2 vCPU(52%).
- **중부하 호스트(`api-prod-04`)는 5%만 조정**, **버스트 호스트(`batch-etl-01`)는
  0% 유지** — p95 안전 통계가 스파이크성 워크로드의 과소축소를 올바르게 차단함을
  실증(신뢰성).
- **메모리 바운드 호스트(`cache-prod-05`)는 CPU만 8→3으로 줄이고 메모리는 유지** —
  자원별 독립 최적화를 실증.

### 정직한 한계 (white-box)
- `batch-dev-03`(준유휴) MAPE는 ~33%로 목표를 초과한다. 이는 **저활용 구간에서
  MAPE 분모가 작아 백분율 오차가 본질적으로 부풀려지는** 잘 알려진 현상이며(예측기가
  분모 바닥값을 두는 이유), 본 시스템은 이를 숨기지 않고 그대로 보고한다. 예측은
  일주기 대화형 워크로드를 표적으로 하며, 지연무관·버스트 워크로드의 높은 오차는
  실제와 부합하는 결과다.

---

## 4. 출처

- M. Cortez et al., "Resource Central: Understanding and Predicting Workloads
  for Improved Resource Management in Large Cloud Platforms," **SOSP 2017** —
  https://www.microsoft.com/en-us/research/wp-content/uploads/2017/10/Resource-Central-SOSP17.pdf
- Microsoft Azure Public Dataset (VM traces) —
  https://github.com/Azure/AzurePublicDataset
- L. A. Barroso, U. Hölzle, P. Ranganathan, "The Datacenter as a Computer:
  Designing Warehouse-Scale Machines" —
  https://www.cs.cmu.edu/~15721-f24/papers/Data_Center_As_a_Computer.pdf
- Alibaba Cluster Trace Program (2018) —
  https://github.com/alibaba/clusterdata ; 분석:
  "Characterizing Co-located Datacenter Workloads: An Alibaba Case Study,"
  https://arxiv.org/pdf/1808.02919
