# 한계점 및 향후 과제 — MetricLens AI

본 문서는 MetricLens 현 구현(2026-06-03 기준)의 한계를 코드 근거와 함께 정직하게
기술한다. 심사·감사 시 과장 없는 자기평가 자료로 사용한다. 각 항목은 **현상 →
원인(코드 위치) → 영향 → 보완 방향** 순으로 정리한다.

관련 코드: [`forecaster.py`](../backend/app/core/forecaster.py),
[`optimizer.py`](../backend/app/core/optimizer.py),
[`evaluation.py`](../backend/app/core/evaluation.py),
[`workload.py`](../backend/app/core/workload.py),
[`integrations/gcp.py`](../backend/app/integrations/gcp.py).

---

## 1. 예측 모델

### 1.1 선형 추세 외삽
- **현상**: 추세를 OLS 직선 한 개로 적합한다(`_linear_trend`,
  [`forecaster.py`](../backend/app/core/forecaster.py)).
- **영향**: 미래로 갈수록 직선이 무한 발산하여 장기 예측이 비현실적이다. 비선형
  성장·포화(saturation) 구간을 표현하지 못한다.
- **보완**: 감쇠 추세(damped trend) 또는 구간별 추세, 로그/로지스틱 변환 도입.

### 1.2 1-스텝(horizon=1)만 검증됨
- **현상**: `_predict`는 다중 스텝에 `rho**horizon` 감쇠를 적용하지만, 평가
  ([`evaluation.py`](../backend/app/core/evaluation.py))·`docs/11`의 백테스트는
  전부 `horizon=1`이다.
- **영향**: 리사이징은 본질적으로 미래 다중 시점을 봐야 하는데, **h>1 예측의
  정확도 근거가 없다**.
- **보완**: 다중 스텝 백테스트(h=6/12/24h) 추가, 호라이즌별 오차·구간 보정 보고.

### 1.3 단일 주기 가정
- **현상**: 모델은 주기 하나(예: 24h)만 받는다. 데이터에는 주중/주말
  (`weekend_factor`, [`workload.py`](../backend/app/core/workload.py)) 패턴이 있으나
  24h 단일 주기 모델은 이를 잡지 못한다.
- **영향**: 주간(weekly) 계절성이 잔차로 흘러가 정확도·구간 보정을 저하시킨다.
- **보완**: 다중 계절성(일+주) 분해 또는 푸리에 항 결합.

### 1.4 예측구간의 정규·등분산 가정
- **현상**: 95% 구간 반폭을 `1.96 × RMSE`로 고정한다
  ([`forecaster.py`](../backend/app/core/forecaster.py)).
- **영향**: 실제 부하는 비대칭·두꺼운 꼬리·이분산이며, AR(1) 잔차상관이 구간
  산정에 반영되지 않는다. 이상치 스파이크가 RMSE를 부풀려 구간이 과대해진다.
- **보완**: 분위수 기반 구간, 컨포멀 예측(conformal prediction), 이분산 모델.

### 1.5 MAPE 바닥값 보정
- **현상**: `max(abs, 0.01×scale)` 바닥으로 준유휴 호스트의 백분율 오차를
  눌러쓴다.
- **영향**: 정직한 보고지만, 저활용 자원에서는 정확도가 사실상 측정 불가다.

---

## 2. 최적화기

### 2.1 "정수계획법 / fleet" 명칭과 구현의 괴리
- **현상**: [`optimizer.py`](../backend/app/core/optimizer.py)는 호스트별로 독립
  수행되는 1차원 완전탐색(`vCPU 1..current` 순회)이다.
- **영향**: README/문서의 "정수계획법", "fleet 최적화" 표현과 달리 **다중 호스트
  빈패킹·통합(consolidation)·co-location·마이그레이션이 없다**. 진정한 fleet-level
  정수계획이 아니다.
- **보완**: 명칭을 "호스트별 제약 만족 탐색"으로 정정하거나, 실제 fleet 빈패킹
  (다중 호스트 통합) 정수계획을 구현.

### 2.2 축소만 가능, 확장 불가
- **현상**: `_smallest_unit_allocation`의 탐색 범위가 `range(1, current+1)`이라
  현재보다 키우는 추천이 구조적으로 불가능하다. 부하가 용량을 초과하면 `current`로
  폴백한다.
- **영향**: 성장·과소프로비저닝 시나리오에서 SLO를 지킬 수 없다(축소 전용 최적화).
- **보완**: 탐색 상한을 확장(머신타입 카탈로그 범위)하여 scale-up 추천 허용.

### 2.3 "SLO 보장"의 정량적 연결고리 약함
- **현상**: `target_utilisation=0.65`, `safety_margin=1.2`는 고정 상수이고,
  `slo_confidence=99.9`는 입력 라벨로 통과될 뿐 예측구간에서 **계산되지 않는다**.
- **영향**: 화이트박스 차별점에 비해 SLO 신뢰도와 마진의 수학적 연결이 약하다.
- **보완**: 마진을 예측구간 상한(p95 + PI)에서 유도, SLO 위반확률을 명시 계산.

### 2.4 비용·운영 현실 미반영
- **현상**: `est_cost_saving_pct`는 vCPU/메모리 감소율의 단순 평균이지 실제 단가
  ($, [`machine_types.py`](../backend/app/core/machine_types.py))가 아니다. vCPU와
  메모리를 독립 최적화하나 GCP 머신타입은 비율 고정 이산 카탈로그다.
- **영향**: 실제 절감액과 어긋날 수 있고, 추천 조합이 실재 머신타입과 불일치할 수
  있다. 리사이즈 다운타임·쿨다운·플래핑(oscillation) 미고려.
- **보완**: 실제 단가 기반 목적함수, 머신타입 이산 제약 결합, 플래핑 억제(히스테
  리시스) 추가.

---

## 3. 데이터·평가의 순환성

### 3.1 자기 생성 데이터로 자기 모델 평가
- **현상**: 평가는 [`workload.py`](../backend/app/core/workload.py)가 만든 합성
  데이터에서만 수행된다. 생성기는 `_AR_RHO=0.55`의 AR(1)를 주입하고, 모델은 AR(1)
  잔차 보정을 더한다.
- **영향**: 모델이 유리하도록 데이터 생성 과정에 정렬된 **순환 구조**다. `docs/11`의
  우수 지표(MASE<1, DM p<0.05)는 이 자기참조 위에 있어 외적 타당성이 제한된다.
- **보완**: Azure/Alibaba 등 **실제 트레이스 1개 이상으로 홀드아웃 재평가**.

### 3.2 기준선 우위가 항상은 아님
- **현상**: `steady_cache`·`devtest`는 직전값 기준선을 유의하게 못 이긴다(문서가
  정직히 보고).
- **영향**: 평탄·준유휴 신호에서는 모델의 추가 가치가 제한적이다.

---

## 4. 실제 GCP 통합 (데모 수준)

- **부하의 대표성**: 실제 호스트 4대는 e2-small 부하 생성기이지 프로덕션
  워크로드가 아니다. e2 공유코어는 100%로 포화돼 부하 생성을 인위적으로 억제한다.
- **메모리 미측정 프록시**: Ops Agent 없이 CPU 연동 추정값으로 저장한다. 메모리
  최적화 입력의 신뢰도가 낮다.
- **수집 해상도**: Cloud Monitoring 시간 정렬로 시간당 1포인트, 전체 일주기 확보에
  ~24h, period=24 백테스트엔 2일 이상 필요 → 콜드스타트 공백.
- **리사이즈 다운타임**: `stop → setMachineType → start`
  ([`integrations/gcp.py`](../backend/app/integrations/gcp.py))로 다운타임이
  발생한다. 라이브 리사이즈가 아니라 SLO 무중단 보장과 상충한다.

---

## 5. 시스템·보안·운영

### 5.1 감사 추적 주장과 영속성 모순
- **현상**: DB가 `sqlite+aiosqlite:////tmp/metriclens.db`
  ([`config.py`](../backend/app/config.py))이고 Cloud Run은 scale-to-zero다. `/tmp`는
  인스턴스 휘발성이라 콜드스타트마다 기록이 소실·재시드된다.
- **영향**: "모든 예측·리사이즈를 영속 기록(감사 추적)"이라는 차별점과 충돌한다.
- **보완**: Cloud SQL 또는 GCS/외부 영속 스토리지로 전환.

### 5.2 인증 부재 + 공개 쓰기 엔드포인트
- **현상**: `allow_origins=["*"]`·인증 없음([`main.py`](../backend/app/main.py)).
  주석은 "read-only demo"라지만 `POST .../resize`는 실제 GCP VM을 stop/start하는
  쓰기 작업이다.
- **영향**: 예산 한도+denylist만 막을 뿐 authn/authz가 없어, 공개 API로 누구나
  실인프라 리사이즈를 트리거할 수 있다.
- **보완**: API 키/OIDC 인증, 쓰기 엔드포인트 분리·권한 통제, CORS 출처 제한.

### 5.3 단일 인스턴스·SQLite
- **현상**: Cloud SQL 미사용으로 HA·동시성·다중 인스턴스 일관성이 없다. 매 예측이
  전체 시리즈를 재적합하나(O(n)) N이 작아 당장은 무해하다.
- **보완**: 관리형 DB + 증분 적합/캐싱.

### 5.4 CI/CD 미완성
- **현상**: git-push 자동배포 연결(`metriclens-gh`)이 `PENDING_USER_OAUTH`로 멈춰
  있어 배포는 수동 `gcloud builds submit`에 의존한다.
- **보완**: OAuth 완료 + 저장소 링크/트리거 생성.

---

## 6. 우선순위 보완 로드맵

임팩트 순:

1. **실제 트레이스로 모델 재평가** — §3.1 순환성 해소(논문 설득력 직결).
2. **다중 스텝 예측 검증 + 확장(scale-up) 추천 허용** — §1.2, §2.2.
3. **영속 DB로 감사 추적 실현 + 리사이즈 엔드포인트 인증** — §5.1, §5.2.
4. **"정수계획법/fleet" 명칭 정정 또는 실제 fleet 빈패킹 구현** — §2.1.
5. **SLO 마진을 예측구간에서 유도** — §2.3.

---

## 7. 출처

- 데이터 근거: [09_workload_modeling.md](09_workload_modeling.md)
  (Azure SOSP'17, Alibaba 2018, Barroso & Hölzle).
- 평가 방법론: [11_model_evaluation.md](11_model_evaluation.md).
