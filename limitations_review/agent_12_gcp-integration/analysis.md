# MetricLens 한계점 분석 #12 — gcp-integration

- 생성: 20260603-1530
- 모델: gemini-2.5-flash (Vertex AI / knudc-yoonwoodev/us-central1)
- 관점: GCP 통합의 한계. Cloud Monitoring 시간단위 정렬 지연(실측 1pt/h, 풀 사이클 ~24h), 메모리 미관측을 CPU 연동 프록시로 대체, e2 shared-core 이용률 100% 포화, Ops Agent 의존, API 레이트리밋·권한 전파를 분석한다.
- 입력 코퍼스: /home/ywlee/metriclens/limitations_review/_input/context.md (9648 줄)

---

## 0. 관점 메모
이 분석 렌즈는 MetricLens AI 프로젝트가 GCP 서비스(Cloud Monitoring, Compute Engine)와 연동되는 방식의 한계에 집중한다. 특히 메트릭 데이터 수집의 granularity, 메모리 지표의 신뢰성, GCP 인스턴스 유형별 특성, 그리고 API 호출의 안정성 및 권한 관리 측면에서의 잠재적 문제를 검토한다.

## 1. 핵심 한계 요약
*   **낮은 Cloud Monitoring 데이터 해상도**: 시간 단위 데이터 수집으로 미세한 부하 변동 예측이 어렵고, 모델 학습에 필요한 이력 확보에 지연이 발생한다.
*   **메모리 지표의 프록시 의존성**: Ops Agent 미설치 시 CPU 기반 추정치를 사용하며, 이는 메모리 최적화 권장안의 신뢰도를 저하시킨다.
*   **e2 shared-core 인스턴스 이용률 포화**: e2 인스턴스 특성상 CPU 이용률이 100%로 보고되어도 실제 부하가 더 높을 수 있어 예측 및 최적화 정확성을 저해한다.
*   **GCP API 연동의 견고성 부족**: API 레이트리밋 및 권한 전파 지연에 대한 명시적 처리 로직이 미비하여 운영 안정성을 위협한다.
*   **"에어갭/온프레" 주장과 GCP 종속성 간의 모순**: 핵심 차별점과 실제 GCP 서비스 연동 사이에 개념적 불일치가 존재한다.

## 2. 상세 분석
### 2.1 Cloud Monitoring 시간 단위(hourly) 데이터 수집의 한계
*   **심각도**: 높음
*   **무엇이**: Cloud Monitoring에서 인스턴스의 CPU 사용률 데이터를 시간 단위(align_minutes=60)로 가져오며, 이로 인해 지표의 세밀한 변동을 놓칠 수 있다. 예측 모델의 주기(seasonal_period=24)를 학습하기 위해 최소 2일 이상의 데이터가 필요하므로, 신규 인스턴스의 콜드스타트 시 예측/권장까지 시간이 오래 걸린다.
*   **근거(인용)**: `backend/app/config.py`의 `sample_interval_minutes: int = 60`. `backend/app/integrations/gcp.py`의 `fetch_cpu_series` 및 `fetch_mem_series` 함수 시그니처에 `align_minutes: int = 60`이 기본값으로 명시되어 있다. `docs/12_limitations.md`의 "4. 실제 GCP 통합 (데모 수준)" 항목에서 "수집 해상도: Cloud Monitoring 시간 정렬로 시간당 1포인트, 전체 일주기 확보에 ~24h, period=24 백테스트엔 2일 이상 필요 → 콜드스타트 공백."
*   **왜 문제**: 시간당 1포인트의 데이터는 단기적인 부하 스파이크나 급격한 변화를 포착하기 어렵다. 이는 예측 모델의 정확도를 저해하고, 특히 부하 예측에 높은 민감도가 요구되는 상황에서 최적의 리사이징 권장을 어렵게 만든다. 또한, 신규 인스턴스에 대한 빠른 최적화 적용을 지연시킨다.
*   **어떤 조건에서 드러나는가**: 짧은 주기로 트래픽 변동이 심한 웹/API 서비스, 혹은 신규 배포된 인스턴스가 즉시 최적화되어야 하는 환경에서 예측의 적시성과 정확성 문제가 심화된다.

### 2.2 메모리 지표의 프록시 사용 및 Ops Agent 의존성
*   **심각도**: 높음
*   **무엇이**: GCP 인스턴스의 메모리 사용률(`agent.googleapis.com/memory/percent_used`)은 Cloud Monitoring의 Ops Agent를 통해 수집된다. Ops Agent가 설치되지 않았거나 데이터를 보고하지 않는 경우, MetricLens는 CPU 사용률에 연동된 추정값(`cpu * 0.6 + 20.0`)을 메모리 사용률로 대신 사용한다.
*   **근거(인용)**: `backend/app/integrations/gcp.py`의 `fetch_mem_series` 함수 주석 "Returns an empty list if the agent metric is not present yet (no agent / not enough history), so callers fall back to a proxy." `backend/app/services_gcp.py`의 `sync` 함수 내 "if real_mem is not None: ... else: mem = max(0.0, min(95.0, round(cpu * 0.6 + 20.0, 2)))" 코드. `docs/12_limitations.md`의 "메모리 미측정 프록시: Ops Agent 없이 CPU 연동 추정값으로 저장한다. 메모리 최적화 입력의 신뢰도가 낮다."
*   **왜 문제**: 메모리 사용 패턴이 CPU 사용 패턴과 독립적인 워크로드(예: 캐시 서버)의 경우, CPU 기반의 프록시 메모리 값은 실제 메모리 부하를 왜곡하여 메모리 최적화 권장안의 신뢰도를 떨어뜨린다. Ops Agent 설치 및 지속적인 운영에 대한 의존성은 추가적인 관리 오버헤드와 실패 지점을 발생시킨다. `scripts/gcp_demo/startup.sh`에서 Ops Agent 설치 실패 시 스크립트가 `|| true`로 에러를 무시하는 것은 이러한 의존성의 취약점을 보여준다.
*   **어떤 조건에서 드러나는가**: 메모리 바운드 워크로드, 또는 메모리 사용량이 CPU와 무관하게 변동하는 애플리케이션에서 잘못된 최적화 권장으로 인해 성능 저하 또는 불필요한 비용이 발생할 수 있다.

### 2.3 e2 shared-core 인스턴스 CPU 이용률 포화 및 클램핑
*   **심각도**: 중간
*   **무엇이**: `e2` shared-core 인스턴스는 100% CPU 이용률에 도달하면 실제 부하가 더 높더라도 그 이상을 보고하지 않는 특성이 있다. MetricLens는 수집된 CPU 사용률을 `max(0.0, min(100.0, cpu))`로 클램핑하며, 데모 환경에서는 CPU 로드 생성기가 `e2` 인스턴스가 포화되지 않도록 `min(1.0, (2.0 * target_utilisation()) / 100.0)`와 같이 인위적으로 부하를 억제한다.
*   **근거(인용)**: `docs/12_limitations.md`의 "부하의 대표성: 실제 호스트 4대는 e2-small 부하 생성기이지 프로덕션 워크로드가 아니다. e2 공유코어는 100%로 포화돼 부하 생성을 인위적으로 억제한다." `backend/app/services_gcp.py`의 `sync` 함수 내 "cpu = max(0.0, min(100.0, cpu))" 코드. `scripts/gcp_demo/startup.sh`의 `target_utilisation()` 및 `main()` 함수 로직.
*   **왜 문제**: 실제 워크로드의 잠재적 CPU 요구량을 과소평가하여, 예측 모델이 실제보다 낮은 CPU 사용률을 학습하고, 이는 공격적인 다운사이징 권장으로 이어져 서비스 가용성에 악영향을 줄 수 있다. 데모 환경에서의 인위적인 억제는 실제 운영 환경에서 발생할 수 있는 문제를 가린다.
*   **어떤 조건에서 드러나는가**: 갑작스러운 부하 스파이크가 발생하는 e2 shared-core 인스턴스, 또는 burstable CPU 크레딧이 소진된 상황에서 실제 필요한 자원을 제대로 예측하지 못할 수 있다.

### 2.4 GCP API 레이트리밋 및 권한 전파 미고려
*   **심각도**: 중간
*   **무엇이**: Cloud Monitoring (`list_time_series`) 및 Compute Engine (`stop`, `set_machine_type`, `start`, `create_instance`, `delete_instance`) API 호출 시 잠재적인 API 레이트리밋이나 IAM 권한 전파 지연에 대한 명시적인 재시도/대기 로직이 없다. API 호출 실패 시 `gcp.GcpError`를 발생시키고 503 HTTP 오류로 처리한다.
*   **근거(인용)**: `backend/app/integrations/gcp.py` 내 모든 GCP API 호출(`client.aggregated_list`, `client.list_time_series`, `client.stop().result()`, `client.set_machine_type().result()`, `client.start().result()`, `client.insert().result()`, `client.delete().result()`). `backend/app/api/routes_gcp.py`에서 `gcp.GcpError` 발생 시 `HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))`로 응답.
*   **왜 문제**: 대규모 GCP 플릿을 동기화하거나 여러 인스턴스를 동시에 리사이즈하는 경우, API 요청 수 초과로 레이트리밋에 걸리거나, IAM 권한 변경 사항이 즉시 적용되지 않아 작업이 실패할 수 있다. 이는 MetricLens의 운영 안정성과 신뢰성을 저해하고, 실패한 작업을 수동으로 복구해야 하는 상황을 초래한다. 특히 `resize_instance`는 3단계 작업이므로 중간 실패 시 인스턴스가 멈춘 상태로 남을 수 있다.
*   **어떤 조건에서 드러나는가**: 수십 개 이상의 GCE 인스턴스를 관리하는 대규모 환경, 또는 짧은 시간 내에 여러 리사이징 작업이 요청되는 경우, IAM 정책 변경 후 즉시 관련 API를 호출하는 경우.

## 3. 암묵적 가정과 그 취약성
*   **GCP API는 항상 지연 없이 응답하며 레이트리밋은 발생하지 않는다는 가정**: `integrations/gcp.py`의 `resize_instance`와 같은 로직은 GCP API 호출이 항상 즉시 성공하고 완료된다고 가정한다. 그러나 실제 API는 네트워크 지연, 서비스 부하, 레이트리밋 등으로 인해 실패하거나 지연될 수 있다.
*   **Cloud Run 서비스 계정이 필요한 GCP 리소스에 대한 모든 권한을 항상 가지고 있다는 가정**: Compute Engine 인스턴스 나열/시작/중지/변경, Cloud Monitoring 지표 조회 등에 필요한 IAM 권한이 항상 적절하게 부여되어 있으며 변경되지 않는다고 가정한다. 권한 부족이나 변경 시 GCP 연동 기능이 마비될 수 있다.
*   **모든 GCE 인스턴스에 Ops Agent가 정상적으로 설치되어 메모리 지표를 제공한다는 가정**: Ops Agent가 없거나 작동하지 않으면 메모리 지표의 신뢰성이 저하됨에도 불구하고, 메모리 최적화가 유효하다고 가정한다.

## 4. 파급 효과
*   **예측 및 최적화의 정확도 저하**: 불충분하고 신뢰성이 떨어지는 메트릭 데이터(특히 낮은 해상도의 CPU, 프록시 메모리)는 예측 모델의 학습에 부정적인 영향을 미쳐, 전반적인 예측 및 리사이징 권장의 정확도를 떨어뜨린다.
*   **운영 안정성 및 서비스 가용성 위협**: GCP API 연동 실패(레이트리밋, 권한 문제 등)로 인해 인스턴스 동기화 및 리사이징 작업이 원활히 수행되지 않으면, 인스턴스가 예상치 못한 상태로 남아 서비스 가용성에 심각한 영향을 미칠 수 있다. 특히 `resize_instance`의 다단계 작업은 잠재적인 서비스 중단 시간을 증가시킨다.
*   **"에어갭/온프레 자립형" 핵심 차별점의 희석**: `docs/08_competitive_analysis.md`에서 MetricLens의 핵심 차별점으로 "에어갭/온프레 자립형"을 강조하지만, 실제 GCP 통합 기능은 Cloud Monitoring 및 Compute Engine에 대한 강한 외부 의존성을 내포한다. 이는 주장의 일관성을 훼손한다.

## 5. 개선 제안
1.  **Cloud Monitoring 데이터 수집 해상도 유연화**: `settings.sample_interval_minutes`를 60분보다 짧게 (예: 5분 또는 1분) 설정할 수 있도록 하고, 예측 모델이 이러한 고해상도 데이터를 활용할 수 있도록 개선. (단, Cloud Monitoring API 비용 및 레이트리밋 증가 가능성 고려).
2.  **메모리 지표 수집의 견고성 강화**:
    *   Ops Agent 설치 실패 시 명확한 경고 또는 알림 기능을 추가하여 운영자가 문제를 인지하도록 한다.
    *   메모리 프록시 로직을 더욱 정교하게 만들거나, Ops Agent 없이도 메모리 사용률을 추정할 수 있는 다른 방법을 탐색한다 (예: `system.memory.usage` 같은 기본 제공 지표 활용).
3.  **GCP API 연동 로직 강화**:
    *   **지수 백오프 재시도**: `integrations/gcp.py`의 모든 GCP API 호출에 대해 지수 백오프(exponential backoff)를 포함한 재시도 로직을 구현하여 일시적인 네트워크 문제나 레이트리밋에 강건하게 대응.
    *   **IAM 권한 사전 검증**: `sync` 또는 `real_resize`와 같은 민감한 작업을 수행하기 전에 Cloud Run 서비스 계정이 필요한 Compute Engine 및 Cloud Monitoring IAM 권한을 가지고 있는지 사전 검증하는 로직을 추가하여 명확한 오류 메시지를 제공.
4.  **e2 shared-core 인스턴스 특성 명확화**: `docs/12_limitations.md`에 명시된 e2 shared-core의 CPU 이용률 포화 문제를 사용자에게 명확히 고지하고, 해당 인스턴스 유형에 대한 최적화 권장 로직을 보수적으로 조정하거나 다른 인스턴스 유형(N2, C2 등)을 권장하는 방안을 고려.

## 6. 타 관점과의 연결
*   **예측 모델의 표현력 한계 (#01)**: Cloud Monitoring의 낮은 데이터 해상도는 예측 모델이 학습할 수 있는 시계열 패턴의 복잡성을 제한하고, 미세한 변동을 놓치게 하여 모델의 표현력 한계와 직결된다.
*   **데이터 대표성의 한계 (#05)**: 메모리 프록시 사용과 e2 shared-core의 특성은 GCP에서 수집되는 실측 데이터의 대표성을 왜곡시켜, 합성 워크로드 기반의 모델 학습 결과가 실제 GCP 환경에 일반화되기 어렵게 만든다.
*   **실시간성·운영의 한계 (#08)**: Cloud Monitoring 데이터 수집 지연은 '실시간' 최적화라는 목표에 직접적인 영향을 미치며, GCP API 호출 실패로 인한 리사이징 중단 위험은 운영 시 서비스 중단을 야기할 수 있다.
*   **보안·규제·자립성의 한계 (#10)**: GCP 연동에 필요한 서비스 계정 권한 관리는 보안 규정 준수 및 시스템의 자립성 주장과 밀접하게 관련된다. 특히 `real_resize`와 같은 작업의 권한 제어는 보안 취약점과 직결될 수 있다.
