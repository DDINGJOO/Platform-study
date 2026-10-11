import http from 'k6/http';

// 닫힌 부하: VU N 개가 쉬지 않고 요청을 보낸다. 응답을 받아야 다음 요청을 보내므로
// 서버 안의 동시성은 N 을 넘지 않는다. USL 의 독립 변수 N 이 바로 이 값이다.
// 앞 WARM 초는 버리고(JIT·커넥션 준비), 뒤 MEASURE 초만 센다.
const N = Number(__ENV.VUS || 1);
const WARM = Number(__ENV.WARM || 5);
const MEASURE = Number(__ENV.MEASURE || 20);

export const options = {
  scenarios: {
    warm: { executor: 'constant-vus', vus: N, duration: `${WARM}s`, gracefulStop: '0s' },
    measure: { executor: 'constant-vus', vus: N, duration: `${MEASURE}s`, startTime: `${WARM}s`, gracefulStop: '5s' },
  },
  // 서브메트릭을 요약에 남기려면 임계값이 하나 있어야 한다(값 자체는 의미 없음)
  thresholds: {
    'http_reqs{scenario:measure}': ['count>=0'],
    'http_req_duration{scenario:measure}': ['avg>=0'],
    'http_req_failed{scenario:measure}': ['rate>=0'],
  },
  summaryTrendStats: ['avg', 'p(50)', 'p(99)', 'max'],
};

export default function () {
  http.get(`http://${__ENV.TARGET || 'app'}:8080/work`, { timeout: '30s' });
}

export function handleSummary(data) {
  const m = data.metrics;
  const out = {
    vus: N,
    measureSeconds: MEASURE,
    count: m['http_reqs{scenario:measure}'].values.count,
    avgMs: m['http_req_duration{scenario:measure}'].values.avg,
    p50Ms: m['http_req_duration{scenario:measure}'].values['p(50)'],
    p99Ms: m['http_req_duration{scenario:measure}'].values['p(99)'],
    failRate: m['http_req_failed{scenario:measure}'].values.rate,
  };
  return { stdout: JSON.stringify(out) + '\n' };
}
