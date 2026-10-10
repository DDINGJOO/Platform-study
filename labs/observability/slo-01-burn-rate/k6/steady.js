import http from 'k6/http';

// 초당 RATE 건을 일정하게 보낸다. 실패율은 앱의 /chaos 로 바꾼다.
export const options = {
  scenarios: {
    steady: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 40),
      timeUnit: '1s',
      duration: __ENV.DURATION || '90m',
      preAllocatedVUs: 20,
      maxVUs: 100,
    },
  },
};

export default function () {
  http.get('http://app:8080/api/work');
}
