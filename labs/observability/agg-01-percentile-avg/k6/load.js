import http from 'k6/http';
import exec from 'k6/execution';

// 초당 RATE 건(기본 60)을 인스턴스 세 대에 나눠 보낸다.
// C_EVERY=3(기본)이면 세 건마다 한 건이 app-c 로 가서 세 대가 같은 양을 받는다.
// C_EVERY=20 이면 app-c 는 5%만 받고 나머지는 app-a, app-b 가 반씩 받는다.
export const options = {
  scenarios: {
    work: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 60),
      timeUnit: '1s',
      duration: __ENV.DURATION || '3m',
      preAllocatedVUs: 50,
    },
  },
};

const cEvery = Number(__ENV.C_EVERY || 3);

export default function () {
  const i = exec.scenario.iterationInTest;
  const t = i % cEvery === 0 ? 'app-c' : (i % 2 === 0 ? 'app-a' : 'app-b');
  http.get(`http://${t}:8080/work`, { tags: { target: t } });
}
