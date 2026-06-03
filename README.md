# MetricLens AI

경량 시계열 모델 기반 서버 리소스 부하 예측 및 동적 리사이징 최적화 시스템.
GPU 없이 범용 CPU만으로 부하를 예측하고, 정수 계획법으로 SLO를 보장하는 최소
자원 구성을 산출하여 OPEX·전력 낭비를 줄인다. **GCP Cloud Run + Cloud Build**에
배포된다.

## Live Endpoints

> `scripts/deploy.sh deploy` 실행 후 발급되는 Cloud Run URL로 갱신.

- 대시보드(프론트엔드): _(배포 후 기입)_ — [frontend/README.md](frontend/README.md)
- API(백엔드): _(배포 후 기입)_, Swagger `/docs` — [backend/README.md](backend/README.md)

## 구성

| 영역 | 위치 | 스택 |
|---|---|---|
| 프론트엔드 | [frontend/](frontend/) | React 19 + Vite + ECharts, nginx(non-root) |
| 백엔드 | [backend/](backend/) | FastAPI 레이어드 + 순수 Core(예측·정수계획), SQLAlchemy async |
| DB 스키마/시드 | [scripts/](scripts/) | `schema.sql`, `generate_test_data.sh`(결정론·멱등) |
| CI/CD | [cloudbuild.yaml](cloudbuild.yaml), [scripts/deploy.sh](scripts/deploy.sh) | Cloud Build 9-스테이지 → Cloud Run |
| 기술 문서 | [docs/](docs/) | 기능명세·아키텍처·API·ERD·시퀀스·인프라·테스트·개발보고서 |

## 빠른 시작 (로컬)

```bash
# 백엔드 품질 게이트 (lint + 27 tests)
cd backend && python -m venv .venv && source .venv/bin/activate \
  && pip install -r requirements-dev.txt && cd .. && SKIP_FRONTEND=1 ./scripts/run_tests.sh

# 프론트엔드 (데모 데이터 폴백 내장)
cd frontend && npm install && npm run dev
```

## 배포

```bash
PROJECT_ID=knudc-yoonwoodev ./scripts/deploy.sh bootstrap
PROJECT_ID=knudc-yoonwoodev DATABASE_URL=postgresql://... ./scripts/deploy.sh migrate
PROJECT_ID=knudc-yoonwoodev \
  CLOUDSQL_INSTANCE=knudc-yoonwoodev:us-central1:metriclens-db ./scripts/deploy.sh deploy
```

자세한 설계·테스트·스크린샷은 [개발 완료 보고서](docs/development_report.md) 참조.
# googai_congress
# googai_congress
# googai_congress
