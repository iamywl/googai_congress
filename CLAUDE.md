# CLAUDE.md — MetricLens AI 프로젝트 작업 지침

이 파일은 사용자(iamywl / yoonwoodev@gmail.com)의 요구사항을 정리한 것으로,
모든 작업은 아래 지침을 **최우선으로 준수**한다. 기본 동작보다 우선한다.

## 0. 응답 언어
- 사용자와의 모든 대화는 **한국어**로 한다.
- 기술 문서 본문/보고서도 한국어로 작성한다(코드 식별자·로그·API는 영어 유지).
- 글쓰기에서 **비유(metaphor)·유추(analogy)를 사용하지 않는다.** 직접적으로 기술한다.

## 1. 제품 정의
- **MetricLens AI**: 경량 시계열 모델로 서버 부하(CPU·메모리·네트워크)를 예측하고,
  정수계획법으로 SLO를 보장하는 최소 자원 구성을 산출하는 리사이징 최적화 플랫폼.
- 도메인은 **시계열 서버-부하 예측**이다. (이전 eBPF / users-projects-tasks 스캐폴드 아님)

## 2. 배포 / 인프라 (확정 사항)
- **GCP 네이티브: Cloud Run + Cloud Build** 로 배포한다.
  - Jenkins / GKE / App Engine 은 **사용하지 않는다** (스펙에 있어도 무시).
- GCP 프로젝트 `knudc-yoonwoodev`, 리전 `us-central1`.
- 비용 최소화를 위해 데모 백엔드는 **SQLite 자체내장 + 부팅 시 자동 시드**(scale-to-zero,
  유휴 ≈ $0). 프로덕션 경로는 Cloud SQL(PostgreSQL)을 지원하되 상시 띄우지 않는다.
- 모든 컨테이너는 **non-root**로 실행. 비밀값은 **env / Secret Manager**로 주입하고
  **절대 하드코딩하지 않는다**.
- 사용자가 브라우저에서 직접 테스트할 수 있도록 **공개(public) 배포**하고 라이브 URL을 제공한다.

## 3. 엔지니어링 규율
- **레이어드 아키텍처**: Controller → Service → Repository + 순수 Core(forecaster·optimizer).
  의존성은 아래로만 흐른다. Core는 DB 없이 단위 테스트 가능해야 한다.
- **공식 스타일 가이드** 준수. Python은 ruff(lint/정적분석), JS는 ESLint.
- **멱등성(idempotency)**: 시드·마이그레이션·생성 스크립트는 반복 실행해도 안전해야 한다.
- **변경마다 엄격 검증**: 코드 변경 후 매번 lint + 정적분석 + 단위테스트를 통과시킨다.
  실패는 숨기지 말고 그대로 보고하고 자동 교정한다.
- 핵심 기술 문서는 `./docs/`에 유지한다(기능명세·아키텍처·API·ERD·시퀀스·인프라·테스트 등).

## 4. UI / UX 요구
- 예측 실행 및 CPU/메모리 **스케일 업/다운을 시연하는 인터랙티브 버튼**을 제공한다.
- 리사이징을 **체감 가능**하게: 모든 과거 로그(예측·리사이즈·결과)를 **DB에 영속 저장**하고
  화면에 표시한다. "무엇을 얼마나 줄였는지"가 명확해야 한다(활동 로그/감사 추적).
- **GCP에서 사용 가능한 인스턴스 타입(CPU·RAM)을 UI에 반영**한다(머신 타입 선택/표시).
- 각 지표(아이콘)에 **`i` 정보 아이콘**을 두어 해당 지표의 의미를 설명한다.
- UI는 **정돈되고 반응형(responsive)**이어야 한다.
- **시스템 아키텍처 그림은 공식 오픈소스 아이콘/이미지**(예: Simple Icons, 공식 브랜드 로고)를
  활용해 그림자료로 만든다. 생성 스크립트: `scripts/build_architecture_diagram.py`.

## 5. 데이터 / 시험의 대표성
- 시험 데이터·시나리오는 **통계적으로 대표성**을 가져야 하며, **근거 자료(출처)**를 갖춘다.
  근거가 없으면 **조사**하여 실측 통계에 정렬한다.
- 현재 근거: Azure Resource Central(SOSP'17), Barroso & Hölzle, Alibaba 2018 트레이스.
  → `docs/09_workload_modeling.md`, 생성기 `backend/app/core/workload.py`,
  검증 `backend/tests/test_workload.py`.

## 6. 보고서
- 개발 보고서는 **USENIX 양식**(`usenix2022.docx` 템플릿)으로 생성한다.
- 보고서 본문은 **한국어**로 작성한다. 생성 스크립트: `scripts/build_report_docx.py`.
- 아키텍처 설명에는 위 공식 아이콘 다이어그램을 포함한다.

## 7. 시장 차별화
- 경쟁 제품을 조사하고 차별점을 도출해 문서에 반영한다.
  → `docs/08_competitive_analysis.md`. 핵심 차별점: 에어갭/온프레 자립형, GPU-프리 경량,
  SLO 제약 처방적 정수계획 최적화, 화이트박스 설명가능성, 감사 추적.

## 8. Git / 협업
- `git config --global user.name "iamywl"`.
- 리모트: `git@github.com:iamywl/googai_congress.git` (**SSH** 인증, 브랜치 `main`).
- 저장소 루트가 홈 디렉토리이므로 **화이트리스트 `.gitignore`**로 프로젝트 파일만 추적한다
  (`.ssh`/`.bash_history`/`.claude.json`/credential 등은 절대 커밋 금지).
- 커밋·푸시는 사용자가 요청할 때 수행한다.

## 9. 빠른 검증 명령
```bash
# 백엔드 게이트 (ruff + pytest)
cd backend && source .venv/bin/activate && ruff check app tests && python -m pytest -q
# 프론트엔드 게이트 (eslint + build)
cd frontend && npx eslint src --max-warnings=0 && npm run build
# 산출물 재생성
python scripts/build_architecture_diagram.py     # 아키텍처 다이어그램
python scripts/build_report_docx.py <FRONTEND_URL> <BACKEND_URL>   # USENIX 보고서(.docx)
```
