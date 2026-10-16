// 사이드카 한 홉의 값: 같은 네트워크 안에서 TARGET 을 초당 RATE 건씩 DURATION 동안 부른다.
import http from 'k6/http';
export const options = {
  discardResponseBodies: true,
  summaryTrendStats: ['avg', 'p(50)', 'p(90)', 'p(99)', 'max'],
  scenarios: { s: { executor: 'constant-arrival-rate', rate: Number(__ENV.RATE || 200), timeUnit: '1s',
    duration: __ENV.DURATION || '60s', preAllocatedVUs: 50, maxVUs: 200 } },
};
export default function () { http.get(__ENV.TARGET); }
export function handleSummary(d) {
  const m = d.metrics.http_req_duration.values, f = d.metrics.http_req_failed.values;
  const line = `${__ENV.NAME} n=${d.metrics.http_reqs.values.count} failed=${f.rate} ` +
    `p50=${m['p(50)'].toFixed(2)}ms p90=${m['p(90)'].toFixed(2)}ms p99=${m['p(99)'].toFixed(2)}ms max=${m.max.toFixed(2)}ms\n`;
  return { stdout: line, [`/out/latency-${__ENV.NAME}.txt`]: line };
}
