// Korean one-line explanations for every metric/indicator shown on the dashboard.
// Surfaced through the InfoTip "i" icons so each figure is self-describing.
export const GLOSSARY = {
  cpu: 'CPU 사용률(%) — 할당된 vCPU 대비 실제 연산 부하. 높을수록 코어가 바쁩니다.',
  memory: '메모리 사용률(%) — 할당된 RAM 대비 사용 중인 메모리 비율.',
  netIn: '네트워크 수신(kbps) — 호스트로 들어오는 초당 트래픽.',
  netOut: '네트워크 송신(kbps) — 호스트에서 나가는 초당 트래픽.',
  hostsMonitored: '모니터링 중인 서버(호스트) 대수.',
  reclaimableVcpu: '예측 기반으로 안전하게 회수 가능한 vCPU 코어 총합 — 줄일 수 있는 CPU.',
  reclaimableMemory: '안전하게 회수 가능한 메모리(GB) 총합 — 줄일 수 있는 RAM.',
  avgSaving: '플릿 평균 절감률 — 권장안 적용 시 평균적으로 줄어드는 자원 비율.',
  sloMaintained:
    'SLO(서비스 수준 목표) 유지율 — 리사이징 후에도 보장되는 가용성 신뢰도.',
  projectedUtil:
    '예상 피크 가동률(%) — 현재 할당량 기준, 예측된 최대 부하가 차지하는 비율. 65%↓ 녹색·85%↓ 주황·초과 빨강.',
  predicted: '예측치 — 시계열 모델이 추정한 다음 구간(+60분)의 CPU 사용률.',
  interval:
    '95% 신뢰구간 — 예측치가 95% 확률로 들어갈 범위(백테스트 오차로 산출).',
  mape: 'MAPE — 평균 절대 백분율 오차. 과거 데이터 백테스트 기준 예측 정확도(낮을수록 정확, 목표 ≤ 15%).',
  costSaving:
    '예상 비용 절감(%) — 권장 사양으로 줄였을 때 vCPU·메모리 기준 절감 비율.',
  sloConfidence: 'SLO 신뢰도(%) — 권장안이 보장하는 가용성 수준.',
  machineType:
    'GCP 머신 타입 — 권장 사양에 가장 근접한 실제 Google Cloud 인스턴스(vCPU·RAM).',
  currentAlloc: '현재 할당 — 이 호스트에 지금 배정된 vCPU·메모리.',
  resizeTarget:
    '리사이징 대상 — 적용할 GCP 인스턴스를 선택하면 해당 사양으로 실제 변경되고 로그에 기록됩니다.',
  activityLog:
    '활동 로그 — 실행한 예측과 적용한 리사이징이 서버에 영속 기록되어 새로고침 후에도 유지됩니다.',
};
