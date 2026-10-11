# 트래픽 관리 실습

블로그 「트래픽 관리」 시리즈(개념 7편)에 붙는 실습 코드다. 글은 `posts/CS/Observability/traffic-management/` 의 `실습-N` 편.
실습마다 디렉터리 하나, 각 디렉터리의 `README.md` 에 돌리는 법·버전·함정·결과가 있다.

| 실습 | 디렉터리 | 도구 | 잇는 개념 글 |
|---|---|---|---|
| 실습-1 느린 서버 한 대를 라운드로빈과 P2C가 다르게 피한다 | `tm-01-p2c/` | Envoy 1.39.3 | 1편 |
| 실습-2 빨리 실패하는 서버가 트래픽을 빨아들이고 outlier detection이 빼낸다 | `tm-02-outlier/` | Envoy 1.39.3 | 2편 |
| 실습-3 갓 뜬 인스턴스에 slow start를 걸면 무엇이 달라지나 | `tm-03-slow-start/` | Envoy 1.39.3 | 3편 |
| 실습-4 Envoy 헤지 요청으로 꼬리 지연을 깎는다 | `tm-04-hedge/` | Envoy 1.39.3 | 4편 |
| 실습-5 세 겹 재시도가 부하를 몇 배로 늘리는지 센다 | `tm-05-retry/` | Envoy 1.39.3 | 5편 |
| 실습-6 같은 장애에 비율 제한, 벌크헤드, 서킷 브레이커를 걸어 본다 | `tm-06-resilience4j/` | Resilience4j 2.4.0 | 6편 |
| 실습-7 동시성 한계를 스스로 찾는 리미터를 돌려 본다 | `tm-07-adaptive/` | concurrency-limits 0.5.4 | 7편 |

`common-envoy/` 는 실습-1~3 이 같이 쓰는 백엔드 앱(Spring Boot)·k6 스크립트·Grafana 설정이다.
결과는 Envoy 통계와 앱 지표를 Prometheus 로 긁어 Grafana 로 본다. `out/` 에는 실행 기록이 남는다(큰 로그는 gitignore).
