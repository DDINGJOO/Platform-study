import http from 'k6/http';
import { sleep } from 'k6';

// 닫힌 모델. VU 10개가 각자 "보내고, 응답을 받고, 100ms 가 될 때까지 쉰다"를 반복한다.
// 서버가 빠르면 VU 하나가 초당 10건, 합쳐서 초당 100건이 나간다.
// 응답이 100ms 를 넘기면 쉬지 않고 바로 다음 요청을 보낸다. 그래도 그사이 보냈어야 할 요청은 사라진다.
const TARGET = __ENV.TARGET || 'app-closed';
const PACE = Number(__ENV.PACE_MS || 100) / 1000;

export const options = {
  scenarios: {
    closed: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS || 10),
      duration: __ENV.DURATION || '5m',
    },
  },
};

export default function () {
  const start = Date.now();
  http.get(`http://${TARGET}:8080/work`);
  const left = PACE - (Date.now() - start) / 1000;
  if (left > 0) sleep(left);
}
