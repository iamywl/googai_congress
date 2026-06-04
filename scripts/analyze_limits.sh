#!/usr/bin/env bash
# =============================================================================
# analyze_limits.sh — MetricLens "현재 접근의 한계점" 16-관점 병렬 분석
#                      (Gemini 2.5 Flash via Vertex AI, tmux 병렬)
#
# review.sh 패턴 차용: 작품 대신 "분석 렌즈" 16개를 병렬로 돌린다. 각 렌즈는
# 전용 tmux 세션(nlim_NN)에서 동일한 코퍼스(문서+코드+테스트+설정+프론트)를 읽고
# 자신의 관점으로 한계점을 분석해 별도 디렉토리에 결과를 남긴다.
#
# 사용법:
#   analyze_limits.sh            # 16개 렌즈 병렬 분석 시작
#   analyze_limits.sh status     # 진행/완료 현황
#   analyze_limits.sh stop       # 모든 분석 세션 종료
#   analyze_limits.sh -1 <NN>    # 워커: 렌즈 1개만 (현재 셸에서) 분석
#
# 결과: limitations_review/agent_<NN>_<slug>/analysis.md (+ index.md, _input/context.md)
# =============================================================================
set -euo pipefail

ROOT="${PROJECT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
OUT_DIR="$ROOT/limitations_review"
INPUT="$OUT_DIR/_input/context.md"
PREFIX="nlim_"

# --- Vertex AI 인증 (기존 ADC 재사용, 하드코딩 금지) ---
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-knudc-yoonwoodev}"
export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
export GEMINI_CLI_TRUST_WORKSPACE=true
MODEL="${GEMINI_MODEL:-gemini-2.5-flash}"

# -----------------------------------------------------------------------------
# 16개 분석 렌즈 — "NN|slug|관점 설명". NN 은 01~16.
# -----------------------------------------------------------------------------
LENSES=(
"01|forecasting-model|예측 모델의 표현력 한계. 계절-추세 분해 + AR(1) 잔차 보정 방식이 비선형성·다중 계절성(주/월)·체제 전환(regime change)·다변량 상호작용(CPU↔메모리↔네트워크)을 포착하지 못하는 지점, 단일 호라이즌·단변량 가정의 한계를 분석한다."
"02|uncertainty|예측 불확실성 정량화의 한계. lower/upper = ŷ ± 1.96·RMSE 의 정규성·등분산(homoscedastic) 가정, 비대칭·두꺼운 꼬리 분포, 호라이즌 증가 시 구간이 넓어지지 않는 문제, PICP 0.93–0.98 해석의 함정을 분석한다."
"03|optimization|정수계획 최적화의 한계. 전수 열거(exact enumeration)의 확장성, 호스트별 독립 최적화로 인한 전역 최적 누락(빈패킹·배치·통합 미고려), vCPU·메모리를 분리 산정해 자원 결합 효과를 무시하는 점, 단조 제약의 표현력을 분석한다."
"04|slo-model|SLO 모델링의 한계. target_utilisation=0.65·safety_margin=1.2·slo_confidence=99.9% 가 정적 상수라는 점, 큐잉이론/대기시간/테일 레이턴시와의 연결 부재, '피크 이용률 ≤ 목표' 가 실제 SLA(가용성·지연)를 보장한다는 근거의 취약성을 분석한다."
"05|data-representativeness|데이터 대표성의 한계. 합성 워크로드(6 아키타입×14일)에 대한 의존, 실측 트레이스 부재, Azure/Alibaba 통계 정렬이 일반화를 보장하지 못하는 점, 결정론적 이상치 주입의 현실성, 도메인 시프트(분포 변화) 취약성을 분석한다."
"06|evaluation-rigor|평가 엄밀성의 한계. 1-스텝 확장윈도우 백테스트만 수행(다스텝/장기 미평가), 표본이 6 아키타입에 불과, seasonal-naive 위주 기준선, DM 검정 표본 수, 리사이징 '결정'의 end-to-end 비용·SLO 위반 평가 부재를 분석한다."
"07|scalability|확장성·플릿 규모의 한계. 수천 호스트로 확장 시 호스트별 예측+최적화의 계산·운영 비용, 상호의존 워크로드·마이그레이션·오토스케일링 그룹 미고려, 동기 처리·배치 주기의 병목을 분석한다."
"08|realtime-ops|실시간성·운영의 한계. stop→setMachineType→start 의 다운타임, 상태유지(stateful) 서비스·무중단 요구와의 충돌, 리사이즈 진동(flapping)·쿨다운 부재, 반응 지연(시간단위 모니터링)으로 인한 적시성 한계를 분석한다."
"09|cost-model|비용 모델의 한계. 절감률을 vCPU·메모리 감축의 단순 평균 프록시로 계산하는 점, 실제 머신타입 가격·전력·커밋약정·이그레스·SLO 위반 비용 미반영, 다운사이징의 리스크 비용 부재를 분석한다."
"10|security-compliance|보안·규제·자립성의 한계. '에어갭/온프레 자립형' 주장과 실제 GCP(Cloud Run/Monitoring/Compute Engine) 종속의 모순, Compute Engine 실제 리사이즈 권한·감사·롤백, 예산 가드/denylist 우회 가능성, 비밀관리 경로를 분석한다."
"11|architecture-debt|아키텍처·기술부채의 한계. 데모 SQLite ↔ 운영 Postgres 이중 경로의 동기화·동작 차이, 레이어드 구조의 실제 준수도, 시드/멱등성·마이그레이션 전략, 단일 백엔드의 장애 격리·관측가능성 부재를 분석한다."
"12|gcp-integration|GCP 통합의 한계. Cloud Monitoring 시간단위 정렬 지연(실측 1pt/h, 풀 사이클 ~24h), 메모리 미관측을 CPU 연동 프록시로 대체, e2 shared-core 이용률 100% 포화, Ops Agent 의존, API 레이트리밋·권한 전파를 분석한다."
"13|generalization-domain|일반화·도메인 적용의 한계. CPU/메모리 외 네트워크·디스크 IOPS·GPU·동시접속 미고려, 이벤트성/버스트성·콜드스타트 워크로드, 비주기 서비스, 컨테이너/서버리스 등 타 인프라로의 이식성 한계를 분석한다."
"14|explainability-ux|설명가능성·운영 UX의 한계. '화이트박스' 주장 대비 운영자가 리사이즈 결정을 신뢰·검증·승인할 근거 제시 수준, 정보 아이콘·활동로그의 충분성, 자동 적용 vs 승인 흐름, 오경보 시 사용자 대응 경로를 분석한다."
"15|competitive-moat|경쟁우위 방어가능성의 한계. 차별점(에어갭·GPU프리·SLO 정수계획·화이트박스·감사)이 실제로 모방난이도가 높은지, 기존 도구(K8s VPA, KEDA, Prometheus 기반 룰)와의 실질 격차, 진입장벽·지속가능성을 분석한다."
"16|meta-synthesis|메타-종합. 위 모든 관점을 가로질러 '가정의 연쇄(예측 정확도 → p95 → 안전마진 → 정수해 → 실제 절감)'에서 가장 취약한 단일 고리와, 한 가정이 깨질 때의 도미노 파급, 프로젝트가 직면한 가장 치명적인 단일 한계를 도출한다."
)

slug_of()  { printf '%s' "${LENSES[$(( 10#$1 - 1 ))]}" | cut -d'|' -f2; }
desc_of()  { printf '%s' "${LENSES[$(( 10#$1 - 1 ))]}" | cut -d'|' -f3-; }

# -----------------------------------------------------------------------------
# 공유 입력 코퍼스 1회 병합 (멱등)
# -----------------------------------------------------------------------------
build_input() {
  mkdir -p "$(dirname "$INPUT")"
  {
    echo "# MetricLens AI — 분석 대상 코퍼스 (문서 + 코드 + 테스트 + 설정 + 프론트엔드)"
    echo

    echo "## A. 기획·기술 문서 (Markdown)"; echo
    while IFS= read -r f; do
      echo "===== [문서] ${f#"$ROOT"/} ====="; cat "$f"; echo; echo
    done < <(
      find "$ROOT" \
        -path "$OUT_DIR" -prune -o \
        -path "$ROOT/node_modules" -prune -o \
        -path "$ROOT/backend/.venv" -prune -o \
        -path "$ROOT/frontend/node_modules" -prune -o \
        -path "$ROOT/frontend/dist" -prune -o \
        -path "$ROOT/backend/.pytest_cache" -prune -o \
        -path "$ROOT/.git" -prune -o \
        -name '*.md' -print | sort )

    echo "## B. 백엔드 구현 (Python — backend/app)"; echo
    while IFS= read -r f; do
      echo "===== [코드] ${f#"$ROOT"/} ====="; cat "$f"; echo; echo
    done < <(find "$ROOT/backend/app" -name '*.py' ! -path '*/__pycache__/*' | sort)

    echo "## C. 백엔드 테스트 (Python — backend/tests)"; echo
    while IFS= read -r f; do
      echo "===== [테스트] ${f#"$ROOT"/} ====="; cat "$f"; echo; echo
    done < <(find "$ROOT/backend/tests" -name '*.py' ! -path '*/__pycache__/*' 2>/dev/null | sort)

    echo "## D. 인프라·설정·스크립트"; echo
    while IFS= read -r f; do
      [ -f "$f" ] || continue
      echo "===== [설정] ${f#"$ROOT"/} ====="; cat "$f"; echo; echo
    done < <(
      find "$ROOT" \
        -path "$OUT_DIR" -prune -o \
        -path "$ROOT/node_modules" -prune -o \
        -path "$ROOT/backend/.venv" -prune -o \
        -path "$ROOT/frontend/node_modules" -prune -o \
        -path "$ROOT/frontend/dist" -prune -o \
        -path "$ROOT/.git" -prune -o \
        \( -name '*.yaml' -o -name '*.yml' -o -name 'Dockerfile' \
           -o -name '*.sh' -o -name '*.sql' -o -name '*.toml' \
           -o -name 'requirements*.txt' \) -print | sort )

    echo "## E. 프론트엔드 (frontend/src)"; echo
    while IFS= read -r f; do
      echo "===== [프론트] ${f#"$ROOT"/} ====="; cat "$f"; echo; echo
    done < <(find "$ROOT/frontend/src" -type f \
               \( -name '*.jsx' -o -name '*.js' -o -name '*.css' \) | sort)
  } > "$INPUT"
  echo "[input] 코퍼스 생성: $INPUT ($(wc -l < "$INPUT") 줄)" >&2
}

# -----------------------------------------------------------------------------
# 프롬프트 생성 (할당된 렌즈에 집중)
# -----------------------------------------------------------------------------
build_prompt() {
  local nn="$1" slug desc
  slug="$(slug_of "$nn")"; desc="$(desc_of "$nn")"
  cat <<EOP
당신은 분산 시스템·시계열 예측·자원 최적화에 정통한 시스템 아키텍트이자 비판적 기술
리뷰어입니다. 표준입력으로 'MetricLens AI' 프로젝트의 전체 코퍼스(기획·기술 문서, 백엔드
구현 코드, 테스트, 인프라/설정, 프론트엔드)가 주어집니다.

MetricLens 는 경량 시계열 모델로 서버 부하(CPU·메모리)를 예측하고, 정수계획법으로 SLO를
보장하는 최소 자원 구성을 산출해 실제 GCP 인스턴스를 리사이즈하는 시스템입니다.

[당신의 임무] 이 프로젝트의 **현재 접근 방식이 가진 한계점**을, 아래의 **할당된 단일
관점**에 집중해 깊이 있게 분석합니다. 다른 관점은 16명의 다른 분석가가 맡습니다. 당신은
이 렌즈를 끝까지 파고드는 전문가입니다.

[할당된 관점 #${nn} — ${slug}]
${desc}

[분석 원칙]
- 칭찬·요약 나열 금지. 오직 "한계·약점·리스크·누락·암묵적 가정"을 찾습니다.
- 모든 지적은 코퍼스의 **구체적 근거를 인용**해 뒷받침합니다(파일 경로, 함수/변수명,
  상수값, 문서의 문장 등). 추측이면 추측이라고 명시합니다.
- 코드와 문서가 어긋나는 지점, 문서의 주장이 코드로 뒷받침되지 않는 지점을 적극적으로
  찾습니다.
- 비유·유추를 쓰지 말고 직접적으로 기술합니다. 한국어로 작성합니다.
- 현실적이고 실행 가능한 개선 방향을 제시하되, 한계 진단이 본론입니다.

[출력 목차 — 그대로 사용]
## 0. 관점 메모 (이 렌즈로 무엇을 집중적으로 봤는지 2~3줄)
## 1. 핵심 한계 요약 (이 관점에서 가장 중요한 한계 3~5개를 한 줄씩)
## 2. 상세 분석 (한계마다: [심각도: 치명/높음/중간/낮음] · 무엇이 / 근거(인용) / 왜 문제 / 어떤 조건에서 드러나는가)
## 3. 암묵적 가정과 그 취약성 (현재 설계가 깔고 있는 전제와 깨질 조건)
## 4. 파급 효과 (이 한계가 다른 영역·전체 시스템에 미치는 영향)
## 5. 개선 제안 (영향 큰 순서, 구체적·실행 가능하게)
## 6. 타 관점과의 연결 (다른 분석가가 깊게 봐야 할 인접 한계 지목)
EOP
}

# -----------------------------------------------------------------------------
# 워커: 렌즈 1개 분석
# -----------------------------------------------------------------------------
review_one() {
  local nn="$1" slug desc dir out ts prompt
  nn="$(printf '%02d' "$(( 10#$nn ))")"
  slug="$(slug_of "$nn")"; desc="$(desc_of "$nn")"
  [ -n "$slug" ] || { echo "[limits] 알 수 없는 렌즈: $nn" >&2; return 1; }
  [ -s "$INPUT" ] || build_input
  dir="$OUT_DIR/agent_${nn}_${slug}"
  mkdir -p "$dir"
  out="$dir/analysis.md"
  ts="$(date +%Y%m%d-%H%M)"
  prompt="$(build_prompt "$nn")"

  echo "[limits] #$nn ($slug) 분석 시작 -> $out" >&2
  {
    echo "# MetricLens 한계점 분석 #${nn} — ${slug}"; echo
    echo "- 생성: ${ts}"
    echo "- 모델: ${MODEL} (Vertex AI / ${GOOGLE_CLOUD_PROJECT}/${GOOGLE_CLOUD_LOCATION})"
    echo "- 관점: ${desc}"
    echo "- 입력 코퍼스: ${INPUT} ($(wc -l < "$INPUT") 줄)"
    echo; echo "---"; echo
    gemini -m "$MODEL" -p "$prompt" < "$INPUT" 2>/dev/null
  } > "$out"
  echo "[limits] #$nn 완료: $out" >&2
}

# -----------------------------------------------------------------------------
# 현황 / 종료 / 인덱스
# -----------------------------------------------------------------------------
show_status() {
  local nn slug sess dir out state last
  for i in $(seq 1 ${#LENSES[@]}); do
    nn="$(printf '%02d' "$i")"; slug="$(slug_of "$nn")"
    sess="${PREFIX}${nn}"; dir="$OUT_DIR/agent_${nn}_${slug}"; out="$dir/analysis.md"
    if [ -s "$out" ] && grep -q '^## ' "$out" 2>/dev/null; then
      state="완료 $(date -r "$out" +%H:%M 2>/dev/null)"
    else state="미생성"; fi
    if tmux has-session -t "$sess" 2>/dev/null; then
      last="$(tmux capture-pane -p -t "$sess" 2>/dev/null | grep -v '^[[:space:]]*$' | tail -1)"
      case "$last" in
        *'완료:'*) last="(작성 완료)";; *'분석 시작'*) last="(분석 중...)";;
        *'$'|*'#') last="(대기/종료)";; esac
    else last="(세션 없음)"; fi
    printf '  #%s %-22s | %-12s | %s\n' "$nn" "$slug" "$state" "$last"
  done
}

stop_all() {
  tmux ls 2>/dev/null | sed 's/:.*//' | grep "^${PREFIX}" | while read -r s; do
    tmux kill-session -t "$s" 2>/dev/null && echo "  종료: $s"
  done
  echo "모든 분석 세션을 종료했습니다."
}

write_index() {
  local idx="$OUT_DIR/index.md" nn slug out
  {
    echo "# MetricLens 한계점 분석 — 16 관점 인덱스"; echo
    echo "- 생성: $(date +%Y-%m-%d\ %H:%M) · 모델: ${MODEL} (Vertex AI)"
    echo "- 입력 코퍼스: \`_input/context.md\`"; echo
    echo "| # | 관점(slug) | 결과 | 상태 |"
    echo "|---|---|---|---|"
    for i in $(seq 1 ${#LENSES[@]}); do
      nn="$(printf '%02d' "$i")"; slug="$(slug_of "$nn")"
      out="agent_${nn}_${slug}/analysis.md"
      if [ -s "$OUT_DIR/$out" ]; then st="완료"; else st="미생성"; fi
      echo "| $nn | $slug | [$out]($out) | $st |"
    done
  } > "$idx"
  echo "[limits] 인덱스: $idx" >&2
}

run_all() {
  build_input
  local nn slug sess
  for i in $(seq 1 ${#LENSES[@]}); do
    nn="$(printf '%02d' "$i")"; slug="$(slug_of "$nn")"; sess="${PREFIX}${nn}"
    tmux has-session -t "$sess" 2>/dev/null || tmux new-session -d -s "$sess" -c "$ROOT"
    tmux send-keys -t "$sess" "bash '$SELF' -1 '$nn'" Enter
    printf '  ▶ #%s %-22s (%s)\n' "$nn" "$slug" "$sess"
  done
  write_index
  echo "총 ${#LENSES[@]}개 관점 분석을 병렬로 시작했습니다."
  echo "현황:   bash '$SELF' status"
  echo "결과:   $OUT_DIR/agent_*/analysis.md  (인덱스: $OUT_DIR/index.md)"
  echo "라이브: tmux attach -t '${PREFIX}01'  (Ctrl-b d 로 빠져나옴)"
}

# =============================================================================
case "${1:-}" in
  status) show_status; exit 0 ;;
  stop)   stop_all;    exit 0 ;;
  index)  write_index; exit 0 ;;
  -1)     shift; review_one "${1:?-1 다음에 렌즈 번호(01~16)}"; exit $? ;;
  *)      run_all; exit 0 ;;
esac
