// 정해진 초당 요청 수로 PATH 를 부른다. 결과 요약은 /out/<NAME>.json 에도 남긴다.
//   TARGET=/hedge RATE=200 DURATION=120s METHOD=GET BODY=
import http from 'k6/http';

const TARGET = __ENV.TARGET || '/plain';
const METHOD = __ENV.METHOD || 'GET';
const BODY = __ENV.BODY || null;
const NAME = __ENV.NAME || TARGET.replace(/\//g, '');

export const options = {
  scenarios: {
    steady: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 200),
      timeUnit: '1s',
      duration: __ENV.DURATION || '120s',
      preAllocatedVUs: 50,
      maxVUs: 400,
    },
  },
  summaryTrendStats: ['avg', 'p(50)', 'p(90)', 'p(99)', 'p(99.9)', 'max'],
};

export default function () {
  const params = BODY ? { headers: { 'Content-Type': 'text/plain' } } : {};
  http.request(METHOD, `http://envoy:10000${TARGET}`, BODY, params);
}

export function handleSummary(data) {
  const d = data.metrics.http_req_duration.values;
  const line = `${NAME}: reqs=${data.metrics.http_reqs.values.count} failed=${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}% ` +
    `p50=${d['p(50)'].toFixed(1)} p90=${d['p(90)'].toFixed(1)} p99=${d['p(99)'].toFixed(1)} p99.9=${d['p(99.9)'].toFixed(1)} max=${d.max.toFixed(1)} (ms)\n`;
  return { stdout: line, [`/out/${NAME}.json`]: JSON.stringify(data, null, 1) };
}
