// 세 엔드포인트를 섞어서 부른다. DURATION 동안 VU 10개.
import http from 'k6/http';

export const options = { vus: 10, duration: __ENV.DURATION || '3m' };

const BASE = 'http://app:8080';
export default function () {
  const r = Math.random();
  if (r < 0.4) http.get(`${BASE}/price/sku-${Math.floor(Math.random() * 50)}`);
  else if (r < 0.7) http.get(`${BASE}/report`);
  else http.get(`${BASE}/checkout`);
}
