#!/usr/bin/env python3
"""MetricLens AI 개발 보고서를 USENIX .docx 양식(한국어)으로 생성한다.

usenix2022.docx 템플릿을 열어 제목/저자 줄을 제자리에서 교체(서식 유지)하고,
플레이스홀더 본문을 비운 뒤 템플릿의 ``Header 1`` / ``Header 2`` / ``Body``
스타일로 한국어 보고서를 다시 구성한다. 2단 레이아웃은 템플릿에서 상속된다.
한국어 글리프 렌더링을 위해 East Asian 폰트(Malgun Gothic)를 지정한다.

사용법:
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
SHOT = ROOT / "docs" / "screenshots" / "dashboard_overview.png"
OUT = ROOT / "docs" / "development_report_usenix.docx"

FRONTEND_URL = sys.argv[1] if len(sys.argv) > 1 else "(배포된 Cloud Run URL)"
BACKEND_URL = sys.argv[2] if len(sys.argv) > 2 else "(배포된 Cloud Run URL)"

_KFONT = "Malgun Gothic"


def _apply_korean_font(p):
    """문단 내 런에 East Asian 폰트를 지정해 한국어가 깨지지 않게 한다."""
    for r in p.runs:
        rpr = r._element.get_or_add_rPr()
        rfonts = rpr.find(qn("w:rFonts"))
        if rfonts is None:
            rfonts = rpr.makeelement(qn("w:rFonts"), {})
            rpr.insert(0, rfonts)
        rfonts.set(qn("w:eastAsia"), _KFONT)


def set_text(p, text):
    """문단 텍스트를 교체하되 문단 수준 서식은 유지한다."""
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

    # 제목 + 저자: 제자리 교체로 템플릿 서식 유지.
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

    H1("초록 (Abstract)")
    B(
        "온프레미스 인프라에서는 과프로비저닝이 만연하다. 운영자는 워크로드가 "
        "요구하는 것보다 훨씬 많은 자원을 할당하여 운영비(OPEX)와 전력을 낭비한다. "
        "MetricLens AI는 다차원 서버 메트릭(CPU·메모리·네트워크 I/O)을 적재하고, "
        "GPU 없이 CPU만으로 구동되는 경량 시계열 모델로 미래 부하를 예측하며, 정수 "
        "계획법으로 SLO를 보장하는 리사이징 권장안을 산출하는 자립형 웹 플랫폼이다. "
        "예측기는 계절 누설을 억제하는 블록 평균 추세 추정기를 사용한 가산 계절-추세 "
        "분해를 수행하고, 예측 구간을 표본 외 백테스트 오차로 산정한다. 리사이징 "
        "엔진은 유계 탐색 공간에서 정확한 정수계획을 푼다. 시스템은 Cloud Build "
        "CI/CD 파이프라인을 통해 Cloud Run에 GCP 네이티브로 배포된다. 공개 트레이스에 "
        "근거한 대표 데모 플릿에서 대화형 호스트의 MAPE는 9–13%로 15% 목표를 충족하며, "
        "최적화기는 99.9% SLO 신뢰도에서 최대 약 54%의 회수 가능 용량을 식별한다."
    )

    H1("1. 서론")
    B(
        "보수적인 용량 산정은 서버를 만성적으로 유휴 상태로 둔다. 퍼블릭 클라우드 "
        "최적화 도구는 망분리·규제 온프레미스 환경에서 사용할 수 없어, 운영자는 "
        "데이터 기반 사이징 수단을 갖지 못한다. MetricLens AI는 이 공백을 겨냥한다: "
        "외부 의존성이 없고 GPU가 필요 없는 시스템으로, 과거 텔레메트리를 정량적 "
        "라이트사이징 지침으로 전환한다(예: \"이 호스트는 16 vCPU의 26%에서 피크를 "
        "이루므로 절반으로 줄여도 99.9% 가용성을 유지한다\")."
    )
    B(
        "기여는 다음과 같다: (i) 단순 최소제곱의 계절 누설을 피하는 블록 평균 추세 "
        "추정기를 갖춘 표준 라이브러리 계절-추세 예측기; (ii) 백분위 피크 안전 통계를 "
        "갖춘 정확한 정수계획 리사이징 엔진; (iii) 레이어드 FastAPI 서비스와 "
        "React/ECharts 대시보드; (iv) 재현 가능한 Cloud Build → Cloud Run 배포; "
        "(v) 공개 데이터센터 트레이스에 근거하여 통계적 대표성을 갖춘 시험 데이터."
    )

    H1("2. 시스템 아키텍처")
    B(
        "시스템은 3계층 레이어드 아키텍처를 따른다. 표현 계층은 Canvas 기반 ECharts로 "
        "대용량 시계열을 렌더링하는 React 19 단일 페이지 애플리케이션으로, 비특권 "
        "nginx 컨테이너가 서빙한다. 업무 계층은 내부적으로 Controller·Service·"
        "Repository로 분리된 단일 FastAPI 애플리케이션이며, 예측·최적화 알고리즘은 "
        "순수하고 의존성 없는 Core에 격리된다. 데이터 계층은 프로덕션에서 "
        "PostgreSQL(Cloud SQL), 자립형 데모 프로파일에서 내장 SQLite이다."
    )
    if ARCH.exists():
        doc.add_picture(str(ARCH), width=Inches(3.3))
        cap = doc.add_paragraph(
            "그림 1. 공식 오픈소스 브랜드 로고(Simple Icons, CC0)로 구성한 시스템 "
            "아키텍처.", style="Body")
        _apply_korean_font(cap)
    H2("2.1. 계층 분리")
    B(
        "의존성은 엄격히 아래로만 흐른다. 컨트롤러는 요청·응답 스키마를 검증하고 "
        "도메인 오류를 HTTP 상태 코드로 매핑한다. 서비스는 도메인 규칙(식별자 발급, "
        "메트릭 선택, 지평 변환, 피크 계산)을 소유한다. 리포지토리만이 SQL을 발행한다. "
        "Core는 다른 계층에 의존하지 않으므로 데이터베이스 없이 단위 테스트된다."
    )

    H1("3. 경량 예측 엔진")
    B(
        "예측기는 시계열을 추세·계절·잔차의 가산합으로 모델링한다. 추세는 주기별 블록 "
        "평균에 대한 최소제곱으로 추정한다. 한 계절 주기 전체를 평균하면 주기 성분이 "
        "상쇄되어 기울기로 누설될 수 없다 — 주기 데이터에 대한 전역 최소제곱의 편향을 "
        "교정하는 고전적 분해 기법이다. 계절 지수는 위상별 평균 탈추세 값을 0합으로 "
        "재중심화한 것이다."
    )
    B(
        "예측은 목표 지평에서 추세에 계절 지수를 더해 외삽한다. 예측 구간은 표본 내 "
        "잔차가 아니라 표본 외 1-스텝 백테스트 오차(RMSE)로 산정하여, 짧고 과적합되기 "
        "쉬운 시계열에서 불확실성을 과소평가하지 않는다. 모델 품질은 분모 바닥값을 둔 "
        "MAPE로 보고하여 준유휴 표본이 백분율을 부풀리지 않게 한다. 엔진은 Python "
        "표준 라이브러리만 사용하므로 네이티브 의존성과 컨테이너 풋프린트가 무시할 "
        "수준이다."
    )

    H1("4. 정수계획 리사이징")
    B(
        "현재 할당과 예측 피크 부하가 주어지면, 엔진은 SLO를 위한 안전 마진을 "
        "유지하면서 예측 피크 가동률을 목표 이하로 유지하는 최소 정수 할당을 선택한다: "
        "peak_load × margin ≤ target_utilisation × allocation. 탐색 공간은 작고 "
        "유계(vCPU는 [1, 현재], 메모리는 256MB 블록)이므로 전수 열거로 최적해를 "
        "구한다 — 외부 의존성이 필요 없는 정확 해법이다. 95퍼센타일 피크 통계는 단발 "
        "스파이크가 영구 과프로비저닝을 강요하지 않게 한다. 실제로 버스트성 배치 "
        "호스트는 p95 안전 통계 덕분에 다운사이징이 올바르게 차단된다."
    )
    H2("4.1. GCP 머신 타입 매핑")
    B(
        "추상적 (vcpu, memory) 권장값은 E2·N2·C2·C3 등 사전정의 GCP 인스턴스 "
        "카탈로그에서 가장 근접한 실제 인스턴스로 스냅된다. 대시보드는 이를 "
        "\"n2-standard-8\"처럼 주문 가능한 사양으로 표시하고, 머신 타입 드롭다운으로 "
        "임의의 GCP 인스턴스로 직접 리사이즈할 수 있다."
    )

    H1("5. 구현 및 배포")
    B(
        "백엔드는 SQLAlchemy 2.0 async와 asyncpg를 쓰는 FastAPI이고, 프론트엔드는 "
        "Vite로 빌드하여 nginx가 서빙하는 React 19이다. 둘 다 Cloud Run이 주입한 "
        "포트를 따르는 비루트 컨테이너로 실행된다. Cloud Build 파이프라인은 린트와 "
        "테스트를 수행하고 두 이미지를 빌드하여 Artifact Registry에 푸시하며, 롤링 "
        "업데이트로 Cloud Run에 배포하고 공개 호출 권한을 부여한 뒤 배포 후 헬스 "
        "체크를 수행하여 비정상 시 빌드를 실패시킨다. 비밀값은 런타임에 Secret "
        "Manager에서 주입되며 절대 커밋되지 않는다."
    )
    H2("5.1. 인터랙티브 리사이징과 감사 추적")
    B(
        "대시보드는 예측-리사이즈 루프를 직접 노출한다: 운영자는 예측을 실행한 뒤 "
        "절반/두 배/AI 권장 할당을 적용한다. 각 동작은 호스트 레코드에 대한 실제 "
        "영속 변경이며 감사 로그 테이블에 기록되어, 얼마만큼의 용량이 회수되었는지를 "
        "실시간 활동 피드로 보여준다(예: \"Downsized web-prod-01: 16->9 vCPU, "
        "32->23 GB\"). 방사형 게이지는 할당 변경에 따라 예측 피크 가동률을 실시간 "
        "재계산한다. 또한 각 지표에는 의미를 설명하는 정보(i) 아이콘을 두었고, UI는 "
        "반응형으로 구성했다."
    )
    B(f"라이브 대시보드: {FRONTEND_URL}")
    B(f"라이브 API (Swagger /docs): {BACKEND_URL}")
    if SHOT.exists():
        doc.add_picture(str(SHOT), width=Inches(3.3))

    H1("6. 시험 데이터의 통계적 대표성")
    B(
        "데모/시드 메트릭은 임의가 아니라 공개된 대규모 데이터센터 트레이스의 실측 "
        "통계에 근거한다. Azure Resource Central(Cortez 외, SOSP 2017)에 따르면 VM의 "
        "60%가 평균 CPU 20% 미만, 40%가 95퍼센타일 CPU 50% 미만이며, VM은 대화형"
        "(일주기)과 지연무관(배치·개발/테스트)으로 나뉜다. Barroso & Hölzle는 서버가 "
        "대부분 10–50% 가동 대역에 머문다고 보고했고, Alibaba 2018 트레이스는 배치 "
        "전용 서버 평균 29.3%, 서비스 전용 7.4% CPU를 보고했다."
    )
    B(
        "이에 따라 데모 플릿을 6개 워크로드 아키타입(대화형 웹/대화형 API/정상상태 "
        "캐시/버스트 배치/과프로비저닝 서비스/산발적 개발)으로 구성하고, 호스트당 14일 "
        "× 시간단위 = 336표본(총 2,016표본)을 결정론적으로 생성한다. 자동 시험은 생성 "
        "데이터가 일주기성·버스트성·정상상태·저활용·대화형 예측가능성(MAPE ≤ 15%)을 "
        "재현하는지 단언한다."
    )

    H1("7. 평가")
    B(
        "품질 게이트는 ruff 정적 분석과 45개 pytest 스위트(예측기 8, 최적화기 9, API "
        "13, 머신타입 6, 워크로드 9)를 실행하며 전부 통과한다. 단위 시험은 경계값 분석과 "
        "동등 분할을 따르고, 통합 시험은 인메모리 리포지토리로 전체 Controller-Service-"
        "Core 경로를 구동하여 라이브 DB가 필요 없다. 근거 기반 6호스트 플릿에서 대화형 "
        "호스트의 MAPE는 9–13%로 15% 목표 이내이며, 최적화기는 과프로비저닝 호스트를 "
        "정확히 축소(web-prod-01 16→9 vCPU ≈36%, api-staging-02 ≈54%)하는 한편 "
        "중부하·버스트 호스트는 유지하고 메모리 바운드 캐시는 CPU만 축소한다 — 모두 "
        "99.9% SLO 신뢰도에서."
    )

    H1("8. 관련 연구 및 차별화")
    B(
        "최적화 시장은 세 그룹으로 나뉜다. (a) 쿠버네티스/클라우드 SaaS 최적화기"
        "(CAST AI, Sedai, StormForge, PerfectScale, Kubecost)는 워크로드별 ML로 "
        "파드/노드 요청을 자율 튜닝하지만 텔레메트리를 벤더 클라우드로 전송하고 퍼블릭 "
        "클라우드 상의 쿠버네티스를 전제한다. (b) 클라우드 제공자 추천기(AWS Compute "
        "Optimizer, Azure Advisor, Google Active Assist, IBM Turbonomic)는 단일 "
        "제공자에 종속되고 인스턴스 패밀리가 제한적이며 짧은(~14일) 윈도우에 의존해 "
        "계절성·버스트에 약하다. (c) 온프레 용량 모니터(SolarWinds, ManageEngine, "
        "IDERA)는 온프레에서 동작하나 임계치·선형회귀 기반의 서술적 리포팅에 그쳐 제약 "
        "최적화를 풀지 않는다."
    )
    B(
        "MetricLens는 그 사이의 공백을 차지한다. (1) 에어갭·자립형 — 외부 API·SaaS "
        "콜백·텔레메트리 유출이 없어 SaaS 최적화기가 구조적으로 진입할 수 없는 규제·"
        "망분리 환경(국방·금융·공공: CUI/GDPR/DORA)에 적합하다; (2) GPU-프리 경량 — "
        "표준 라이브러리 예측기를 범용 CPU에서 구동한다; (3) 처방적 — 유휴를 보고하는 "
        "데 그치지 않고 SLO 제약 정수계획을 정확히 푼다; (4) 화이트박스 — MAPE·예측 "
        "구간·헤드룸 부등식으로 모든 결정을 감사 가능하게 한다; (5) 인프라 비종속 — "
        "쿠버네티스 파드가 아니라 일반 VM/베어메탈 호스트를 모델링한다."
    )

    H1("9. 결론")
    B(
        "MetricLens AI는 정확한 CPU-온리 부하 예측과 정확한 정수계획 리사이징을 "
        "의존성 없는 클라우드 네이티브 서비스로 제공할 수 있음을 보인다. 수동적 "
        "텔레메트리를 정량적·SLO 인지 사이징 지침으로 전환함으로써 용량 관리를 "
        "반응형에서 선제형으로 전환하고, 온프레미스 환경의 인프라 비용과 전력 낭비를 "
        "줄이는 실용적 경로를 제시한다."
    )

    doc.save(str(OUT))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
