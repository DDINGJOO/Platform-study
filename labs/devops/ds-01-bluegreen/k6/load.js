// 초당 RATE 건을 DURATION 동안 고르게 보낸다. 응답 본문의 버전을 ver 카운터의 태그로 남긴다.
import http from 'k6/http';
import { Counter } from 'k6/metrics';

const ver = new Counter('ver');
const TARGET = __ENV.TARGET || 'http://ds-01-control-plane:30080/';

export const options = {
  scenarios: {
    steady: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 50),
      timeUnit: '1s',
      duration: __ENV.DURATION || '90s',
      preAllocatedVUs: 20,
      maxVUs: 200,
    },
  },
  // NOREUSE=1 이면 요청마다 새 연결. 기본은 keep-alive 로 연결을 재사용한다
  noConnectionReuse: __ENV.NOREUSE === '1',
  // 실패해도 멈추지 않는다. 실패 건수 자체가 측정 대상이다
  thresholds: {},
};

export default function () {
  const res = http.get(TARGET, { timeout: '2s' });
  const v = res.status === 200 ? res.body.split(' ')[0] : 'fail';
  ver.add(1, { v: v });
}
