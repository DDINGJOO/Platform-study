import http from 'k6/http';
import exec from 'k6/execution';

// 초당 RATE 건(기본 50)을 엔드포인트 다섯 개에 돌아가며 보낸다.
const ROUTES = ['checkout', 'order', 'search', 'cart', 'login'];
export const options = {
  scenarios: {
    shop: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 50),
      timeUnit: '1s',
      duration: __ENV.DURATION || '8m',
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
  },
};

export default function () {
  const r = ROUTES[exec.scenario.iterationInTest % ROUTES.length];
  http.get(`http://app:8080/api/${r}`, { tags: { name: r } });
}
