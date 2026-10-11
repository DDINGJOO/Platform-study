import http from 'k6/http';

// 네 대에 똑같이 초당 RATE 건(기본 200)을 보낸다. 응답을 5초 넘게 기다리지 않는다.
// 하위 지연 바꾸기는 scripts/phases.sh 가 한다.
const targets = (__ENV.TARGETS || 'app-fixed,app-gradient2-windowed,app-vegas').split(',');
const scenarios = {};
for (const t of targets) {
  scenarios[t] = {
    executor: 'constant-arrival-rate',
    rate: Number(__ENV.RATE || 200), timeUnit: '1s', duration: __ENV.DURATION || '13m',
    preAllocatedVUs: 50, maxVUs: 1500,
    exec: 'hit',
    env: { URL: `http://${t}:8080/work` },
    tags: { target: t },
  };
}
// 대상별 숫자를 요약에 따로 찍으려고 항상 통과하는 threshold 를 건다(k6 는 threshold 가 걸린 하위 지표만 따로 보여 준다).
const thresholds = {};
for (const t of targets) {
  thresholds[`http_req_duration{target:${t},status:200}`] = ['max>=0'];
  thresholds[`http_reqs{target:${t},status:200}`] = ['count>=0'];
  thresholds[`http_reqs{target:${t},status:429}`] = ['count>=0'];
  thresholds[`http_reqs{target:${t},status:0}`] = ['count>=0'];   // 5초 타임아웃 등 응답 없음
}
export const options = { scenarios, thresholds, discardResponseBodies: true };

export function hit() {
  http.get(__ENV.URL, { timeout: '5s' });
}
