import http from 'k6/http';

// 고객 1만 명 중 한 명의 최근 주문을 초당 RATE 건씩 조회한다. 3초 안에 답이 없으면 실패로 센다.
export const options = {
  scenarios: {
    read: {
      executor: 'constant-arrival-rate',
      rate: Number(__ENV.RATE || 30),
      timeUnit: '1s',
      duration: __ENV.DURATION || '60m',
      preAllocatedVUs: 50,
      maxVUs: 300,
    },
  },
};

export default function () {
  const c = 'C' + String(Math.floor(Math.random() * 10000)).padStart(5, '0');
  http.get(`http://app:8080/orders/recent?customer=${c}`, { timeout: '3s', tags: { name: 'recent' } });
}
