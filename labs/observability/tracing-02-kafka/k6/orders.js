import http from 'k6/http';
import { sleep } from 'k6';

export const options = { vus: 5, duration: __ENV.DURATION || '30s' };

export default function () {
  http.post('http://order:8080/orders', JSON.stringify({ sku: 'A-100', qty: 1 }), {
    headers: { 'Content-Type': 'application/json' },
  });
  sleep(0.2);
}
