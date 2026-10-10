import http from 'k6/http';

// TARGET 서비스에 초당 RATE 건을 DURATION 동안 보낸다.
export const options = {
  scenarios: {
    load: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 30),
      timeUnit: '1s',
      duration: __ENV.DURATION || '10m',
      preAllocatedVUs: 50,
      maxVUs: Number(__ENV.MAX_VUS || 600),
    },
  },
  summaryTrendStats: ['avg', 'p(50)', 'p(90)', 'p(99)', 'max'],
};

export default function () {
  http.get(`http://${__ENV.TARGET || 'orders'}:8080/api/work`, { timeout: '30s' });
}
