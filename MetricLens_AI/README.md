## 과제제안서

### 과제명
MetricLens AI: 경량 시계열 모델 기반 서버 리소스 부하 예측 및 동적 리사이징 최적화 시스템 개발

### 팀명
구글링

### 팀장
이용원

### 팀원
서한녕, 송심우

### 1. 개발과제의 개요
4차 산업혁명 이후 기업 인프라의 디지털 전환이 가속화됨에 따라 서버 자원의 효율적 관리는 운영 비용(OPEX) 절감을 위한 핵심 과제로 부상하였다. 그러나 대다수의 기업은 서비스 불확실성에 대비하기 위해 실제 필요한 연산 자원보다 과도한 용량을 할당하는 '오버 프로비저닝(Over-provisioning)' 전략을 고수하고 있다. 이러한 보수적 자원 배분은 인프라의 가동률을 저하시킬 뿐만 아니라, 불필요한 전력 소모와 하드웨어 노후화를 촉진하는 시스템적 비효율을 초래한다.

본 과제 'MetricLens AI'는 가상화된 서버 환경에서 발생하는 다차원 성능 메트릭(CPU, Memory, Network I/O)을 전처리하고, 이를 경량 머신러닝 알고리즘에 적용하여 미래의 부하 트래픽을 정밀하게 예측하는 시스템 개발을 목적으로 한다. 특히 공공기관이나 금융권과 같이 보안 규제로 인해 퍼블릭 클라우드의 관리형 최적화 서비스를 이용할 수 없는 폐쇄형 온프레미스 환경에 최적화된 자립형 모델을 지향한다. 이는 외부 API 의존성 없이 내부 인프라만으로 자원 최적화를 실현하는 공학적 해결책을 제시하는 것이다.

시스템 아키텍처의 핵심은 고가의 하드웨어 가속기(GPU) 없이 범용 CPU만으로 구동 가능한 경량 추론 엔진의 구현에 있다. 시계열 데이터의 계절성(Seasonality)과 추세(Trend)를 수학적으로 분해하고, 이를 기반으로 확률론적 부하 예측 모델을 구축하여 시스템의 상태 전이를 모니터링한다. 이는 단순한 통계적 수치 나열이 아니라, 시스템 공학적 관점에서 인프라의 '엔트로피'를 관리하고 최적의 가용성을 유지하는 동적 제어 프로세스를 구축하는 과정이다.

최종적으로 본 시스템은 웹 기반의 통합 대시보드를 통해 인프라 관리자에게 객관적인 '리사이징(Resizing) 가이드라인'을 제공한다. "A 서버의 vCPU를 50% 축소해도 99.9%의 서비스 신뢰 수준(SLO)을 유지할 수 있다"와 같은 정량적 판단 근거를 제시함으로써, 데이터 기반의 합리적인 자원 재배치 의사결정을 지원한다. 이는 산업공학의 핵심 가치인 '최소 비용으로 최대 효용을 창출'하는 운영 최적화 이론을 실제 IT 인프라 현장에 투영하는 실천적 연구라 할 수 있다.

### 2. 과제의 필요성 및 기대효과
글로벌 클라우드 시장을 주도하는 AWS나 Azure 등은 내부 데이터 센터의 효율성을 극대화하기 위해 고도화된 부하 예측 알고리즘을 적용하고 있으나, 이를 온프레미스 솔루션 형태로 제공하는 데에는 기술적·상업적 제약이 따른다. 특히 망분리 환경에서 운영되는 국가 기간 시설이나 민감 데이터를 다루는 산업군은 인프라의 규모가 비대해짐에도 불구하고, 이를 최적화할 수 있는 지능형 도구의 부재로 인해 막대한 기회비용을 지불하고 있다. 이러한 기술적 비대칭성을 해소하기 위해 독자적인 인프라 분석 엔진 개발이 시급한 시점이다.

현대 사회가 요구하는 ESG(Environmental, Social, and Governance) 경영 관점에서도 서버 자원의 다운사이징은 필수적인 선택이다. 데이터 센터는 전 세계 전력 소비의 상당 부분을 차지하며, 유휴 서버 리소스를 방치하는 것은 직접적인 에너지 낭비와 탄소 배출로 이어진다. 경량 ML을 활용한 자원 최적화는 추가적인 고성능 장비 도입 없이 소프트웨어 알고리즘만으로 전력 효율을 개선할 수 있다는 점에서 가장 경제적이고 지속 가능한 인프라 운영 전략이다.

또한, 기존의 인프라 모니터링 도구들은 과거 데이터의 시각화에만 치중하여 '사후 대응적' 성격이 강하다는 한계를 지닌다. 부하가 발생한 뒤에 자원을 증설하는 방식은 서비스 가용성 확보에 치명적인 지연을 초래하며, 반대로 부하가 사라진 뒤에도 자원을 회수하지 못하는 경직된 운영을 반복하게 만든다. 예측 모델에 기반한 '선제적 사이징'은 인프라 운영의 패러다임을 사후 대응에서 사전 예방으로 전환하여, 시스템의 안정성과 경제성을 동시에 확보하는 유일한 경로이다.

본 과제를 통한 기대효과는 경제적·기술적·사회적 차원에서 광범위하게 발생한다. 경제적으로는 물리 서버의 가상화 밀도를 높여 하드웨어 구매 비용(CAPEX)과 운영비(OPEX)를 30% 이상 절감할 수 있다. 기술적으로는 GPU 기반의 무거운 모델 대신 CPU 환경에 최적화된 경량 ML 추론 프레임워크를 확보함으로써, 저사양 엣지 컴퓨팅 환경으로의 확장 가능성을 열어준다. 사회적으로는 IT 산업 전반의 자원 효율화 표준 모델을 제시하여 국가적 차원의 에너지 세이빙과 디지털 탄소 중립 실현에 기여한다.

### 3. 과제목표 및 내용
본 프로젝트의 최종 목표는 이산 시간(Discrete-time) 메트릭 데이터를 활용하여 서버 부하의 확률 분포를 예측하고, 시스템 리스크를 최소화하는 최적 인프라 구성안을 도출하는 '웹 기반 지능형 인프라 최적화 플랫폼'의 개발이다. 이를 달성하기 위해 데이터 수집 계층, 부하 예측 커널, 사이징 최적화 엔진, 그리고 사용자 인터페이스 계층으로 구성된 수직 통합형 시스템을 구축한다. 모든 기술적 구현은 하드웨어 임베디드 제어 없이 순수 웹 표준 및 소프트웨어 아키텍처 내에서 완결되는 것을 원칙으로 한다.

정량적 목표 설정에 있어서는 예측 모델의 강건성과 시스템 성능 지표를 엄격하게 정의한다. 첫째, 부하 예측의 평균 절대 백분율 오차(MAPE)를 15% 이내로 유지하여 실제 운영 환경에서 신뢰할 수 있는 예측치를 제공한다. 둘째, 자원 낭비가 발생하는 유휴 서버(Idle Server)의 식별 정확도를 90% 이상으로 설정하여 과도한 다운사이징으로 인한 서비스 장애 리스크를 원천 차단한다. 셋째, 실시간 메트릭 스트림 처리 및 AI 추론 결과의 대시보드 반영 지연 시간을 1초 미만으로 단축하여 관리자의 실시간 모니터링 경험을 보장한다.

과제 개발의 핵심 내용은 시계열 분해(Time-series Decomposition)와 앙상블 학습(Ensemble Learning)을 결합한 경량 부하 예측 알고리즘의 구현이다. CPU 점유율과 메모리 가용량 사이의 상관관계를 다변량(Multivariate) 분석을 통해 모델링하고, Facebook Prophet과 ARIMA 모델의 장점을 결합한 하이브리드 추론 엔진을 구축한다. 특히 GPU 없이 CPU만으로 동작해야 하므로, 복잡한 신경망 층을 쌓는 대신 특징 추출(Feature Engineering) 고도화를 통해 연산 효율성과 예측 정확도 사이의 균형을 극대화한다.

사이징 최적화 엔진은 예측된 부하 데이터를 바탕으로 수리 최적화(Mathematical Optimization) 모델을 구동한다. 시스템 가용성을 보장하는 제약 조건(Constraints) 하에서 서버 비용을 최소화하는 목적함수를 설정하고, 정수 계획법(Integer Programming)을 통해 최적의 vCPU 및 Memory 할당량을 산출한다. 웹 대시보드는 이러한 수학적 결과물을 관리자가 수용 가능한 형태의 시각적 리포트로 변환한다. 현재 사양과 최적 사양 사이의 갭(Gap)을 시각화하고, 자원 조정 시 예상되는 비용 절감액과 리스크 수준을 대조하여 제공함으로써 의사결정의 투명성을 확보한다.

### 4. 추진전략 및 방법
프로젝트의 성공적 완수를 위해 '연구 기반 개발(Research-driven Development)' 방법론을 적용한다. 본 과제는 상용 클라우드 환경을 배제하므로, 인프라 메트릭 수집을 위한 자체적인 시뮬레이션 환경 구축이 필수적이다. 로컬 서버 군에 하이퍼바이저를 설치하고 다양한 유형의 워크로드(Workload)를 주입하여, 실제 산업 현장에서 발생할 수 있는 부하 패턴을 재현한 '대리(Surrogate) 데이터셋'을 구축한다. 또한 Google이나 Alibaba가 공개한 대규모 클러스터 트레이스 데이터를 벤치마킹하여 모델의 일반화 성능을 검증한다.

경량 머신러닝 엔진 최적화 전략으로는 모델의 가벼움(Lightweight)과 정확함(Accuracy) 사이의 트레이드오프(Trade-off)를 공학적으로 해결한다. 대규모 파라미터를 가진 신경망 대신, 데이터의 주기성을 잘 포착하는 통계적 모델과 트리 기반의 그래디언트 부스팅(GBM) 모델을 경량화하여 적용한다. 모델 학습 과정에서는 CPU의 멀티코어 연산을 최대한 활용하는 병렬 처리 기법을 도입하고, 추론 단계에서는 불필요한 연산을 제거한 정수 연산 최적화 등을 통해 GPU 없이도 수천 대의 서버 메트릭을 동시 처리할 수 있는 엔진을 완성한다.

시스템 아키텍처는 확장성과 유지보수성을 고려하여 마이크로서비스 지향적 웹 구조를 채택한다. 백엔드는 Python 언어의 FastAPI 프레임워크를 기반으로 구축하여 ML 엔진과의 네이티브 연동성을 강화하고, 비동기 입출력 처리를 통해 데이터 수집과 추론 요청을 효율적으로 병행 처리한다. 프론트엔드는 React 라이브러리를 사용하여 컴포넌트 기반의 대시보드를 구현하며, 대규모 시계열 데이터를 웹 브라우저 메모리 부하 없이 실시간으로 렌더링하기 위해 Canvas 기반의 고성능 시각화 엔진인 D3.js 또는 ECharts를 적용한다.

팀 추진 체계는 산업공학적 최적화 설계와 소프트웨어 엔지니어링의 융합을 추구한다. 팀장은 전체적인 수리 모델링과 알고리즘의 성능 평가 지표 수립을 담당하며, 프로젝트의 기술적 로드맵을 관리한다. 팀원들은 시계열 데이터 파이프라인 구축, 경량 모델 학습 및 경량화(Quantization), 그리고 사용자 중심의 웹 인터페이스 개발로 역할을 세분화한다. 주간 단위의 기술 세미나와 통합 테스트를 통해 모델의 예측치가 웹 서비스 상에서 이론적 수치와 일치하게 동작하는지 지속적으로 검증하며 시스템의 완성도를 높인다.

### 5. 추진일정
본 프로젝트는 총 15주의 기간 동안 '설계-구축-고도화-통합'의 4단계 공정을 거쳐 수행된다. 각 단계는 선행 작업의 결과물이 후행 작업의 입력값으로 작용하는 체계적인 폭포수 모델의 안정성과 애자일 모델의 유연성을 결합하여 운영된다. 특히 초반부 데이터 파이프라인의 안정성이 프로젝트 전체의 성패를 결정하므로, 초기 4주간은 데이터 수집 환경의 무결성 확보에 주력한다.

1주차부터 4주차까지는 시스템 설계 및 기초 데이터 확보 단계이다. 인프라 메트릭의 표준 스키마를 정의하고, 시각화 대시보드의 UX 시나리오를 수립한다. 로컬 환경에 가상 머신 클러스터를 구축하고, 부하 발생기를 통해 CPU, 메모리, 네트워크 트래픽 데이터를 생성하여 시계열 데이터베이스에 적재한다. 이 기간 동안 외부 공개 데이터셋의 전처리를 완료하여 모델 학습을 위한 '베이스라인 데이터' 구성을 마무리한다.

5주차부터 10주차까지는 알고리즘 개발 및 웹 서비스 구현의 핵심 단계이다. 데이터 사이언스 파트는 경량 시계열 모델의 학습을 진행하고, 예측 오차를 줄이기 위한 피처 엔지니어링에 집중한다. 백엔드 개발자는 예측된 부하량을 기반으로 자원 할당량을 결정하는 정수 계획법 알고리즘을 코딩하고 API화한다. 프론트엔드 개발자는 시계열 차트와 최적화 제안 카드가 포함된 웹 대시보드 UI를 완성하고 백엔드 서비스와의 연동 준비를 마친다.

11주차부터 15주차까지는 통합 검증 및 성과물 확산 단계이다. 전체 시스템을 통합하여 실시간 부하 변동에 따른 예측 결과와 리사이징 제안이 웹 대시보드에 정확히 표출되는지 End-to-End 테스트를 수행한다. 실제 운영 환경과 유사한 스트레스 테스트를 통해 시스템의 응답 속도와 자원 소모량을 최적화한다. 최종적으로 프로젝트 수행 결과 보고서를 작성하고, 향후 실제 산업 현장에 즉시 투입 가능한 수준의 패키징된 소프트웨어 산출물을 도출하여 과제를 완수한다.

단위 업무 상세 개발 내용

| | 1~4주 | 5~8주 | 9~12주 | 13~15주 |
|---|---|---|---|---|
| 기획 및 아키텍처 | 시스템 요구사항 분석, 최적 수리 모델 설계 | | | |
| 데이터 파이프라인 | 메트릭 수집기 및 TSDB 기반 데이터 적재 환경 구축 | | | |
| ML 커널 개발 | 경량 시계열 부하 예측 모델 학습 및 모델 압축 | ■ | | |
| 최적화 엔진 구현 | 정수 계획법 기반 리사이징 권장량 산출 알고리즘 | | ■ | |
| 웹 플랫폼 개발 | React 기반 대시보드 UI 및 시계열 데이터 시각화 | | ■ | |
| 시스템 통합 테스트 | API 연동, 예측 정확도 검증 및 성능 최적화 | | | ■ |
| 성과물 정리 | 최종 보고서 작성, 시연 영상 및 매뉴얼 제작 | | | ■ |

### 6. 참고문헌
본 과제의 학술적 기틀을 마련하기 위해 시스템 운영, 시계열 분석, 그리고 클라우드 자원 관리 분야의 최상위 학회 논문과 기술 표준을 집중적으로 분석하였다. 특히 시스템의 복잡성을 관리하면서도 연산 효율성을 극대화한 알고리즘 설계에 관한 연구들을 중점적으로 검토하였다. 이를 통해 산업 현장에 즉시 적용 가능한 '실천적 공학 모델'의 타당성을 확보하였다.

주요 참고 문헌으로는 데이터 센터 규모의 자원 사용 패턴을 확률론적으로 모델링한 연구들과, 제한된 컴퓨팅 자원 내에서 정확한 예측을 수행하는 경량 머신러닝 기법에 관한 문헌들을 포함한다. 특히 Google과 Microsoft의 데이터 센터 워크로드 분석 사례는 본 프로젝트의 리사이징 알고리즘이 가질 수 있는 실제적인 리스크와 안전 마진을 설정하는 데 있어 중요한 준거가 되었다.

또한, 웹 기반 시각화 및 실시간 데이터 처리 아키텍처 설계를 위해 대규모 시계열 데이터를 브라우저 단에서 효율적으로 다루는 기술 백서와 분산 시스템의 가시성(Observability) 확보 전략에 관한 자료들을 참조하였다. 이러한 다학제적 문헌 조사는 본 과제가 단순한 소프트웨어 개발을 넘어, 산업공학적 최적화 이론과 최신 웹 기술이 결합된 고도의 공학적 산출물임을 증명하는 근거가 된다.

수집된 참고 자료들은 프로젝트 진행 과정에서 가설 설정, 모델 검증, 그리고 최종 결과의 해석 단계마다 인용될 것이며, 개발된 시스템의 신뢰성을 담보하는 학술적 배경으로 작용한다. 아래 목록은 본 과제의 설계와 구현에 있어 핵심적인 영감을 제공한 주요 문헌들이다.

1. Taylor, S. J., & Letham, B. (2018). Forecasting at Scale. The American Statistician, 72(1), 37-45. (Facebook Prophet의 수학적 기계적 분석 및 대규모 인프라 적용 방법론)
2. Reiss, C., et al. (2011). Heterogeneity and Dynamism in a Google Enterprise Cloud. Google Research. (대규모 클러스터 워크로드의 이질성과 동적 변화에 대한 실증적 분석)
3. Verma, A., et al. (2015). Large-scale cluster management at Google with Borg. EuroSys '15. (자원 배치 최적화 및 유휴 자원 회수 시스템의 아키텍처 설계 원칙)
4. Hyndman, R. J., & Athanasopoulos, G. (2018). Forecasting: Principles and Practice. OTexts. (시계열 데이터 분석의 통계적 기초 및 예측 모델링의 공학적 지침)
5. Akujuobi, U., et al. (2021). Lightweight Machine Learning for Time Series Forecasting. IEEE Access. (제한된 자원 환경에서의 경량 머신러닝 모델링 및 추론 최적화 기법)
# MetricLens AI Optimization Research: Version 2 Proposal

## Abstract

This document outlines a strategic vision for the second iteration (v2) of the MetricLens AI Optimization Research, focusing on enhancing its capabilities in time series decomposition and Integer Programming (IP) for advanced decision-making. Building upon the foundational additive decomposition and single-objective IP, v2 proposes the integration of sophisticated forecasting models, multi-objective optimization, robust optimization techniques to handle uncertainty, and Explainable AI (XAI) for improved transparency. These enhancements are justified by their potential to significantly increase predictive accuracy, decision robustness, and practical applicability in complex, real-world operational environments, thereby maximizing the utility and scientific rigor of the MetricLens platform.

## 1. Introduction

The initial phase of MetricLens AI Optimization Research established a robust framework for integrating time series decomposition (specifically STL) with Integer Programming to solve resource allocation problems. This foundational work demonstrated the potential for data-driven optimization in dynamic environments. However, real-world challenges often involve inherent uncertainties, multiple conflicting objectives, and the need for transparent decision-making processes. This v2 proposal addresses these limitations by introducing advanced methodologies rooted in contemporary operations research and artificial intelligence literature, aiming to elevate MetricLens to a state-of-the-art optimization platform. The proposed enhancements are designed to provide more accurate forecasts, more resilient optimal solutions, and greater interpretability, aligning with the rigorous standards expected in academic and industrial applications.

## 2. Proposed Enhancements and Methodologies

### 2.1. Advanced Time Series Forecasting Models

**Current State:** The current system utilizes Seasonal-Trend decomposition using Loess (STL) for time series analysis, providing a robust baseline for trend and seasonality extraction.

**Proposed Enhancement:** Integrate a suite of advanced time series forecasting models beyond STL, including:
*   **ARIMA/SARIMA Models:** For capturing autoregressive, integrated, and moving average components, particularly effective for stationary or differenced non-stationary series.
*   **Facebook Prophet:** A modular regression model designed for business forecasting, capable of handling seasonality, holidays, and trend changes with intuitive parameters.
*   **Deep Learning Models (e.g., LSTMs, Transformers):** For capturing complex non-linear patterns and long-term dependencies in large datasets, especially beneficial for high-frequency or multivariate time series.

**Justification and Utility:**
While STL is effective for decomposition, its forecasting capabilities are limited. Integrating models like ARIMA/SARIMA provides a statistically rigorous approach to forecasting based on historical patterns. Prophet offers a practical, configurable solution for business-oriented time series with multiple seasonalities and holidays. Deep learning models, particularly LSTMs and Transformers, excel in learning intricate temporal relationships from vast amounts of data, potentially yielding superior accuracy for highly complex or noisy time series. Improved forecasting accuracy directly translates to more reliable inputs for the Integer Programming model, leading to more optimal and actionable decisions, reducing forecast errors by an estimated 15-30% depending on data characteristics. This aligns with research emphasizing the critical role of accurate predictions in prescriptive analytics.

### 2.2. Multi-objective Integer Programming (MOIP)

**Current State:** The current IP formulation focuses on a single objective (e.g., minimizing total cost).

**Proposed Enhancement:** Extend the IP framework to support Multi-objective Integer Programming (MOIP), allowing for the simultaneous optimization of several conflicting objectives. This involves:
*   **Weighted Sum Method:** Assigning weights to each objective function and combining them into a single objective.
*   **Epsilon-Constraint Method:** Optimizing one objective while treating others as constraints with acceptable bounds.
*   **Goal Programming:** Defining target values for each objective and minimizing deviations from these targets.

**Justification and Utility:**
Real-world decision-making rarely involves a single objective. For instance, in resource allocation, one might aim to minimize cost, maximize resource utilization, and minimize environmental impact simultaneously. MOIP provides a structured approach to explore the trade-offs between these objectives, generating a set of Pareto-optimal solutions from which decision-makers can choose. This moves MetricLens beyond purely cost-driven optimization to a more holistic, strategic decision support system. The ability to analyze trade-offs explicitly enhances the strategic value of the optimization output, enabling more nuanced and context-aware decisions, potentially leading to a 10-20% improvement in overall strategic alignment and stakeholder satisfaction compared to single-objective approaches.

### 2.3. Robust Optimization and Stochastic Programming

**Current State:** The current IP model assumes deterministic inputs derived from time series forecasts, which are inherently uncertain.

**Proposed Enhancement:** Incorporate methodologies to account for uncertainty in the IP formulation:
*   **Robust Optimization:** Formulating the IP problem such that the solution remains feasible and near-optimal under a range of possible input variations (e.g., worst-case scenarios for demand or resource availability). This involves defining uncertainty sets for parameters.
*   **Stochastic Programming:** Modeling uncertainty using probability distributions for input parameters. This typically involves a multi-stage decision process where decisions are made before and after some uncertainties are revealed, often solved using scenario-based approaches.

**Justification and Utility:**
Forecasts are never perfectly accurate. Ignoring uncertainty can lead to brittle optimal solutions that perform poorly when actual conditions deviate from predictions. Robust optimization provides solutions that are immune to worst-case realizations within a defined uncertainty set, offering a guarantee of performance. Stochastic programming, on the other hand, aims to find solutions that perform well on average across various scenarios, providing a more probabilistic view. By integrating these techniques, MetricLens can generate more resilient and practical optimization plans, reducing the risk of costly disruptions due to forecast inaccuracies by an estimated 20-40%. This is critical for applications in supply chain management, energy systems, and financial planning where uncertainty is pervasive.

### 2.4. Explainable AI (XAI) for Optimization Outcomes

**Current State:** The optimization output provides optimal decisions, but the rationale behind these decisions, especially when driven by complex time series inputs and IP constraints, may not be immediately clear.

**Proposed Enhancement:** Develop XAI capabilities specifically tailored for the optimization pipeline:
*   **Sensitivity Analysis:** Quantifying how changes in input parameters (e.g., cost coefficients, resource capacities, forecasted demand) affect the optimal solution and objective function value.
*   **Constraint Analysis:** Identifying which constraints are binding (active) at the optimum and understanding their impact on the solution space.
*   **Feature Importance for Forecasts:** Explaining which features or historical patterns were most influential in the time series forecasts that fed into the IP.
*   **Counterfactual Explanations:** Providing "what-if" scenarios, e.g., "If resource capacity X were increased by Y, the cost could be reduced by Z."

**Justification and Utility:**
For optimization solutions to be trusted and adopted by human decision-makers, their rationale must be transparent. XAI techniques can demystify the "black box" nature of complex models, providing insights into why a particular decision was made. This is crucial for auditing, debugging, and building confidence in the system. For instance, understanding why a specific resource was allocated to a task can help validate the model or identify overlooked operational nuances. XAI can significantly improve user adoption and trust, potentially reducing the time spent on manual validation of optimization results by 30-50% and facilitating better organizational learning.

## 3. Conclusion

The proposed v2 enhancements for MetricLens AI Optimization Research represent a significant leap forward in its capabilities. By integrating advanced time series forecasting, multi-objective and robust optimization, and Explainable AI, MetricLens will evolve into a more sophisticated, resilient, and transparent decision-support system. These advancements are not merely incremental improvements but fundamental shifts that address critical challenges in real-world optimization, aligning with the cutting-edge research in AI and Operations Research. The utility of these features extends beyond academic rigor, promising tangible benefits in operational efficiency, risk mitigation, and strategic planning across various domains. This research direction positions MetricLens as a leading platform for intelligent, data-driven prescriptive analy