import http from 'k6/http';

// 초당 20건을 3분 동안 보낸다.
export const options = {
  scenarios: {
    work: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 20),
      timeUnit: '1s',
      duration: __ENV.DURATION || '3m',
      preAllocatedVUs: 50,
    },
  },
};

export default function () {
  http.get('http://app:8080/work');
}
