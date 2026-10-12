// 평소 트래픽: 주문, 결제, 검색, 목록. /admin/legacy 와 음수 id(예외 경로)는 보내지 않는다.
import http from 'k6/http';
import { check } from 'k6';

export const options = { vus: 10, duration: '60s' };
const BASE = __ENV.BASE || 'http://localhost:31180';
const paths = ['/orders?id=', '/payments?id=', '/search?q=', '/items?q='];

export default function () {
  const p = paths[Math.floor(Math.random() * paths.length)];
  const r = http.get(`${BASE}${p}${Math.floor(Math.random() * 100000)}`);
  check(r, { '200': (x) => x.status === 200 });
}
