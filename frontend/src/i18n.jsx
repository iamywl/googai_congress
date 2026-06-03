/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useState } from 'react';

// Lightweight bilingual layer (English / Korean). Components call useT() to get
// `t(key)` and the current `lang`; a header toggle flips the language. English is
// the default/primary; the choice is persisted to localStorage.

const STR = {
  // Header / chrome
  subtitle: { en: 'Time-series load forecasting & resizing optimisation',
              ko: '시계열 부하 예측 · 리사이징 최적화' },
  live: { en: '● live', ko: '● 라이브' },
  demo: { en: '● demo data', ko: '● 데모 데이터' },
  slides: { en: '📊 Slides', ko: '📊 발표자료' },
  brief: { en: '📄 Brief', ko: '📄 소개자료' },
  footer: { en: 'MetricLens AI · CPU-only forecasting · target MAPE ≤ 15% · SLO 99.9%',
            ko: 'MetricLens AI · CPU-온리 예측 · 목표 MAPE ≤ 15% · SLO 99.9%' },

  // Nav
  navDashboard: { en: 'Dashboard', ko: '대시보드' },
  navHistory: { en: 'History', ko: '기록' },
  navTests: { en: 'Test Scenarios', ko: '테스트 시나리오' },

  // KPI strip
  kpiHosts: { en: 'Hosts monitored', ko: '모니터링 호스트' },
  kpiReclVcpu: { en: 'Reclaimable vCPU', ko: '회수 가능 vCPU' },
  kpiReclMem: { en: 'Reclaimable memory', ko: '회수 가능 메모리' },
  kpiSaving: { en: 'Avg. cost saving', ko: '평균 절감률' },
  kpiSlo: { en: 'SLO maintained', ko: 'SLO 유지' },
  unitCores: { en: 'cores', ko: '코어' },

  // Dashboard side panel
  projUtil: { en: 'Projected Utilisation', ko: '예상 가동률' },

  // ResizeControls
  rcTitle: { en: 'Interactive HW Resizing', ko: '인터랙티브 HW 리사이징' },
  rcCurrent: { en: 'Current allocation', ko: '현재 할당' },
  rcMachine: { en: 'GCP machine type', ko: 'GCP 머신 타입' },
  rcPeak: { en: 'Projected peak utilisation', ko: '예상 피크 가동률' },
  rcHalve: { en: '↓ Halve vCPU', ko: '↓ vCPU 절반' },
  rcDouble: { en: '↑ Double vCPU', ko: '↑ vCPU 2배' },
  rcApplyRec: { en: '✓ Apply AI recommendation', ko: '✓ AI 권장 적용' },
  rcRun: { en: '▶ Run forecast', ko: '▶ 예측 실행' },
  rcWorking: { en: 'Working…', ko: '실행 중…' },
  rcResizeTo: { en: 'Resize to GCP instance', ko: 'GCP 인스턴스로 변경' },
  rcSelect: { en: 'Select machine type…', ko: '머신 타입 선택…' },
  rcApply: { en: 'Apply', ko: '적용' },

  // RecommendationCard
  recTitle: { en: 'Resizing Recommendation', ko: '리사이징 권장' },
  recVcpu: { en: 'vCPU', ko: 'vCPU' },
  recMemory: { en: 'Memory', ko: '메모리' },
  recInstance: { en: 'GCP instance', ko: 'GCP 인스턴스' },
  recSaving: { en: 'Est. cost saving', ko: '예상 절감' },
  recSlo: { en: 'SLO confidence', ko: 'SLO 신뢰도' },
  recNoteDown: { en: 'Headroom detected — downsizing keeps utilisation under target while preserving availability.',
                 ko: '여유 감지 — 다운사이징해도 목표 이하 가동률과 가용성을 유지합니다.' },
  recNoteOk: { en: 'Current allocation is near-optimal for the forecasted load.',
               ko: '현재 할당은 예측 부하에 거의 최적입니다.' },

  // ForecastPanel
  fpPredicted: { en: 'Predicted', ko: '예측치' },
  fpInterval: { en: '95% interval', ko: '95% 구간' },
  fpMape: { en: 'MAPE (target ≤ 15%)', ko: 'MAPE (목표 ≤ 15%)' },
  fpTitle: { en: 'CPU Forecast (+60m)', ko: 'CPU 예측 (+60분)' },

  // MetricChart
  mcTitle: { en: 'Resource Utilisation (7-day)', ko: '자원 사용률 (7일)' },
  mcCpu: { en: 'CPU %', ko: 'CPU %' },
  mcMem: { en: 'Memory %', ko: '메모리 %' },
  mcNetIn: { en: 'Net In Kbps', ko: '수신 Kbps' },
  mcNetOut: { en: 'Net Out Kbps', ko: '송신 Kbps' },

  // ActivityLog
  alTitle: { en: 'Activity Log', ko: '활동 로그' },
  alEmpty: { en: 'No actions yet. Apply a resize or run a forecast.',
             ko: '아직 기록이 없습니다. 리사이즈나 예측을 실행하세요.' },
  alCapacity: { en: 'capacity', ko: '용량' },

  // History view
  hvFleetLog: { en: 'Fleet Activity Log', ko: '플릿 활동 로그' },
  hvFleetDesc: { en: "Every host's past forecasts and resizes (newest first, persisted).",
                 ko: '모든 호스트의 과거 예측·리사이즈 (최신순, 영속 저장).' },
  hvEmpty: { en: 'No records yet.', ko: '아직 기록이 없습니다.' },
  hvMetricHistory: { en: 'Metric History', ko: '메트릭 기록' },
  hvSamples: { en: 'samples', ko: '표본' },
  hvPeriod: { en: 'period', ko: '기간' },
  hvCpuAvgMax: { en: 'CPU avg/max', ko: 'CPU 평균/최대' },
  hvMemAvgMax: { en: 'Memory avg/max', ko: '메모리 평균/최대' },
  hvLoading: { en: 'Loading…', ko: '불러오는 중…' },
  thTimestamp: { en: 'Timestamp', ko: '타임스탬프' },

  // Tests view
  tvTitle: { en: 'Test Scenarios', ko: '테스트 시나리오' },
  tvDesc: { en: 'Each button runs a real backend scenario; forecasts and resizes are persisted and shown instantly on Dashboard and History.',
            ko: '버튼을 누르면 실제 백엔드 시나리오가 실행됩니다. 예측·리사이즈는 영속 기록되어 Dashboard·History에 즉시 반영됩니다.' },
  tvRunning: { en: 'Running…', ko: '실행 중…' },
};

const LangContext = createContext({ lang: 'en', setLang: () => {}, t: (k) => k });

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    try {
      return localStorage.getItem('metriclens-lang') || 'en';
    } catch {
      return 'en';
    }
  });
  const setLang = useCallback((l) => {
    setLangState(l);
    try {
      localStorage.setItem('metriclens-lang', l);
    } catch {
      /* ignore */
    }
  }, []);
  const t = useCallback((key) => (STR[key] ? STR[key][lang] : key), [lang]);
  return <LangContext.Provider value={{ lang, setLang, t }}>{children}</LangContext.Provider>;
}

export function useT() {
  return useContext(LangContext);
}
