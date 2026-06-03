# UML 모델링 — MetricLens AI

본 문서는 MetricLens AI 시스템을 UML 2.x 다이어그램으로 모델링한다. 실제
코드베이스(`backend/app/`, `frontend/src/`)와 일치하도록 작성했으며, 모든
다이어그램은 Mermaid로 렌더링된다.

목차: [유스케이스](#1-유스케이스-다이어그램) · [클래스](#2-클래스-다이어그램) ·
[객체](#3-객체-다이어그램) · [시퀀스](#4-시퀀스-다이어그램) ·
[커뮤니케이션](#5-커뮤니케이션-다이어그램) · [액티비티](#6-액티비티-다이어그램) ·
[상태 머신](#7-상태-머신-다이어그램) · [컴포넌트](#8-컴포넌트-다이어그램) ·
[패키지](#9-패키지-다이어그램) · [배치](#10-배치-다이어그램) ·
[복합 구조](#11-복합-구조-다이어그램) · [타이밍](#12-타이밍-다이어그램)

---

## 1. 유스케이스 다이어그램

운영자(SRE)가 MetricLens로 수행하는 기능과 외부 액터(GCP)를 표현한다.

```mermaid
flowchart LR
    SRE([SRE / 운영자])
    GMON([Cloud Monitoring]):::ext
    GCE([Compute Engine]):::ext

    subgraph MetricLens AI
      UC1((대시보드 조회))
      UC2((CPU 부하 예측))
      UC3((리사이징 권장 조회))
      UC4((인터랙티브 리사이즈))
      UC5((과거 데이터 열람))
      UC6((테스트 시나리오 실행))
      UC7((실제 인스턴스 동기화))
      UC8((실제 VM 리사이즈))
    end

    SRE --- UC1
    SRE --- UC2
    SRE --- UC3
    SRE --- UC4
    SRE --- UC5
    SRE --- UC6
    SRE --- UC7
    SRE --- UC8
    UC2 -.->|«include»| UC3
    UC4 -.->|«extend»| UC8
    UC7 --- GMON
    UC8 --- GCE

    classDef ext fill:#eee,stroke:#888,color:#333;
```

| 유스케이스 | 액터 | 설명 |
|---|---|---|
| 부하 예측 | SRE | 호스트의 +60분 CPU를 예측하고 MAPE를 표시 |
| 리사이징 권장 | SRE | SLO 제약 정수계획으로 최소 자원 산출(예측 결과 «include») |
| 인터랙티브 리사이즈 | SRE | 권장/머신타입 적용(실제 VM이면 «extend»로 GCE 호출) |
| 실제 인스턴스 동기화 | SRE, Cloud Monitoring | 라벨된 GCE 인스턴스의 실측 메트릭 ingest |

---

## 2. 클래스 다이어그램

레이어드 구조(Controller→Service→Repository + 순수 Core)와 도메인 모델.

```mermaid
classDiagram
    class Host {
      +str id
      +str hostname
      +str environment
      +int vcpu_count
      +int memory_mb
      +datetime created_at
    }
    class Metric {
      +int id
      +str host_id
      +datetime ts
      +float cpu_pct
      +float mem_pct
      +float net_in_kbps
      +float net_out_kbps
    }
    class Forecast {
      +str id
      +str host_id
      +str metric
      +float predicted_value
      +float lower_bound
      +float upper_bound
      +float mape
    }
    class Recommendation {
      +str id
      +str host_id
      +int recommended_vcpu
      +int recommended_memory_mb
      +float est_cost_saving_pct
      +float slo_confidence
    }
    class Action {
      +str id
      +str host_id
      +str action_type
      +str detail
      +int before_vcpu
      +int after_vcpu
      +float saving_pct
    }

    class AnalysisService {
      +forecast(host_id, metric, horizon) Forecast
      +recommend(host_id) Recommendation
    }
    class HostService {
      +resize_host(id, vcpu, mem) Action
      +list_all_actions() Action[]
    }
    class HostRepository
    class ActionRepository
    class Forecaster {
      <<pure core>>
      +forecast(series, period, horizon) ForecastResult
    }
    class Optimizer {
      <<pure core>>
      +recommend_resize(...) ResizeRecommendation
      +peak(values, pct) float
    }

    Host "1" --> "*" Metric
    Host "1" --> "*" Forecast
    Host "1" --> "*" Recommendation
    Host "1" --> "*" Action
    AnalysisService ..> Forecaster : uses
    AnalysisService ..> Optimizer : uses
    AnalysisService ..> HostRepository
    HostService ..> ActionRepository
```

---

## 3. 객체 다이어그램

특정 시점(데모 플릿)의 인스턴스 스냅샷.

```mermaid
classDiagram
    class webProd01 {
      hostname = "web-prod-01"
      vcpu_count = 16
      memory_mb = 32768
    }
    class rec1 {
      recommended_vcpu = 9
      est_cost_saving_pct = 36.0
      slo_confidence = 99.9
    }
    class action1 {
      action_type = "RESIZE"
      detail = "16->9 vCPU"
      saving_pct = 36.0
    }
    webProd01 --> rec1 : recommendation
    webProd01 --> action1 : audit
```

---

## 4. 시퀀스 다이어그램

### 4.1 예측 → 권장 → 리사이즈

```mermaid
sequenceDiagram
    actor SRE
    participant UI as React Dashboard
    participant API as FastAPI Controller
    participant SVC as AnalysisService
    participant CORE as Core(forecaster/optimizer)
    participant DB as Repository/DB

    SRE->>UI: Run forecast
    UI->>API: POST /hosts/{id}/forecast
    API->>SVC: forecast(id, CPU, 60)
    SVC->>DB: list metrics(id)
    DB-->>SVC: series[]
    SVC->>CORE: forecast(series, 24, 1)
    CORE-->>SVC: ForecastResult(mape, bounds)
    SVC->>DB: save Forecast + Action(FORECAST)
    SVC-->>API: Forecast
    API-->>UI: 200 ForecastOut
    SRE->>UI: Apply recommendation
    UI->>API: POST /hosts/{id}/resize
    API->>SVC: resize_host(id, vcpu, mem)
    SVC->>DB: update Host + Action(RESIZE)
    SVC-->>UI: HostOut (persisted)
```

### 4.2 실제 인스턴스 동기화 (Cloud Monitoring)

```mermaid
sequenceDiagram
    actor SRE
    participant UI
    participant API as FastAPI
    participant GCP as GcpMonitoringService
    participant CM as Cloud Monitoring API
    participant DB

    SRE->>UI: Sync real hosts
    UI->>API: POST /gcp/sync
    API->>GCP: sync_labelled_instances()
    GCP->>CM: query cpu/utilization (metriclens=true)
    CM-->>GCP: time series[]
    GCP->>DB: upsert Host + Metric (real)
    GCP-->>UI: synced hosts[]
```

---

## 5. 커뮤니케이션 다이어그램

시퀀스 4.1과 의미적으로 동일하나 협업(메시지 번호) 관점.

```mermaid
flowchart LR
    UI -->|1: forecast| API
    API -->|2: forecast id| SVC[AnalysisService]
    SVC -->|3: list metrics| DB[(Repository)]
    SVC -->|4: forecast series| CORE[Core]
    SVC -->|5: save| DB
    API -->|6: 200| UI
```

---

## 6. 액티비티 다이어그램

예측–권장–리사이즈 워크플로우(분기/병합 포함).

```mermaid
flowchart TD
    A([시작]) --> B[메트릭 이력 조회]
    B --> C{표본 >= 2?}
    C -- 아니오 --> E[422 Insufficient Data] --> Z([종료])
    C -- 예 --> D[추세+계절 분해 예측]
    D --> F[p95 피크 계산]
    F --> G[정수계획 최소자원 탐색]
    G --> H{권장 != 현재?}
    H -- 아니오 --> I[현행 유지] --> Z
    H -- 예 --> J{헤드룸 충족?}
    J -- 예 --> K[리사이즈 적용 + 감사로그] --> Z
    J -- 아니오 --> I
```

---

## 7. 상태 머신 다이어그램

호스트(특히 실제 VM)의 리사이즈 생명주기.

```mermaid
stateDiagram-v2
    [*] --> Monitored
    Monitored --> Forecasted : run forecast
    Forecasted --> Recommended : recommend_resize
    Recommended --> Monitored : hold (near-optimal)
    Recommended --> Resizing : apply (real VM)
    Resizing --> Stopping : compute.stop
    Stopping --> Reconfiguring : setMachineType
    Reconfiguring --> Starting : compute.start
    Starting --> Monitored : healthy
    Resizing --> Rejected : cost > ₩300k 가드
    Rejected --> Monitored
```

---

## 8. 컴포넌트 다이어그램

```mermaid
flowchart TB
    subgraph Frontend
      SPA[React SPA]:::c
      Ech[ECharts]:::c
    end
    subgraph Backend
      Ctrl[Controllers]:::c
      Svc[Services]:::c
      Repo[Repositories]:::c
      Core[Core: forecaster/optimizer/workload/machine_types]:::c
      Gcp[GcpMonitoring/Compute adapter]:::c
    end
    DB[(SQLite/Postgres)]:::c
    CM[(Cloud Monitoring)]:::c
    CE[(Compute Engine)]:::c

    SPA --> Ctrl
    Ctrl --> Svc --> Repo --> DB
    Svc --> Core
    Svc --> Gcp
    Gcp --> CM
    Gcp --> CE
    classDef c fill:#f5f7f9,stroke:#c2c9d1;
```

---

## 9. 패키지 다이어그램

```mermaid
flowchart TB
    subgraph app
      api[app.api]
      services[app.services]
      repositories[app.repositories]
      models[app.models]
      schemas[app.schemas]
      subgraph core[app.core]
        forecaster
        optimizer
        workload
        machine_types
      end
    end
    api --> services --> repositories --> models
    api --> schemas
    services --> core
    repositories --> models
```

---

## 10. 배치 다이어그램

물리/클라우드 배치(GCP 네이티브).

```mermaid
flowchart TB
    Browser["«device» 브라우저"]
    subgraph GCP["«cloud» GCP project knudc-yoonwoodev"]
      subgraph Run["«execution env» Cloud Run"]
        FE["«artifact» metriclens-frontend (nginx)"]
        BE["«artifact» metriclens-backend (FastAPI)"]
      end
      AR["«artifact store» Artifact Registry"]
      CB["«CI/CD» Cloud Build"]
      MON["«service» Cloud Monitoring"]
      subgraph GCE["«execution env» Compute Engine (us-central1-a)"]
        V1["«device» ml-web-01 (e2-small)"]
        V2["«device» ml-api-02"]
        V3["«device» ml-batch-03"]
        V4["«device» ml-idle-04"]
      end
    end
    Browser -->|HTTPS| FE
    FE -->|REST| BE
    CB --> AR --> Run
    BE -->|query metrics| MON
    GCE -->|cpu/utilization| MON
    BE -->|setMachineType| GCE
```

---

## 11. 복합 구조 다이어그램

`AnalysisService`의 내부 부품(part)과 포트.

```mermaid
flowchart LR
    subgraph AnalysisService
      direction LR
      pHost[": HostRepository"]
      pMetric[": MetricRepository"]
      pFore[": forecaster"]
      pOpt[": optimizer"]
      portIn(( in )) --> pMetric
      pMetric --> pFore
      pFore --> pOpt
      pOpt --> portOut(( out ))
    end
```

---

## 12. 타이밍 다이어그램

리사이즈 시 실제 VM 상태의 시간축 변화(Mermaid 미지원 → ASCII 표현).

```
상태
RUNNING     ────┐                              ┌────────────
STOPPING        └──┐                        
TERMINATED         └────┐              ┌──┘
RECONFIG                └──(setType)──┘
            t0   t1   t2          t3   t4  →  시간
            apply stop  terminated  setType start
```

> 실제 리사이즈는 stop → setMachineType → start 순으로 진행되며, 다운타임은
> t1~t4 구간이다. `≤ ₩300k/월` 비용 가드를 통과한 경우에만 수행된다.

---

마지막 갱신: 2026-06-03 · 생성 근거: 실제 코드베이스(`backend/app/`) 및 배포 구성.
