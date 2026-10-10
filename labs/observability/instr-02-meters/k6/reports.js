// 보고서 요청을 60초 동안 보낸다. 대부분 50~150ms, 2%는 1~2초짜리 느린 보고서.
import http from 'k6/http';
export const options = { vus: 5, duration: '60s', summaryTrendStats: ['avg', 'med', 'p(90)', 'p(99)', 'max'] };
export default function () {
  const slow = Math.random() < 0.02;
  const ms = slow ? 1000 + Math.floor(Math.random() * 1000) : 50 + Math.floor(Math.random() * 100);
  http.post(`http://app:8080/reports?ms=${ms}`);
}
