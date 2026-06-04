# MetricLens 한계점 분석 #10 — security-compliance

- 생성: 20260603-1530
- 모델: gemini-2.5-flash (Vertex AI / knudc-yoonwoodev/us-central1)
- 관점: 보안·규제·자립성의 한계. '에어갭/온프레 자립형' 주장과 실제 GCP(Cloud Run/Monitoring/Compute Engine) 종속의 모순, Compute Engine 실제 리사이즈 권한·감사·롤백, 예산 가드/denylist 우회 가능성, 비밀관리 경로를 분석한다.
- 입력 코퍼스: /home/ywlee/metriclens/limitations_review/_input/context.md (9648 줄)

---

## 0. 관점 메모
이 렌즈에서는 MetricLens AI 프로젝트가 내세우는 '에어갭/온프레 자립형'이라는 핵심 제품 정의와 실제 구현(GCP 의존성), 그리고 GCP 자원 제어(리사이즈) 및 비밀 관리에 대한 보안 및 규제 준수 관점의 한계점과 위험을 집중적으로 분석했습니다. 특히 인증 없는 공개 쓰기 API의 보안 취약성에 주목했습니다.

## 1. 핵심 한계 요약
1.  **치명적**: 핵심 제품 정의인 '에어갭/온프레 자립형' 주장과 실제 배포 및 운영이 GCP 클라우드 서비스에 깊이 종속되어 모순됩니다.
2.  **치명적**: 실제 GCP 리소스를 변경하는 쓰기 엔드포인트(VM 리사이즈 등)가 인증 없이 공개되어 있어 심각한 보안 취약점을 내포합니다.
3.  **높음**: VM 리사이즈 작업에 대한 상세 감사 기록, 승인 절차, 롤백 메커니즘이 미흡하여 운영 안정성 및 책임 추적성을 저해합니다.
4.  **높음**: 데모 환경(SQLite)에서의 감사 로그 영속성이 보장되지 않아 "감사 추적"이라는 핵심 차별점의 신뢰도가 낮습니다.
5.  **중간**: 예산 가드 및 보호 인스턴스 목록(denylist)이 제한적이거나 하드코딩되어 있어 우회될 가능성이 있습니다.

## 2. 상세 분석

*   **[심각도: 치명] '에어갭/온프레 자립형' 주장과 실제 GCP 종속의 모순**
    *   **무엇이**: 프로젝트 문서 (`CLAUDE.md`, `README.md`, `docs/08_competitive_analysis.md`) 전반에서 MetricLens AI의 핵심 차별점으로 "에어갭/온프레 자립형"을 내세우며 외부 API/SaaS 콜백이 없음을 강조합니다. 하지만 실제 아키텍처 (`cloudbuild.yaml`, `docs/06_infrastructure_layout.md`)는 백엔드가 GCP Cloud Run에 배포되고, Cloud Monitoring에서 메트릭을 가져오며, Compute Engine API를 통해 실제 VM을 리사이즈하는 등 GCP 클라우드 서비스에 깊이 의존하고 있습니다 (`backend/app/integrations/gcp.py`).
    *   **근거(인용)**:
        *   `CLAUDE.md`: "MetricLens AI... 온프레미스 환경에 최적화된 자립형 모델을 지향한다. 이는 외부 API 의존성 없이 내부 인프라만으로 자원 최적화를 실현하는 공학적 해결책을 제시하는 것이다." / "GCP 네이티브: Cloud Run + Cloud Build 로 배포한다."
        *   `README.md`: "폐쇄망/에어갭 자립형 — 외부 API·SaaS 콜백 0, 단일 컨테이너+내장 DB. 망분리(국방·금융·공공) 즉시 투입."
        *   `docs/06_infrastructure_layout.md`: "본 시스템은 GCP 관리형 서버리스 컨테이너 플랫폼(Cloud Run) 위에 배포된다... 영속성은 Cloud SQL for PostgreSQL이, 비밀 관리는 Secret Manager가 담당한다." 및 관련 다이어그램.
        *   `backend/app/integrations/gcp.py`: `google.cloud.compute_v1` 및 `google.cloud.monitoring_v3` 클라이언트를 사용.
    *   **왜 문제**: '에어갭/온프레 자립형'은 외부 네트워크와의 단절을 의미합니다. GCP 서비스에 의존하는 시스템은 에어갭 환경에서 동작할 수 없으며, 이는 핵심 제품 정의와의 직접적인 모순이자 고객에 대한 오해의 소지를 만듭니다. 망분리 환경의 고객은 GCP 서비스 접근이 불가능합니다.
    *   **어떤 조건에서 드러나는가**: 에어갭 또는 엄격한 온프레미스 환경에 시스템을 배포하려고 할 때, GCP 의존성으로 인해 배포가 불가능하거나 대대적인 아키텍처 변경이 필요할 때 이 문제가 드러납니다.

*   **[심각도: 치명] 인증 부재 및 공개된 쓰기 엔드포인트**
    *   **무엇이**: FastAPI 애플리케이션 (`backend/app/main.py`)이 모든 오리진(`allow_origins=["*"]`)에 대해 CORS를 허용하며, 어떠한 인증 메커니즘도 구현되어 있지 않습니다. 이 상태로 실제 GCP VM을 리사이즈하는 (`backend/app/api/routes_gcp.py`의 `/api/v1/gcp/hosts/{host_id}/resize`) 및 테스트 노드를 생성/삭제하는 (`/api/v1/gcp/testnode`) 엔드포인트가 외부로 공개되어 있습니다. 문서는 이를 "public, read-only demo API"라고 설명하지만, VM 리사이즈는 명백한 '쓰기' 작업입니다.
    *   **근거(인용)**:
        *   `backend/app/main.py`: `app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)`, "This is a public, read-only demo API; credentials are not used, so a permissive policy is acceptable."
        *   `backend/app/api/routes_gcp.py`: `@router.post("/hosts/{host_id}/resize", ...)` 및 `@router.post("/testnode", ...)` `@router.delete("/testnode", ...)` 엔드포인트.
        *   `backend/app/integrations/gcp.py`: `resize_instance`, `create_instance`, `delete_instance` 함수가 실제 GCP 리소스를 조작함.
    *   **왜 문제**: 인증되지 않은 모든 외부 주체가 공개된 API를 통해 GCP 인프라의 VM을 임의로 리사이즈하거나 생성/삭제할 수 있습니다. 이는 비용 폭탄, 서비스 중단, 데이터 손실 등 심각한 보안 사고로 이어질 수 있는 치명적인 취약점입니다. "read-only demo API"라는 설명은 쓰기 엔드포인트가 존재하는 현실과 모순됩니다.
    *   **어떤 조건에서 드러나는가**: 악의적인 공격자가 API 엔드포인트를 발견하고 호출하여 GCP 리소스를 조작하려고 시도할 때, 또는 우발적인 호출로 인해 예상치 못한 서비스 중단이나 비용 발생이 발생할 때 이 문제가 드러납니다.

*   **[심각도: 높음] VM 리사이즈 작업의 불충분한 감사, 승인, 롤백**
    *   **무엇이**: `/api/v1/gcp/hosts/{host_id}/resize` 엔드포인트를 통한 실제 VM 리사이즈는 `gcp.resize_instance` 호출을 통해 수행됩니다 (`backend/app/services_gcp.py`). 이 작업은 VM 정지, 머신 타입 변경, VM 시작의 3단계로 이루어져 다운타임을 유발합니다. `Action` 테이블에 감사 로그가 기록되지만 (`backend/app/models.py`), 리사이즈를 누가 요청했는지에 대한 사용자 정보나, 변경된 사양이 실제로 유효한지 검증하는 승인 절차, 실패 시 자동으로 이전 상태로 되돌리는 롤백 메커니즘이 없습니다.
    *   **근거(인용)**:
        *   `backend/app/integrations/gcp.py`: `resize_instance` 함수 구현.
        *   `backend/app/models.py`: `Action` 모델은 `host_id`, `action_type`, `detail` 등을 기록하지만, 요청자 정보는 없음.
        *   `docs/10_uml_models.md`: 7. 상태 머신 다이어그램 (Resizing → Stopping → Reconfiguring → Starting).
    *   **왜 문제**: 실제 인프라 변경 작업에 대한 상세한 감사 기록과 책임 추적성 부족은 규제 준수(컴플라이언스) 요구사항을 충족하기 어렵게 만듭니다. 또한, 승인 절차와 롤백 메커니즘이 없으면 운영자가 잘못된 리사이즈를 실수로 적용했을 때의 위험이 매우 크며, 서비스 중단 시간이 길어질 수 있습니다.
    *   **어떤 조건에서 드러나는가**: 서비스 중단이 발생하거나, 규제 감사 요구사항에 직면했을 때, 또는 잘못된 리사이즈가 적용되어 복구해야 할 때 이 문제가 드러납니다.

*   **[심각도: 높음] 데모 환경 감사 로그의 영속성 문제**
    *   **무엇이**: `docs/12_limitations.md`의 §5.1에 명시된 바와 같이, 데모 환경에서 SQLite DB는 `/tmp/metriclens.db`에 저장됩니다. Cloud Run 인스턴스는 scale-to-zero로 유휴 시 인스턴스가 종료되고, `/tmp` 디렉토리는 휘발성 저장소이므로 인스턴스가 재시작될 때마다 감사 기록이 유실됩니다.
    *   **근거(인용)**: `docs/12_limitations.md`: "DB가 `sqlite+aiosqlite:////tmp/metriclens.db` ([`backend/app/config.py`](../backend/app/config.py))이고 Cloud Run은 scale-to-zero다. `/tmp`는 인스턴스 휘발성이라 콜드스타트마다 기록이 소실·재시드된다."
    *   **왜 문제**: MetricLens의 핵심 차별점 중 하나가 "감사 추적" (`README.md`, `CLAUDE.md`)임에도 불구하고, 데모 환경에서는 이러한 기능이 제대로 작동하지 않아 사용자가 제품의 핵심 가치를 경험하기 어렵게 합니다. 프로덕션 환경에서는 Cloud SQL을 사용하겠지만, 데모/테스트 환경에서의 이러한 불일치는 제품의 신뢰성을 저하시킵니다.
    *   **어떤 조건에서 드러나는가**: Cloud Run 인스턴스가 재시작되거나 데모를 여러 번 실행할 때 과거 감사 기록이 사라지는 것을 발견할 때 이 문제가 드러납니다.

*   **[심각도: 중간] 예산 가드/denylist 우회 가능성**
    *   **무엇이**: 실제 VM 리사이즈 작업을 보호하기 위해 `monthly_budget_krw` (`backend/app/config.py`)를 초과하는 리사이즈를 거부하고, `gcp_protected_instances` (`backend/app/config.py`)에 나열된 VM은 리사이즈를 거부하는 메커니즘이 있습니다 (`backend/app/services_gcp.py`). 그러나 예산 가드는 `_MACHINE` 딕셔너리에 하드코딩된 머신 타입 정보 (`backend/app/integrations/gcp.py`)에만 의존하며, `_protected()` 목록은 문자열 기반입니다.
    *   **근거(인용)**:
        *   `backend/app/integrations/gcp.py`: `_MACHINE` 딕셔너리, `within_budget` 함수.
        *   `backend/app/config.py`: `monthly_budget_krw`, `gcp_protected_instances`.
        *   `backend/app/services_gcp.py`: `BudgetExceededError`, `NotARealHostError` (보호 인스턴스에 대한 예외).
    *   **왜 문제**: `_MACHINE` 딕셔너리에 없는 새로운 고비용 머신 타입이 GCP에 추가되거나, 수동으로 입력될 경우 예산 가드가 이를 인식하지 못하고 통과시킬 수 있습니다. 또한, `gcp_protected_instances`가 코드에 하드코딩되거나 환경 변수로 관리되더라도, 관리자가 목록을 최신 상태로 유지하지 않거나 실수로 보호 인스턴스를 누락할 경우 보호가 무력화될 수 있습니다.
    *   **어떤 조건에서 드러나는가**: GCP에 새로운 머신 타입이 추가되거나, `_MACHINE` 딕셔너리가 업데이트되지 않았을 때, 또는 `gcp_protected_instances` 목록에 없는 VM을 실수로 리사이즈했을 때 이 문제가 드러납니다.

## 3. 암묵적 가정과 그 취약성

*   **가정**: '공개 API + 예산/denylist 가드'만으로 실제 GCP 리소스 변경에 대한 보안이 충분하다는 가정.
    *   **취약성**: 이 가정은 인증 및 권한 부여가 부재한 상태에서 공개된 쓰기 엔드포인트가 외부 공격에 매우 취약하다는 점을 간과합니다. 예산 가드와 denylist는 추가적인 보호 계층일 뿐, 기본적인 접근 제어 없이는 핵심적인 보안 위협을 막을 수 없습니다.
*   **가정**: 데모 환경(SQLite)과 프로덕션 환경(Cloud SQL) 간의 동작 차이(예: 감사 로그 영속성)가 제품의 핵심 가치에 영향을 미치지 않는다는 가정.
    *   **취약성**: "감사 추적"이라는 핵심 차별점을 내세우면서 데모 환경에서 로그가 유실되는 것은 제품의 신뢰도를 저하시킵니다. 프로덕션 환경에서는 Cloud SQL을 사용하겠지만, 개발 및 테스트 단계에서의 불일치는 잠재적인 버그를 숨기거나 혼란을 야기할 수 있습니다.
*   **가정**: GCP 서비스 계정의 권한이 항상 적절하게 관리되며, 과도한 권한이 부여되지 않는다는 가정.
    *   **취약성**: `cloudbuild.yaml`에 `gcloud run services add-iam-policy-binding` 명령을 사용하여 `allUsers`에 `roles/run.invoker` 역할을 부여하고 있습니다. `backend/app/integrations/gcp.py`의 Compute Engine 및 Monitoring 클라이언트가 사용하는 서비스 계정의 권한이 과도하게 설정될 경우, 앞서 언급된 인증 부재 문제와 결합하여 더 큰 위험을 초래할 수 있습니다.

## 4. 파급 효과

*   **심각한 보안 침해 및 비용 발생**: 인증 없는 공개 쓰기 API는 임의의 외부 주체에 의한 GCP 리소스의 무단 변경, 삭제, 생성 등을 초래하여 통제 불가능한 비용 발생(리소스 스케일업)이나 서비스 중단(리소스 삭제/스케일다운)을 야기할 수 있습니다.
*   **규제 준수 실패**: 감사 로그의 불완전성, 리사이즈 작업에 대한 불충분한 책임 추적성은 금융, 공공 등 규제가 엄격한 산업 분야에서 요구하는 컴플라이언스 기준(예: ISO 27001, SOC 2)을 충족하지 못하게 할 수 있습니다.
*   **제품 신뢰도 및 시장 경쟁력 하락**: "에어갭/온프레 자립형"이라는 핵심 강점과 GCP 종속성 간의 모순, 그리고 실제 GCP 리소스에 대한 불안정한 통제는 제품의 신뢰도를 크게 훼손하고, 특히 보안을 중시하는 고객층에서의 시장 경쟁력을 약화시킬 것입니다.
*   **운영 리스크 증가**: 리사이즈 작업의 비가역성과 롤백 메커니즘의 부재는 운영팀이 변경 사항을 적용하는 데 주저하게 만들고, 문제가 발생했을 때 복구 시간을 지연시켜 서비스 가용성에 부정적인 영향을 미칩니다.

## 5. 개선 제안

1.  **쓰기 엔드포인트에 대한 인증 및 권한 부여 강화 (치명)**:
    *   `backend/app/main.py`의 `CORSMiddleware` `allow_origins`를 특정 화이트리스트 도메인으로 제한합니다.
    *   FastAPI의 보안 기능을 활용하여 `/api/v1/gcp/*` 및 `/api/v1/hosts/{host_id}/resize`와 같이 실제 리소스를 변경하는 모든 쓰기 엔드포인트에 인증(예: API 키, OAuth2 JWT 토큰) 및 권한 부여(RBAC)를 즉시 구현합니다.
2.  **감사 로그의 영속성 및 완전성 보장 (높음)**:
    *   데모 환경에서도 `Action` 테이블의 데이터를 휘발성 `/tmp` 대신 영속적인 스토리지(예: Docker Compose 환경에서 볼륨 마운트된 SQLite 파일 또는 로컬 PostgreSQL 인스턴스)에 저장하도록 `backend/app/config.py`의 `DATABASE_URL` 기본 설정을 변경합니다.
    *   `Action` 모델 (`backend/app/models.py`)에 `user_id` 또는 `requested_by` 필드를 추가하여 리사이즈 또는 예측을 트리거한 주체를 기록합니다.
3.  **GCP 통합 제어의 견고성 확보 (높음)**:
    *   GCP Compute Engine API를 통해 실시간으로 머신 타입 목록과 비용 정보를 조회하여 `backend/app/integrations/gcp.py`의 `_MACHINE` 딕셔너리를 동적으로 업데이트하고 예산 가드의 정확성을 높입니다.
    *   `gcp_protected_instances` 목록 (`backend/app/config.py`)을 환경 변수 대신 Secret Manager에서 로드하도록 하여 관리 편의성 및 보안을 강화합니다.
4.  **리사이즈 작업에 대한 승인 워크플로우 및 롤백 도입 (중간)**:
    *   `real_resize` 함수 (`backend/app/services_gcp.py`) 호출 전에 별도의 승인 단계(예: 관리자 승인)를 추가하는 기능을 고려합니다.
    *   리사이즈 실패 시 자동으로 이전 머신 타입으로 롤백하거나, 최소한 수동 롤백 절차를 문서화하고 구현을 위한 토대를 마련합니다.
5.  **제품 정의 및 문서의 명확화 (중간)**:
    *   `CLAUDE.md`, `README.md`, `docs/08_competitive_analysis.md` 등 문서에서 "에어갭/온프레 자립형"이라는 주장을 명확히 재정의합니다. 즉, '코어 예측/최적화 로직은 클라우드에 비종속적'임을 강조하되, '실제 클라우드 인프라 연동 기능은 해당 클라우드에 종속된다'는 점을 명확히 명시하여 모순을 해소합니다.

## 6. 타 관점과의 연결

*   **관점 #11 (architecture-debt)**: 데모 환경(SQLite)과 프로덕션 환경(Cloud SQL) 간의 DB 설정 및 동작 차이는 아키텍처 부채의 핵심적인 부분입니다. 감사 로그 영속성 문제는 이 관점에서 더 깊이 있게 다루어져야 합니다.
*   **관점 #14 (explainability-ux)**: 인프라 변경이라는 민감한 작업에 대한 보안, 인증, 감사, 롤백 메커니즘은 운영자가 리사이즈 결정을 신뢰하고 적용하는 데 필수적인 요소입니다. UX는 이러한 보안적 요구사항을 투명하게 반영해야 합니다.
*   **관점 #9 (cost-model)**: 예산 가드의 정확성 및 우회 가능성은 비용 모델의 한계와 직접적으로 연결됩니다. `_MACHINE` 딕셔너리의 정확성 및 동적 업데이트 필요성도 이 관점에서 추가적으로 분석될 수 있습니다.
*   **관점 #12 (gcp-integration)**: `gcp.py`의 GCP 클라이언트 권한 관리, API 레이트리밋, 그리고 메모리 메트릭 수집 방식 등 GCP 통합 자체의 기술적 한계와도 긴밀하게 연결됩니다.
