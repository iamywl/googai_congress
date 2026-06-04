# MetricLens 한계점 분석 #11 — architecture-debt

- 생성: 20260603-1530
- 모델: gemini-2.5-flash (Vertex AI / knudc-yoonwoodev/us-central1)
- 관점: 아키텍처·기술부채의 한계. 데모 SQLite ↔ 운영 Postgres 이중 경로의 동기화·동작 차이, 레이어드 구조의 실제 준수도, 시드/멱등성·마이그레이션 전략, 단일 백엔드의 장애 격리·관측가능성 부재를 분석한다.
- 입력 코퍼스: /home/ywlee/metriclens/limitations_review/_input/context.md (9648 줄)

---

## 0. 관점 메모
이 렌즈에서는 MetricLens AI 프로젝트의 아키텍처 부채와 관련된 한계점을 집중적으로 분석한다. 특히, 데모 환경과 운영 환경 간의 데이터베이스 이중화 문제, 계층형 아키텍처의 실제 준수 여부, 데이터 시딩 및 마이그레이션 전략의 견고함, 그리고 단일 백엔드 서비스가 가지는 장애 격리 및 관측 가능성 측면에서의 약점을 살펴본다.

## 1. 핵심 한계 요약
1.  **데모-운영 이중 경로로 인한 데이터베이스 동기화 및 동작 불일치 위험**: SQLite (데모)와 PostgreSQL (운영) 간의 이중 경로가 잠재적인 기능 불일치 및 예측 불가능한 동작을 야기한다.
2.  **형식적인 계층형 아키텍처와 실제 코드의 불일치**: 문서에 명시된 엄격한 계층형 아키텍처 원칙(단방향 의존성)이 `backend/app/api/deps.py`와 같은 코드에서 일부 모호하게 구현되어 원칙 준수도를 떨어뜨린다.
3.  **감사 추적 주장의 영속성 부족**: `ActivityLog`와 같은 핵심 기능이 데모 모드에서 휘발성 `/tmp` SQLite를 사용하여 "영속적 감사 추적"이라는 시스템의 핵심 차별점과 모순된다.
4.  **단일 백엔드 서비스의 장애 격리 취약성**: 모든 핵심 기능(API, 예측, 최적화, GCP 통합)이 단일 FastAPI 백엔드 서비스 내에 존재하여, 특정 기능의 부하나 오류가 전체 시스템의 가용성에 영향을 미칠 수 있다.
5.  **마이그레이션 전략의 부재 및 자동 시딩의 제한적 사용**: `scripts/schema.sql`과 `scripts/seed_data.sql`은 멱등성을 보장하지만, 실제 운영 환경에서의 복잡한 스키마 변경 이력 관리(마이그레이션) 전략은 명시되지 않았다.

## 2. 상세 분석

*   **[심각도: 치명] 데모-운영 이중 경로로 인한 데이터베이스 동기화 및 동작 불일치 위험**
    *   **무엇이**: `backend/app/config.py`에서 `database_url`의 기본값이 `"sqlite+aiosqlite:////tmp/metriclens.db"`로 설정되어 있으며, `auto_seed`가 True일 경우 `backend/app/main.py`의 `lifespan` 함수에서 SQLite 전용으로 `create_schema()` 및 `seed_demo_data()`를 호출한다. 반면, `cloudbuild.yaml`에서는 `_CLOUDSQL_INSTANCE` 변수 존재 여부에 따라 PostgreSQL(`METRICLENS_DATABASE_URL`)을 사용하도록 분기된다.
    *   **근거(인용)**:
        *   `backend/app/config.py`: `database_url: str = "sqlite+aiosqlite:////tmp/metriclens.db"`
        *   `backend/app/main.py`: `if settings.auto_seed and settings.database_url.startswith("sqlite"): ...`
        *   `cloudbuild.yaml`: `if [ -n "${_CLOUDSQL_INSTANCE}" ]; then EXTRA="--add-cloudsql-instances=${_CLOUDSQL_INSTANCE} ..."`
        *   `docs/12_limitations.md`: "DB가 `sqlite+aiosqlite:////tmp/metriclens.db` ([`config.py`](../backend/app/config.py))이고 Cloud Run은 scale-to-zero다. `/tmp`는 인스턴스 휘발성이라 콜드스타트마다 기록이 소실·재시드된다."
    *   **왜 문제**: 개발/데모 환경에서 SQLite를 사용하는 것은 편리하지만, SQLite와 PostgreSQL은 SQL 문법, 트랜잭션 처리, 동시성 관리, 인덱싱 최적화 등에서 상당한 차이가 있다. 이로 인해 데모 환경에서 정상 작동하던 로직이 PostgreSQL 운영 환경에서 문제를 일으킬 수 있으며, 그 반대의 경우도 가능하다. 특히 ORM(`sqlalchemy`)이 이러한 차이를 어느 정도 추상화하지만, 특정 기능(예: `ON CONFLICT` 동작)이나 성능 특성은 데이터베이스마다 다르게 나타날 수 있다. `docs/12_limitations.md`에서 이미 `/tmp` SQLite 사용으로 인한 "영속 기록" 차별점과의 충돌을 지적하고 있다.
    *   **어떤 조건에서 드러나는가**:
        *   PostgreSQL 특정 기능(예: `GENERATED ALWAYS AS IDENTITY`)을 SQLite에서 지원하지 않거나 다른 방식으로 에뮬레이션해야 할 때.
        *   동시성 높은 트랜잭션 부하가 발생할 때 SQLite의 낮은 동시성 처리 능력이 병목이 될 때.
        *   개발/테모 환경에서 발견되지 않은 버그가 운영 환경에서 PostgreSQL의 다른 동작 방식 때문에 발생할 때.

*   **[심각도: 중간] 형식적인 계층형 아키텍처와 실제 코드의 불일치**
    *   **무엇이**: `docs/02_architecture_volume.md`에서는 Controller → Service → Repository의 엄격한 수직 분리를 강조하며 Core 로직(`forecaster`, `optimizer`)이 영속성/전송 관심사로부터 격리된다고 설명한다. `main.py`의 `lifespan` 함수에서 `create_schema()`와 `seed_demo_data()`를 호출하는 것은 `db.py`에 정의된 `Base.metadata.create_all`을 사용하며, 이는 ORM(`models.py`) 정의를 통해 스키마를 생성한다.
    *   **근거(인용)**:
        *   `docs/02_architecture_volume.md`: "백엔드는 단일 FastAPI 애플리케이션 내부에서 다시 Controller → Service → Repository 의 수직 분리를 강제하여, 시계열 예측·정수 계획 코어 로직(`core`)을 영속성·전송 관심사로부터 격리한다."
        *   `docs/02_architecture_volume.md`의 모듈 간 의존성 관계 맵: `services --> core` (단방향 의존성)
        *   `backend/app/api/deps.py`: `get_analysis_service` 함수가 `AnalysisRepository(session)`를 직접 주입받는다.
        *   `backend/app/services.py`: `AnalysisService`가 `AnalysisRepository`를 직접 사용한다.
        *   `backend/app/main.py`: `lifespan` 함수에서 DB 스키마 생성 및 시드 데이터 적재를 수행.
    *   **왜 문제**: 계층형 아키텍처의 핵심은 각 계층이 명확한 책임과 제한된 의존성을 갖는 것이다. `api/deps.py`에서 Service 계층이 Repository를 인자로 받는 것은 일반적인 패턴이지만, `main.py`의 `lifespan`에서 스키마 생성 및 시딩 로직이 애플리케이션의 핵심 라이프사이클에 포함되어 비즈니스 로직(Service)이나 영속성 로직(Repository) 계층을 우회할 수 있다. 이는 계층 간 관심사 분리를 약화시키고, 특히 복잡한 마이그레이션 시나리오에서 예측치 못한 부작용을 일으킬 수 있다.
    *   **어떤 조건에서 드러나는가**:
        *   스키마 변경 시 `lifespan`의 `create_schema`가 기존 데이터를 보존하지 않고 덮어쓸 위험이 있을 때.
        *   애플리케이션 부트 시점의 DB 작업이 복잡해지거나 실패할 때 전체 애플리케이션 시작이 지연되거나 실패할 때.
        *   Service 계층의 로직이 Repository를 직접 호출하지 않고 `lifespan`과 같은 외부 지점에서 데이터를 조작할 때 비즈니스 규칙 위반 가능성.

*   **[심각도: 치명] 감사 추적 주장의 영속성 부족**
    *   **무엇이**: `README.md` 및 `docs/08_competitive_analysis.md`에서 MetricLens의 핵심 차별점 중 하나로 "감사 추적"을 내세우며 "모든 예측·리사이즈를 영속 기록"한다고 주장한다. 하지만 `docs/12_limitations.md`에 명시된 바와 같이 데모 환경에서는 `sqlite+aiosqlite:////tmp/metriclens.db`를 사용하여 `/tmp` 디렉토리에 데이터베이스 파일을 저장한다. Cloud Run 인스턴스는 스테이트리스(stateless)하며 콜드 스타트 시 `/tmp`를 포함한 파일 시스템이 휘발성이므로, 기록이 유실된다.
    *   **근거(인용)**:
        *   `README.md`: "감사 추적 — 모든 예측·리사이즈를 영속 기록."
        *   `docs/08_competitive_analysis.md`: "감사 추적 (Audit Trailing) — 모든 예측·리사이즈가 `actions` 테이블에 영속 기록되어 '누가 언제 16→8 vCPU로 얼마나 줄였는지'를 거버넌스 관점에서 추적한다."
        *   `docs/12_limitations.md`: "DB가 `sqlite+aiosqlite:////tmp/metriclens.db` ([`config.py`](../backend/app/config.py))이고 Cloud Run은 scale-to-zero다. `/tmp`는 인스턴스 휘발성이라 콜드스타트마다 기록이 소실·재시드된다."
        *   `backend/app/config.py`: `database_url: str = "sqlite+aiosqlite:////tmp/metriclens.db"`
    *   **왜 문제**: "영속 기록"과 "감사 추적"이라는 핵심 주장이 실제 데모/개발 환경에서는 충족되지 않아 마케팅/기능 설명과 실제 구현 간의 심각한 불일치가 발생한다. 이는 시스템의 신뢰성을 떨어뜨리고, 특히 감사가 필요한 환경에서는 치명적인 결함으로 작용한다. 콜드 스타트가 잦은 서버리스 환경에서 데이터가 유실되는 것은 심각한 운영 문제다.
    *   **어떤 조건에서 드러나는가**:
        *   Cloud Run 인스턴스가 스케일 투 제로(scale-to-zero) 정책에 따라 유휴 상태에서 종료된 후 재시작될 때 모든 감사 기록이 유실될 때.
        *   데모 환경에서 장기간 사용 후 과거 기록을 조회하려 할 때 데이터가 없어 당황스러울 때.
        *   운영 환경에서도 `--add-cloudsql-instances` 설정 없이 SQLite를 그대로 사용할 경우 동일한 문제가 발생한다.

*   **[심각도: 높음] 단일 백엔드 서비스의 장애 격리 취약성**
    *   **무엇이**: `backend/app/main.py`에 모든 라우터(`routes_hosts`, `routes_metrics`, `routes_analysis`, `routes_catalog`, `routes_history`, `routes_gcp`)가 포함되어 단일 FastAPI 애플리케이션으로 배포된다.
    *   **근거(인용)**:
        *   `backend/app/main.py`: `app.include_router(...)` 호출 목록
        *   `docs/02_architecture_volume.md`: "Business Layer (Cloud Run: metriclens-backend, FastAPI)" 아래 Controller, Service, Core, Repository가 모두 포함됨을 명시하는 다이어그램.
    *   **왜 문제**: 마이크로서비스 지향 아키텍처를 추구하면서도 실제 배포 단위는 단일 거대 서비스(monolithic service)에 가깝다. 예측(CPU 집약적)이나 GCP 통합(외부 API 호출)과 같은 특정 기능에 높은 부하가 걸리거나 오류가 발생할 경우, 이는 전체 백엔드 서비스의 성능 저하 또는 장애로 이어질 수 있다. 장애 격리가 제대로 이루어지지 않아 전체 시스템의 가용성이 떨어진다.
    *   **어떤 조건에서 드러나는가**:
        *   동시에 여러 호스트에 대한 예측 요청이 쇄도하여 CPU 집약적인 `forecaster` 코드가 병목이 될 때.
        *   GCP API 호출에 지연이 발생하거나 오류가 발생하여 `routes_gcp` 엔드포인트가 응답하지 못할 때.
        *   예측/최적화 로직의 버그가 발생하여 서비스 전체가 다운될 때.

*   **[심각도: 중간] 마이그레이션 전략의 부재 및 자동 시딩의 제한적 사용**
    *   **무엇이**: `scripts/schema.sql`은 `CREATE TABLE IF NOT EXISTS`를 사용하여 멱등성을 보장하며, `scripts/generate_test_data.sh` 스크립트는 `ON CONFLICT (id) DO NOTHING`을 통해 시드 데이터의 멱등성을 보장한다. 하지만 `docs` 폴더 내에 데이터베이스 스키마 변경 이력(마이그레이션)을 관리하는 방법에 대한 문서는 부재하다.
    *   **근거(인용)**:
        *   `scripts/schema.sql`: `CREATE TABLE IF NOT EXISTS hosts (...)`
        *   `scripts/generate_test_data.sh`: `INSERT INTO hosts (...) ON CONFLICT (id) DO NOTHING;`
        *   `docs/01_functional_spec.md`: "NFR-03 멱등 시드/DDL" 항목.
    *   **왜 문제**: 스키마와 시딩의 멱등성은 초기 배포와 테스트에는 유리하지만, 운영 환경에서 스키마가 변경될 때마다 수동으로 DDL을 작성하고 적용해야 하는 위험이 있다. Flyway, Alembic, Liquibase와 같은 데이터베이스 마이그레이션 도구의 부재는 장기적인 유지보수와 안정적인 배포에 기술 부채로 작용한다. `main.py`에서 `create_schema()`를 `lifespan` 단계에서 호출하는 방식은 `Base.metadata.create_all`을 사용하므로 프로덕션 환경에서 스키마 변경 시 데이터 손실을 야기할 위험이 있다.
    *   **어떤 조건에서 드러나는가**:
        *   새로운 기능 추가로 인해 기존 테이블에 컬럼이 추가되거나 변경될 때.
        *   스키마 변경 후 롤백이 필요할 때 마이그레이션 이력이 없어 복구 과정이 복잡해질 때.
        *   `create_schema()`를 운영 환경에서 오작동하여 기존 데이터를 삭제할 때.

## 3. 암묵적 가정과 그 취약성

*   **데모 환경의 SQLite가 운영 환경의 PostgreSQL과 동일하게 작동할 것이라는 가정**: 개발 및 테스트 과정에서 SQLite의 동작 방식이 PostgreSQL과 동일하다는 암묵적인 가정을 한다. 이는 `ON CONFLICT` 동작 방식, 트랜잭션 격리 수준, 자료형 처리 등에서 차이가 발생할 때 깨질 수 있다. 특히 성능 테스트나 부하 테스트 시 SQLite 환경의 결과가 PostgreSQL 환경에 그대로 적용될 것이라는 가정은 위험하다.
*   **단일 백엔드 서비스가 충분한 가용성과 확장성을 제공할 것이라는 가정**: 모든 백엔드 기능이 하나의 서비스에 묶여 있으므로, 특정 기능의 부하 증가가 전체 서비스의 자원 부족을 야기하지 않을 것이라는 암묵적인 가정을 한다. Cloud Run의 자동 스케일링이 이를 어느 정도 완화하지만, CPU 바운드 예측 작업이나 I/O 바운드 DB/GCP 통합 작업이 동일한 인스턴스에서 경쟁할 때 병목이 발생할 수 있다.
*   **스키마의 변경이 빈번하지 않거나 수동 관리가 가능할 것이라는 가정**: 현재 마이그레이션 도구가 없다는 것은 스키마 변경이 드물거나, 발생하더라도 수동으로 DDL을 관리하는 것이 충분하다고 가정하는 것이다. 이는 프로젝트가 성장하고 기능이 복잡해질수록 깨지기 쉬운 가정이다.
*   **GCP 통합 기능이 느슨한 결합으로 구현되어 있다는 착각**: `backend/app/integrations/gcp.py`의 클라이언트 지연 로딩은 GCP 통합이 느슨하게 결합되어 있다는 인상을 주지만, 실제로는 `GcpSyncService`가 `HostRepository`, `MetricRepository`, `ActionRepository`를 직접 주입받고 있어 DB 계층과 강하게 결합되어 있다. 이는 `GcpSyncService`가 DB가 없는 환경에서 독립적으로 테스트되기 어렵다는 것을 의미한다.

## 4. 파급 효과

*   **데모-운영 이중 경로**:
    *   **다른 영역**: 데모 환경에서 발견되지 않은 버그가 운영 환경에서만 발생하여 디버깅이 어려워진다. 배포 프로세스 복잡성 증가.
    *   **전체 시스템**: 시스템의 신뢰성 저하. 개발-운영 환경 불일치로 인한 예기치 못한 다운타임 발생 가능성.
*   **형식적인 계층형 아키텍처**:
    *   **다른 영역**: 계층 간 관심사 분리 원칙 위반으로 코드 유지보수가 어려워지고, 특정 로직 변경 시 예상치 못한 다른 계층에 영향이 미칠 수 있다.
    *   **전체 시스템**: 아키텍처의 견고함 저하. 확장이 어렵고 버그 발생 확률 증가.
*   **감사 추적 주장의 영속성 부족**:
    *   **다른 영역**: 활동 로그 기능의 신뢰성 상실. 사용자 인터페이스(`frontend/src/components/ActivityLog.jsx`)에서 표시되는 기록이 휘발성으로 변하여 UX 저하.
    *   **전체 시스템**: 핵심 차별점의 상실. 규제 준수 환경에서의 사용 불가. 시스템의 목적 중 하나가 훼손된다.
*   **단일 백엔드 서비스의 장애 격리 취약성**:
    *   **다른 영역**: CPU 집약적인 예측 기능이 I/O 바운드 API 호출이나 다른 비즈니스 로직에 영향을 미쳐 응답 지연을 야기할 수 있다. GCP API 호출 실패 시 전체 서비스 장애로 확산.
    *   **전체 시스템**: 단일 장애 지점(SPOF) 증가. 시스템 가용성 저하. 마이크로서비스 아키텍처의 이점 상실.
*   **마이그레이션 전략의 부재**:
    *   **다른 영역**: 스키마 변경 시 수동 작업으로 인한 오류 발생 가능성. 배포 파이프라인의 견고함 저하.
    *   **전체 시스템**: 장기적인 시스템 유지보수 비용 증가. 스키마 변경에 대한 두려움으로 인해 기술적 발전이 저해될 수 있다.

## 5. 개선 제안

1.  **데이터베이스 이중 경로 통합 및 마이그레이션 도구 도입**:
    *   **PostgreSQL을 표준 개발/운영 DB로 단일화**한다. SQLite는 순수 단위 테스트(DB 접근 없는 `core` 계층 테스트)에만 활용하고, 통합 테스트/개발 환경에서는 Docker Compose 등으로 PostgreSQL을 띄워 사용한다.
    *   **Alembic과 같은 Python 기반 마이그레이션 도구를 도입**하여 스키마 변경 이력을 코드 레벨로 관리하고, 배포 시점에 자동 적용되도록 `cloudbuild.yaml`에 통합한다.
    *   `docs/04_database_design.md`에 Alembic 사용법 및 마이그레이션 정책을 추가한다.
2.  **`Action` 테이블을 Cloud SQL에 영속 저장**:
    *   현재 `/tmp` SQLite에 저장되는 `Action` 테이블(`backend/app/models.py`)을 운영 환경의 Cloud SQL (PostgreSQL)에 저장하도록 변경한다. 이렇게 하면 "감사 추적"이라는 핵심 차별점이 실제로 구현되며, `docs/12_limitations.md`의 문제점 §5.1이 해결된다.
    *   **근거**: `docs/12_limitations.md` §5.1의 보완 방향: "Cloud SQL 또는 GCS/외부 영속 스토리지로 전환."
3.  **핵심 기능별 마이크로서비스 분리 (단계적)**:
    *   장기적으로는 예측 엔진, 최적화 엔진, GCP 통합 서비스 등을 독립적인 Cloud Run 서비스로 분리하여 배포한다. 초기에는 예측 엔진(`core/forecaster.py`)과 최적화 엔진(`core/optimizer.py`) 같이 CPU/메모리 집약적인 작업을 먼저 분리하여 단일 백엔드의 부하를 줄인다.
    *   API Gateway (예: API Gateway for Cloud Run, 또는 Nginx)를 도입하여 통합된 엔드포인트를 제공하고, 각 마이크로서비스로 요청을 라우팅한다.
4.  **계층형 아키텍처 원칙 강화 및 코드 검토**:
    *   `main.py`의 `lifespan`에서 스키마 생성 및 시딩 로직을 분리하여 `scripts/generate_test_data.sh` 또는 Alembic 마이그레이션 스크립트를 통해 독립적으로 실행되도록 한다.
    *   Service 계층이 Repository를 인자로 받는 방식을 유지하되, Service가 Repository의 추상화 인터페이스에만 의존하도록 하여 테스트 용이성 및 유연성을 확보한다.
5.  **관측 가능성 도구 도입**:
    *   구조화된 로깅(`python-json-logger`)을 도입하여 Cloud Logging에서 로그를 쉽게 분석할 수 있도록 한다.
    *   성능 모니터링(`OpenTelemetry` 등)을 추가하여 각 기능(예측, DB 쿼리, GCP API 호출)의 레이턴시와 리소스 사용량을 시각화하고 병목 지점을 빠르게 식별할 수 있도록 한다.

## 6. 타 관점과의 연결

*   **관점 #05 (data-representativeness)**: 데모-운영 DB 불일치는 `seed_demo_data`에서 생성되는 데이터의 대표성이 운영 환경에 얼마나 잘 반영되는지에 직접적인 영향을 미친다. 휘발성 데이터는 재현 가능성을 떨어뜨린다.
*   **관점 #07 (scalability)**: 단일 백엔드 서비스 구조는 확장성에 직접적인 한계를 부여하며, 특정 기능의 부하 증가가 전체 시스템의 병목을 야기할 수 있다.
*   **관점 #08 (realtime-ops)**: 단일 백엔드 서비스의 장애는 전체 운영에 영향을 미치며, 감시/운영 도구의 통합 부재는 실시간 대응 능력을 저하시킨다.
*   **관점 #10 (security-compliance)**: 감사 추적의 영속성 부족은 보안 및 규제 준수(예: GDPR, DORA) 요구 사항을 충족하지 못하게 하며, 인증/권한 부여 부재와 결합되어 심각한 보안 리스크를 초래한다.
*   **관점 #12 (gcp-integration)**: GCP 통합 기능이 백엔드 서비스 내에 강하게 결합되어 있어, GCP API 호출 관련 오류나 지연이 전체 서비스에 영향을 미칠 수 있다.
