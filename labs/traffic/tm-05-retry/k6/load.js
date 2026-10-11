// VUS=1 ITERATIONS=200 : 한 번에 하나씩 차례로 (동시 재시도가 1을 넘지 않는다)
// VUS=100 DURATION=60s : 사용자 100명이 쉬지 않고 차례로 (동시에 100개)
// RATE=50 DURATION=60s : 초당 RATE 건을 일정하게
import http from 'k6/http';

const NAME = __ENV.NAME || 'run';
const scenario = __ENV.RATE
  ? { executor: 'constant-arrival-rate', rate: Number(__ENV.RATE), timeUnit: '1s',
      duration: __ENV.DURATION || '60s', preAllocatedVUs: 100, maxVUs: 1000 }
  : __ENV.DURATION
  ? { executor: 'constant-vus', vus: Number(__ENV.VUS || 10), duration: __ENV.DURATION }
  : { executor: 'shared-iterations', vus: Number(__ENV.VUS || 1), iterations: Number(__ENV.ITERATIONS || 200) };

export const options = {
  scenarios: { main: scenario },
  summaryTrendStats: ['avg', 'p(50)', 'p(99)', 'max'],
};

export default function () {
  http.get('http://198.18.27.10:10000/work', { timeout: '30s' });
}

export function handleSummary(data) {
  const d = data.metrics.http_req_duration.values;
  const line = `${NAME}: reqs=${data.metrics.http_reqs.values.count} failed=${(data.metrics.http_req_failed.values.rate * 100).toFixed(1)}% ` +
    `p50=${d['p(50)'].toFixed(0)} p99=${d['p(99)'].toFixed(0)} max=${d.max.toFixed(0)} (ms)\n`;
  return { stdout: line, [`/out/${NAME}.json`]: JSON.stringify(data, null, 1) };
}
