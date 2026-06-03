#!/usr/bin/env python3
"""MetricLens AI 개발 보고서를 USENIX .docx 양식(한국어)으로 생성한다.

usenix2022.docx 템플릿을 열어 제목/저자 줄을 제자리에서 교체(서식 유지)하고,
플레이스홀더 본문을 비운 뒤 템플릿의 ``Header 1`` / ``Header 2`` / ``Body``
스타일로 한국어 보고서를 다시 구성한다. 아키텍처 다이어그램과 모델 평가 그림
(scripts/build_architecture_diagram.py, scripts/evaluate_model_paper.py 생성물)을
삽입한다. 한국어 글리프 렌더링을 위해 East Asian 폰트(Malgun Gothic)를 지정한다.

사용법:
    python scripts/evaluate_model_paper.py          # 평가 그림 먼저 생성
    python scripts/build_architecture_diagram.py    # 아키텍처 그림
    python scripts/build_report_docx.py [FRONTEND_URL] [BACKEND_URL]
"""

from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "usenix2022.docx"
ARCH = ROOT / "docs" / "diagrams" / "architecture.png"
RUNTIME = ROOT / "docs" / "diagrams" / "runtime.png"
APPROACH = ROOT / "docs" / "diagrams" / "approach.png"
EVAL = ROOT / "docs" / "evaluation"
OUT = ROOT / "docs" / "development_report_usenix.docx"

FRONTEND_URL = sys.argv[1] if len(sys.argv) > 1 else "(배포된 Cloud Run URL)"
BACKEND_URL = sys.argv[2] if len(sys.argv) > 2 else "(배포된 Cloud Run URL)"

_KFONT = "Malgun Gothic"


def _apply_korean_font(p):
    for r in p.runs:
        rpr = r._element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = rpr.makeelement(qn("w:rFonts"), {})
            rpr.insert(0, rfonts)
        rfonts.set(qn("w:eastAsia"), _KFONT)


def set_text(p, text):
    for r in list(p.runs):
        r.text = ""
    if p.runs:
        p.runs[0].text = text
    else:
        p.add_run(text)
    _apply_korean_font(p)


def delete(p):
    p._element.getparent().remove(p._element)


def build():
    doc = Document(str(TEMPLATE))
    paras = doc.paragraphs

    set_text(paras[0], (
        "MetricLens AI: 온프레미스 서버 최적화를 위한 경량 시계열 예측과 "
        "정수계획 기반 리사이징"
    ))
    set_text(paras[1], "이용원 (팀장), 서한녕, 송심우")
    set_text(paras[2], "Team 구글링 — googai_congress")

    for p in paras[3:]:
        delete(p)

    def H1(t):
        _apply_korean_font(doc.add_paragraph(t, style="Header 1"))

    def H2(t):
        _apply_korean_font(doc.add_paragraph(t, style="Header 2"))

    def B(t):
        _apply_korean_font(doc.add_paragraph(t, style="Body"))

    def IMG(path: Path, caption: str, width: float = 3.3):
        if path.exists():
            doc.add_picture(str(path), width=Inches(width))
            _apply_korean_font(doc.add_paragraph(caption, style="Body"))

    # ---------------------------------------------------------------- Abstract
    H1("초록 (Abstract)")
    B(
        "온프레미스 인프라는 과프로비저닝이 만연해 운영비와 전력을 낭비한다. "
        "MetricLens AI는 다차원 서버 메트릭(CPU·메모리·네트워크)을 적재하고, GPU 없이 "
        "CPU만으로 구동되는 경량 시계열 모델로 부하를 예측하며, 정수계획법으로 SLO를 "
        "보장하는 최소 자원 구성을 산출하는 자립형 웹 플랫폼이다. 예측기는 계절-추세 "
        "분해에 AR(1) 잔차 보정을 결합하고, 예측 구간을 표본 외 백테스트 오차로 "
        "산정한다. 리사이징 엔진은 유계 탐색 공간에서 정확한 정수계획을 푼다. 시스템은 "
        "Cloud Build CI/CD로 Cloud Run에 GCP 네이티브 배포되며, Cloud Monitoring으로 "
        "실제 Compute Engine 인스턴스의 메트릭을 적재하고 예산 한도 내에서 실제 VM을 "
        "리사이즈한다. 공개 데이터센터 트레이스(Azure·Alibaba)에 근거한 대표 데이터에서, "
        "모델은 6개 워크로드 아키타입 모두에서 seasonal-naive 기준선을 RMSE로 능가하고 "
        "(5/6에서 두 기준선 모두 능가, Diebold-Mariano p<0.05 4/6), 95% 예측구간 "
        "커버리지는 0.93–0.98로 잘 보정된다."
    )

    # ------------------------------------------------------------ 1. 서론
    H1("1. 서론")
    B(
        "보수적 용량 산정은 서버를 만성적으로 유휴 상태로 둔다(Azure 트레이스: VM의 "
        "60%가 평균 CPU 20% 미만). 퍼블릭 클라우드 최적화 도구는 망분리·규제 온프레미스 "
        "환경에서 쓸 수 없어, 운영자는 데이터 기반 사이징 수단이 없다. MetricLens AI는 "
        "이 공백을 겨냥한 외부 의존성 없는 GPU-프리 시스템으로, 과거 텔레메트리를 "
        "정량적 라이트사이징 지침으로 전환한다."
    )
    B(
        "기여는 다음과 같다: (i) 자기상관을 활용하는 표준 라이브러리 계절-추세+AR 예측기; "
        "(ii) 백분위 피크 안전 통계를 갖춘 정확한 정수계획 리사이징 엔진; (iii) Cloud "
        "Monitoring 연동 실제 인스턴스 모니터링과 예산 가드 실제 리사이즈; (iv) 공개 "
        "트레이스에 근거한 통계적 대표성 데이터와 논문 수준의 모델 평가."
    )

    # --------------------------------------------------- 2. 시스템 아키텍처
    H1("2. 시스템 아키텍처")
    B(
        "시스템은 3계층 레이어드 아키텍처를 따른다. 표현 계층은 Canvas 기반 ECharts로 "
        "시계열을 렌더링하는 React 19 SPA(비특권 nginx 서빙)이고, 업무 계층은 Controller·"
        "Service·Repository로 분리된 단일 FastAPI이며 예측·최적화는 순수 Core에 격리된다. "
        "데이터 계층은 프로덕션 PostgreSQL(Cloud SQL), 데모 내장 SQLite이다."
    )
    IMG(ARCH, "그림 1. 공식 오픈소스 브랜드 로고로 구성한 시스템 아키텍처.")
    H2("2.1. 구동 방식 (어떤 아키텍처로 운영되는가)")
    B(
        "MetricLens는 GCP 네이티브 서버리스로 구동된다. 프론트엔드·백엔드는 각각 컨테이너 "
        "이미지로 빌드되어 Artifact Registry에 푸시되고 Cloud Run 서비스로 배포된다(요청이 "
        "없으면 0으로 스케일되어 유휴 비용이 거의 없다). 형상 변경은 Cloud Build 파이프라인이 "
        "린트→테스트→이미지 빌드→Cloud Run 배포→헬스 체크 순으로 수행한다. 백엔드는 런타임 "
        "서비스 계정의 기본 자격증명으로 Cloud Monitoring·Compute Engine API에 접근하여, "
        "`metriclens` 라벨이 붙은 실제 인스턴스의 CPU(에이전트 없이)와 메모리(Ops Agent)를 "
        "조회해 호스트로 적재하고, 권장 사양을 실제 머신 타입으로 변경(stop→setMachineType→"
        "start)할 수 있다. 비밀값은 Secret Manager에서 주입되며 하드코딩되지 않는다."
    )
    IMG(RUNTIME, "그림 2. 런타임·CI/CD 구동 방식: Cloud Build 파이프라인, 서버리스 "
                 "서빙, Cloud Monitoring 실측 적재·Compute Engine 실제 리사이즈.", width=6.2)

    # --------------------------------------------------- 3. 예측 엔진
    H1("3. 경량 예측 엔진")
    IMG(APPROACH, "그림 3. MetricLens 접근법(방법) 개요: 텔레메트리 → 분해+AR "
        "예측(95% 구간) → p95 피크 → SLO 제약 정수계획 → GCP 머신 타입 → 리사이즈.", width=6.5)
    H2("3.1. 계절-추세 분해와 AR 잔차 보정")
    B(
        "예측기는 시계열을 추세+계절+잔차의 가산합으로 모델링한다(y[t] = trend[t] + "
        "seasonal[t mod 24] + residual[t]). 추세는 주기별 블록 평균에 대한 최소제곱으로 "
        "추정하는데, 한 계절 주기 전체를 평균하면 주기 성분이 상쇄되어 추세 기울기로 "
        "누설되지 않는다(전역 OLS의 계절 누설 보정). 계절 지수는 위상(시간대)별 평균 "
        "탈추세 값을 0합으로 재중심화한다."
    )
    B(
        "결정론적 분해만으로는 최근의 변동을 놓친다. 실제 서버 CPU는 시간 간 강하게 "
        "자기상관되므로(측정된 시차-1 자기상관 0.5–0.9), 분해 예측에 AR(1) 잔차 보정을 "
        "더한다: ŷ = (trend + seasonal) + ρ^h · (직전 실측값 − 직전 적합값). 여기서 ρ는 "
        "잔차의 시차-1 자기상관(0–0.95로 한정), h는 예측 지평(시간)이다. 이 항은 "
        "직전값(naive) 예측의 강점과 계절 모델의 강점을 결합하여, 모델이 두 기준선을 "
        "모두 능가하게 만드는 핵심 요소다(§7)."
    )
    H2("3.2. 점예측과 95% 예측구간")
    B(
        "각 예측은 두 부분으로 구성된다: (i) 점예측치(가장 그럴듯한 미래값 한 점)와 "
        "(ii) 95% 예측구간(실제 미래값이 95% 확률로 들어갈 범위). 구간은 표본 내 잔차가 "
        "아니라 표본 외 1-스텝 백테스트 오차(RMSE)로 산정한다: "
        "[예측치 − 1.96·RMSE, 예측치 + 1.96·RMSE]. 표본 외 오차를 쓰는 이유는 짧고 "
        "과적합되기 쉬운 시계열에서 불확실성을 과소평가하지 않기 위함이다. 측정된 실측 "
        "커버리지(PICP)는 0.93–0.98로 공칭 95%와 거의 일치하여 구간이 잘 보정되어 있음을 "
        "보인다(그림 7). 점예측만 내놓는 블랙박스와 달리 '예측 X% ± 범위'를 그대로 노출해 "
        "운영자가 위험을 가늠하게 한다(화이트박스). 엔진은 Python 표준 라이브러리만 사용해 "
        "네이티브 의존성·GPU가 필요 없다."
    )

    # --------------------------------------------------- 4. 정수계획 리사이징
    H1("4. 정수계획 리사이징 및 실제 적용")
    H2("4.1. 강건 피크(p95)와 헤드룸 제약")
    B(
        "사이징의 기준이 되는 '피크'로 최댓값(max)이 아니라 95퍼센타일(p95)을 사용한다. "
        "최댓값은 단발 스파이크 한 점에 취약해, 어쩌다 튄 값 때문에 영구적 과프로비저닝을 "
        "유발한다. p95는 가장 극단적인 약 5%를 제외하므로 드문 일시적 급등이 사이징을 "
        "좌우하지 않는다 — 이것이 '강건(robust) 피크'다. 반대로 자주 반복되는 부하(예: 매일 "
        "같은 시간대의 배치 스파이크)는 발생 빈도가 5%를 넘어 p95에 포함되므로, 해당 "
        "호스트는 올바르게 축소되지 않고 유지된다(데모의 버스트 호스트 batch-etl-01이 0% "
        "유지된 이유)."
    )
    B(
        "엔진은 안전 마진을 유지하며 강건 피크 가동률을 목표 이하로 두는 최소 정수 할당을 "
        "선택한다: p95_peak × safety_margin ≤ target_utilisation × allocation. 여기서 "
        "safety_margin(예 1.2)은 예측 오차를 흡수하는 버퍼, target_utilisation(예 0.65)은 "
        "정상상태 가동률 상한이다. 탐색 공간이 작고 유계(vCPU∈[1,현재], 메모리 256MB "
        "블록)이므로 전수 열거로 정확 해를 구한다 — 외부 의존성 없는 정확 해법이며, vCPU와 "
        "메모리를 독립적으로 최적화한다(메모리 바운드 호스트는 CPU만 축소)."
    )
    H2("4.2. GCP 머신 타입 매핑과 예산 가드 실제 리사이즈")
    B(
        "추상적 (vcpu, memory) 권장값은 사전정의 GCP 인스턴스(E2/N2/C2/C3)로 스냅된다. "
        "실제 GCE 호스트는 Compute API로 머신 타입을 변경하여 물리적으로 리사이즈하되, "
        "월 비용이 한도(예: 300,000원/월)를 초과하는 타입은 거부하고, 보호 인스턴스 "
        "목록(작업 머신 등)은 변경 대상에서 제외한다."
    )

    # --------------------------------------------------- 5. 구현 및 배포
    H1("5. 구현 및 배포")
    B(
        "백엔드는 SQLAlchemy 2.0 async의 FastAPI, 프론트엔드는 Vite 빌드 React 19(nginx "
        "서빙)이며 둘 다 비루트 컨테이너로 Cloud Run에 배포된다. 대시보드는 상단 메뉴로 "
        "Dashboard / History(전체 메트릭·활동 로그 열람) / Test Scenarios(예측·최적화·"
        "실제 GCP 동기화·실제 리사이즈·모델 평가 실행)를 제공한다. 모든 예측·리사이즈는 "
        "감사 로그 테이블에 영속 기록된다. 실제 인스턴스 플릿은 다양한 일주기 부하 생성기를 "
        "구동하여 Cloud Monitoring에 대표적인 실측 신호를 남긴다."
    )
    B(f"라이브 대시보드: {FRONTEND_URL}")
    B(f"라이브 API (Swagger /docs): {BACKEND_URL}")

    # --------------------------------------------------- 6. 데이터 대표성
    H1("6. 시험 데이터의 통계적 대표성")
    B(
        "데모/시드 메트릭은 공개 트레이스의 실측 통계에 근거한다. Azure Resource "
        "Central(SOSP'17): VM 60%가 평균 CPU<20%, 대화형/지연무관 분류. Barroso & "
        "Hölzle: 서버는 대부분 10–50% 대역. Alibaba 2018: 배치 평균 29.3%, 서비스 7.4%. "
        "이에 6개 워크로드 아키타입을 14일×시간단위로 생성하되, 단순 반복 곡선이 아니라 "
        "AR(1) 자기상관·날짜별 진폭 변동·완만한 추세·이분산 잡음·희귀 이상치를 가산한다. "
        "생성 데이터의 변동계수(CV)는 0.28–1.11, 시차-1 자기상관은 0.5–0.9로 실측 분포와 "
        "일치한다(균일 합성 데이터의 CV≈0과 대조)."
    )

    # --------------------------------------------------- 7. 모델 평가 (논문 수준)
    H1("7. 모델 평가 (논문 수준)")
    B(
        "균일 데이터의 단일 MAPE는 모델 유효성을 입증하지 못한다. 따라서 확장 윈도우 "
        "1-스텝 백테스트로 두 표준 기준선(naive=직전값, seasonal-naive=한 주기 전 값)과 "
        "비교하고, 학술 표준 지표인 MASE(Hyndman & Koehler 2006), sMAPE, RMSE를 "
        "보고하며, 예측구간 보정도를 PICP(커버리지)·MPIW(폭)로 측정하고, Diebold-Mariano "
        "검정(1995)으로 예측 정확도 차이의 통계적 유의성을 평가한다."
    )
    B(
        "결과: 모델은 6/6 아키타입에서 seasonal-naive를 RMSE로 능가하고, 5/6에서 MASE<1"
        "(seasonal-naive 대비 우수), 4/6에서 Diebold-Mariano p<0.05로 유의하게 우수하다. "
        "예측구간 커버리지는 0.93–0.98(공칭 0.95)로 잘 보정된다. 저활용 워크로드(steady_"
        "cache·devtest)는 직전값 기준선이 매우 강해 유의성이 낮은데, 이는 평탄·준유휴 "
        "신호의 본질적 특성으로 정직하게 보고한다."
    )
    IMG(EVAL / "fig_forecast_overlay.png",
        "그림 4. 1-스텝 예측 vs 실측과 95% 예측구간(대화형·배치 아키타입).")
    IMG(EVAL / "fig_error_rmse.png",
        "그림 5. 예측 오차(RMSE): 모델 vs 기준선(낮을수록 우수).")
    IMG(EVAL / "fig_mase.png",
        "그림 6. MASE — 1 미만이면 seasonal-naive를 능가.")
    IMG(EVAL / "fig_coverage.png",
        "그림 7. 95% 예측구간 보정(PICP) — 공칭 0.95 대비.")
    IMG(EVAL / "fig_residual_acf.png",
        "그림 8. 잔차 자기상관 — 백색잡음 대역 내면 적합 양호.")

    # --------------------------------------------------- 8. 관련 연구
    H1("8. 관련 연구 및 차별화")
    B(
        "시장은 (a) 쿠버네티스/클라우드 SaaS 최적화기(CAST AI·Sedai·StormForge — 텔레메트리 "
        "외부 전송·K8s 전제), (b) CSP 추천기(AWS Compute Optimizer·Azure Advisor — 단일 "
        "클라우드·짧은 윈도우), (c) 온프레 모니터(SolarWinds·ManageEngine — 임계치 기반 "
        "서술적 리포팅)로 나뉜다. MetricLens는 그 사이의 공백을 차지한다: (1) 에어갭·자립형, "
        "(2) GPU-프리 경량, (3) SLO 제약 처방적 정수계획, (4) 화이트박스 설명가능성, "
        "(5) 인프라 비종속(일반 VM/베어메탈)."
    )

    # --------------------------------------------------- 9. 결론
    H1("9. 결론")
    B(
        "MetricLens AI는 정확한 CPU-온리 예측과 정수계획 리사이징을 의존성 없는 클라우드 "
        "네이티브 서비스로 제공하고, 실제 GCP 인스턴스를 모니터링·리사이즈하며, 모델 "
        "유효성을 논문 수준의 평가(기준선 대비·MASE·Diebold-Mariano·구간 보정)로 입증한다. "
        "수동적 텔레메트리를 정량적·SLO 인지 사이징 지침으로 전환함으로써, 온프레미스 "
        "인프라의 비용과 전력 낭비를 줄이는 실용적 경로를 제시한다."
    )

    doc.save(str(OUT))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
