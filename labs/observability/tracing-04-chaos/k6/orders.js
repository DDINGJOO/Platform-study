import http from 'k6/http';
import { sleep } from 'k6';

export const options = { vus: 5, duration: __ENV.DURATION || '60s' };

const skus = ['A-100', 'A-100', 'C-300', 'C-300', 'B-200'];

export default function () {
  const sku = skus[Math.floor(Math.random() * skus.length)];
  http.post('http://order:8080/orders', JSON.stringify({ sku, qty: 1 }), {
    headers: { 'Content-Type': 'application/json' },
  });
  sleep(0.2);
}
