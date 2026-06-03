// Bilingual one-line explanations for every metric/indicator, surfaced through
// the InfoTip "i" icons. Call glossary(lang) to get the dict for a language.
const G = {
  en: {
    cpu: 'CPU utilisation (%) — load on the allocated vCPU. Higher = busier cores.',
    memory: 'Memory utilisation (%) — used RAM as a share of the allocation.',
    netIn: 'Network in (kbps) — inbound traffic per second.',
    netOut: 'Network out (kbps) — outbound traffic per second.',
    hostsMonitored: 'Number of monitored servers (hosts).',
    reclaimableVcpu: 'Total vCPU cores that can be safely reclaimed per the forecast.',
    reclaimableMemory: 'Total memory (GB) that can be safely reclaimed.',
    avgSaving: 'Average fleet saving when recommendations are applied.',
    sloMaintained: 'SLO (service-level objective) availability preserved after resizing.',
    projectedUtil:
      'Projected peak utilisation (%) at the current allocation. Green <=65% / amber <=85% / red above.',
    predicted: "Point forecast — the model's estimate of next-hour (+60m) CPU.",
    interval: '95% prediction interval — the range the actual value falls in with 95% probability.',
    mape: 'MAPE — mean absolute percentage error from the backtest (lower is better, target <= 15%).',
    costSaving: 'Estimated cost saving (%) from the recommended downsizing (vCPU + memory).',
    sloConfidence: 'SLO confidence (%) the recommendation preserves.',
    machineType: 'GCP machine type — the nearest orderable Google Cloud instance (vCPU / RAM).',
    currentAlloc: 'Current allocation — vCPU and memory assigned to this host now.',
    resizeTarget:
      'Resize target — picking a GCP instance applies that spec for real and logs it.',
    activityLog:
      'Activity log — forecasts and resizes are persisted server-side and survive reloads.',
  },
  ko: {
    cpu: 'CPU 사용률(%) — 할당된 vCPU 대비 실제 연산 부하. 높을수록 코어가 바쁩니다.',
    memory: '메모리 사용률(%) — 할당된 RAM 대비 사용 중인 메모리 비율.',
    netIn: '네트워크 수신(kbps) — 호스트로 들어오는 초당 트래픽.',
    netOut: '네트워크 송신(kbps) — 호스트에서 나가는 초당 트래픽.',
    hostsMonitored: '모니터링 중인 서버(호스트) 대수.',
    reclaimableVcpu: '예측 기반으로 안전하게 회수 가능한 vCPU 코어 총합.',
    reclaimableMemory: '안전하게 회수 가능한 메모리(GB) 총합.',
    avgSaving: '플릿 평균 절감률 — 권장안 적용 시 평균 자원 절감 비율.',
    sloMaintained: 'SLO(서비스 수준 목표) 유지율 — 리사이징 후에도 보장되는 가용성.',
    projectedUtil:
      '예상 피크 가동률(%) — 현재 할당 기준 예측 최대 부하. 65%↓ 녹색·85%↓ 주황·초과 빨강.',
    predicted: '예측치 — 모델이 추정한 다음 구간(+60분)의 CPU 사용률.',
    interval: '95% 예측구간 — 실제값이 95% 확률로 들어갈 범위.',
    mape: 'MAPE — 백테스트 평균 절대 백분율 오차(낮을수록 정확, 목표 <= 15%).',
    costSaving: '예상 비용 절감(%) — 권장 사양으로 줄였을 때 vCPU·메모리 절감 비율.',
    sloConfidence: 'SLO 신뢰도(%) — 권장안이 보장하는 가용성 수준.',
    machineType: 'GCP 머신 타입 — 권장 사양에 가장 근접한 실제 GCP 인스턴스(vCPU·RAM).',
    currentAlloc: '현재 할당 — 이 호스트에 지금 배정된 vCPU·메모리.',
    resizeTarget: '리사이징 대상 — GCP 인스턴스를 선택하면 해당 사양으로 실제 변경·기록됩니다.',
    activityLog: '활동 로그 — 예측·리사이즈가 서버에 영속 기록되어 새로고침 후에도 유지됩니다.',
  },
};

export function glossary(lang) {
  return G[lang] || G.en;
}
