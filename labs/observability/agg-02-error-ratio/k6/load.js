import http from 'k6/http';
import exec from 'k6/execution';

// 초당 요청 수를 단계별로 바꾼다(8분). 8:00 이후 트래픽 0 구간은 run.sh 가 k6 없이 기다린다. 열 건 중 한 건은 app-b, 나머지는 app-a 로 간다.
// 실패율은 k6 가 아니라 run.sh 가 시각에 맞춰 바꾼다.
export const options = {
  scenarios: {
    orders: {
      executor: 'ramping-arrival-rate',
      startRate: 20,
      timeUnit: '1s',
      preAllocatedVUs: 50,
      stages: [
        { target: 20, duration: '2m' },   // 0:00-2:00  평소
        { target: 100, duration: '30s' }, // 2:00-2:30  피크로 오른다
        { target: 100, duration: '1m30s' },// 2:30-4:00  피크
        { target: 10, duration: '30s' },  // 4:00-4:30  한산해진다
        { target: 10, duration: '2m' },   // 4:30-6:30  한산 (4:30 장애)
        { target: 20, duration: '0s' },
        { target: 20, duration: '1m30s' },// 6:30-8:00  app-b 만 고장
      ],
    },
  },
};

export default function () {
  const t = exec.scenario.iterationInTest % 10 === 0 ? 'app-b' : 'app-a';
  http.post(`http://${t}:8080/orders`, null, { tags: { target: t } });
}
