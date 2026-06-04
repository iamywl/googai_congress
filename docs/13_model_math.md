# 13. 모델 수학 설명 — 연산 과정

이 문서는 MetricLens의 두 핵심 Core(`backend/app/core/forecaster.py`, `backend/app/core/optimizer.py`)가
원시 메트릭 시계열을 받아 SLO 보장 정수 할당까지 **어떤 식으로 연산하는지**를 수식으로 기술한다.
모든 식은 코드가 실제로 계산하는 식과 일치한다. 시각 자료는 다음 그림을 참조한다.

- 연산 파이프라인(수식): `docs/diagrams/method_math.png` (EN) / `method_math_kr.png` (KR)
- 생성 스크립트: `scripts/build_math_diagram.py`

표기: 시계열 `y_0 … y_{n-1}`(오래된 것 먼저), 계절 주기 `m`(시간단위 기본 24), 예측 지평 `h`(≥1).

---

## 1. 예측기 — 계절-추세 분해 + AR(1) 잔차 보정

분해 모델:

```
y_t = T_t + S_{t mod m} + r_t
```

`T_t` 추세, `S_{t mod m}` 계절 성분, `r_t` 잔차.

### 1.1 추세 (계절 누설을 제거한 OLS)

원시 표본이 아니라 **주기별 블록 평균**에 직선을 적합한다. 한 주기를 평균하면 계절 성분이 상쇄되므로
기울기로 누설되지 않는다(전체 블록 수 `B = ⌊n/m⌋ ≥ 2`일 때).

```
블록 평균:   ȳ_k = (1/m) · Σ_{i=0}^{m-1} y_{k·m+i}          (k = 0 … B-1)
블록 중심:   c_k = k·m + (m-1)/2
OLS:        β = Σ_k (c_k - c̄)(ȳ_k - ȳ) / Σ_k (c_k - c̄)^2
            α = ȳ - β·c̄
추세:        T_t = β·t + α
```

`B < 2`이면 전체 표본에 대한 일반 OLS로 대체한다.
(`forecaster._linear_trend`, `forecaster._ols`)

### 1.2 계절 지수 (0합 재중심화)

```
탈추세:      d_t = y_t - T_t
위상 평균:   raw_j = mean{ d_t : t mod m = j }              (j = 0 … m-1)
재중심화:    S_j = raw_j - (1/m) · Σ_j raw_j      ⇒  Σ_j S_j = 0
```

(`forecaster._seasonal_indices`)

### 1.3 잔차와 AR(1) 계수

```
잔차:        r_t = d_t - S_{t mod m}
시차-1 자기상관:
            ρ = Σ_{t=1}^{n-1} (r_t - r̄)(r_{t-1} - r̄) / Σ_t (r_t - r̄)^2
클램프:      ρ ∈ [0, 0.95]
```

실제 CPU 트레이스는 강하게 자기상관(측정 시차-1 0.5–0.9)되므로 분해 예측에 잔차의 최근 수준을
감쇠 반영한다. (`forecaster._ar1_coeff`)

### 1.4 점예측 (지평 h)

```
미래 인덱스: f = (n-1) + h
점예측:      ŷ_f = T_f + S_{f mod m} + ρ^h · r_{n-1}
                = β·f + α + S_{f mod m} + ρ^h · r_{n-1}
```

`ρ^h`로 지평이 멀어질수록 잔차 보정이 감쇠한다. (`forecaster._predict`)

### 1.5 95% 예측구간 (표본 외 백테스트 기반)

구간 폭은 **확장창(expanding-window) 1-스텝 백테스트** 오차로 산정한다. 즉 시점 `t`를 예측할 때
`y_0 … y_{t-1}`만 사용한다(미래 미사용).

```
시작:        start = max(m, ⌊n/2⌋, 2)
백테스트:    각 t = start … n-1 에 대해 ŷ_t^(1) = predict(y_{0:t}, h=1)
RMSE:        RMSE = sqrt( (1/N) · Σ_t (y_t - ŷ_t^(1))^2 )
95% 구간:    [ ŷ - 1.96·RMSE ,  ŷ + 1.96·RMSE ]
```

이력이 부족해 백테스트가 불가하면 잔차의 모표준편차를 RMSE 대용으로 쓴다.
정확도 지표 MAPE는 같은 백테스트에서 분모 바닥값 `f = max(1, 0.01·max|y|)`로 계산해
준유휴 표본이 백분율을 부풀리지 않게 한다. (`forecaster._backtest`, `forecaster.forecast`)

측정된 커버리지(PICP)는 6개 워크로드에서 0.93–0.98로 공칭 0.95에 잘 보정된다(보고서 §7).

---

## 2. 옵티마이저 — 유계 공간 정확 정수계획

예측 결과의 **피크**를 입력으로 받아 SLO를 지키는 최소 정수 할당을 자원별(vCPU, 메모리 블록)로 구한다.

### 2.1 강건 피크 (p95, 근접순위)

최댓값은 단발 스파이크 1점에 취약하므로 95퍼센타일을 피크로 쓴다.

```
정렬 후:     rank = ⌈(95/100) · N⌉
p95 = sorted[min(rank, N) - 1]
```

자주 반복되는 부하(예: 매일 배치 급등)는 빈도가 5%를 넘어 p95에 포함되므로 해당 호스트는 유지된다.
(`optimizer.peak`)

### 2.2 자원단위 부하와 헤드룸 제약

```
부하(vCPU):  L = (p95_cpu / 100) · u_cur · γ
제약:        L ≤ τ · u
```

`u_cur` 현재 단위 수, `γ` 안전마진(기본 1.2, 예측 오차 버퍼), `τ` 목표 가동률 상한(기본 0.65).

### 2.3 정수계획과 정확 해

```
minimise  u
s.t.      L ≤ τ · u ,   u ∈ {1, …, u_cur} ,  u 정수
```

탐색 공간이 작고 유계이므로 1부터 전수 열거로 첫 충족값을 취한다. 닫힌형으로는:

```
u* = min( u_cur , max(1, ⌈L / τ⌉) )
```

`u_cur`로도 제약을 못 지키면(이미 과소 프로비저닝) `u_cur`로 폴백한다.
메모리는 256MB 블록으로 동일 계산:

```
b_cur = M_cur / 256
L_mem = (p95_mem / 100) · b_cur · γ
b*    = min( b_cur , ⌈L_mem / τ⌉ )
M*    = max(256, b* · 256)   [MB]
```

(`optimizer._smallest_unit_allocation`, `optimizer.recommend_resize`)

### 2.4 비용 절감과 GCP 머신 타입 스냅

```
절감률 = (1/2) · [ (u_cur - u*)/u_cur + (M_cur - M*)/M_cur ] · 100 [%]
```

추상 `(vcpu, memory)` 권장값은 사전정의 GCP 인스턴스(E2/N2/C2/C3)로 스냅되고, 월 비용이 예산 한도를
넘는 타입은 거부, 보호 인스턴스는 제외한다(보고서 §4).

---

## 3. 전 과정 연산 순서 요약

```
y_t  →  ①추세 T_t  →  ②계절 S_j  →  ③잔차+AR(1) ρ  →  ④점예측 ŷ  →  ⑤95% 구간
                                                                    │ (예측 피크)
                                                                    ▼
        ⑨할당 u*,M* + 절감  ←  ⑧정수계획 min u  ←  ⑦부하 L  ←  ⑥강건 피크 p95
                    │
                    ▼
        GCP 머신 타입(E2/N2/C2/C3) 스냅 → 예산 가드 리사이즈 → 감사 로그 영속
```

근거 코드: `backend/app/core/forecaster.py`, `backend/app/core/optimizer.py`,
평가 스크립트 `scripts/evaluate_model_paper.py`, 워크로드 모델 `docs/09_workload_modeling.md`.
