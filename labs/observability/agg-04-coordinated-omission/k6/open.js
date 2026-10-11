import http from 'k6/http';

// 열린 모델. 응답과 상관없이 초당 RATE 건을 출발시킨다.
// 출발 시각에 쉬는 VU 가 없으면 k6 는 그 반복을 버리고 dropped_iterations 에 센다.
// VUS 를 넉넉히(기본 300) 주면 2초 멈춤 동안 묶이는 200건을 감당한다. 20 으로 주면 모자란다.
const TARGET = __ENV.TARGET || 'app-open';
const VUS = Number(__ENV.VUS || 300);

export const options = {
  scenarios: {
    open: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 100),
      timeUnit: '1s',
      duration: __ENV.DURATION || '5m',
      preAllocatedVUs: VUS,
      maxVUs: VUS,
    },
  },
};

export default function () {
  http.get(`http://${TARGET}:8080/work`);
}
