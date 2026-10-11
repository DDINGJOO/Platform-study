import http from 'k6/http';
import exec from 'k6/execution';

// 초당 RATE 건을 DURATION 동안 Envoy 로 보낸다(도착률 고정. 서버가 느려져도 보내는 양은 그대로).
// ENVOYS 에 Envoy 여러 대를 쉼표로 주면 요청을 차례로 나눠 보낸다(로드 밸런서 여러 대 흉내).
export const options = {
  discardResponseBodies: true,
  scenarios: {
    work: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 400),
      timeUnit: '1s',
      duration: __ENV.DURATION || '90s',
      preAllocatedVUs: 200,
      maxVUs: 2000,
    },
  },
  summaryTrendStats: ['avg', 'p(50)', 'p(90)', 'p(99)', 'max'],
};

const envoys = (__ENV.ENVOYS || 'envoy:10000').split(',');

export default function () {
  const e = envoys[exec.scenario.iterationInTest % envoys.length];
  http.get(`http://${e}/work`, { timeout: '10s' });
}
