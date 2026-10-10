// 사용자 USERS 명이 한 번씩 주문한다. user_id 가 USERS 가지 값이 된다.
import http from 'k6/http';
import { check } from 'k6';
import exec from 'k6/execution';

const USERS = parseInt(__ENV.USERS || '1000');

export const options = {
  scenarios: {
    users: { executor: 'shared-iterations', vus: 20, iterations: USERS, maxDuration: '5m' },
  },
};

export default function () {
  const id = exec.scenario.iterationInTest + 1;
  const res = http.get(`http://app:8080/checkout?user=u${id}`);
  check(res, { '200': (r) => r.status === 200 });
}
