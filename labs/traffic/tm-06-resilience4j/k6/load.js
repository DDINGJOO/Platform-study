import http from 'k6/http';

// 호출하는 쪽 네 대에 같은 부하를 준다: /recommend 초당 40건, /pay 초당 20건.
// 장애 주입은 k6 가 아니라 scripts/phases.sh 가 시간에 맞춰 한다.
const targets = (__ENV.TARGETS || 'order-rl,order-bh,order-cb,order-cbbh').split(',');
const duration = __ENV.DURATION || '11m';

const scenarios = {};
for (const t of targets) {
  for (const [path, rate] of [['recommend', 40], ['pay', 20]]) {
    scenarios[`${t}-${path}`] = {
      executor: 'constant-arrival-rate',
      rate, timeUnit: '1s', duration,
      preAllocatedVUs: 20, maxVUs: 400,
      exec: 'hit',
      env: { URL: `http://${t}:8080/${path}` },
      tags: { target: t, path },
    };
  }
}
// 대상별 숫자를 요약에 따로 찍으려고 항상 통과하는 threshold 를 건다(k6 는 threshold 가 걸린 하위 지표만 따로 보여 준다).
const thresholds = {};
for (const t of targets) {
  thresholds[`http_req_duration{target:${t},path:pay}`] = ['max>=0'];
  for (const st of [200, 429, 502, 503, 0]) {   // 0 = 5초 안에 응답 없음
    thresholds[`http_reqs{target:${t},path:recommend,status:${st}}`] = ['count>=0'];
  }
  thresholds[`http_reqs{target:${t},path:pay,status:0}`] = ['count>=0'];
}
export const options = { scenarios, thresholds, discardResponseBodies: true };

export function hit() {
  http.get(__ENV.URL, { timeout: '5s' });
}
