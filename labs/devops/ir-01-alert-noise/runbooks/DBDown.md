# DBDown

> 경고 규칙: `prometheus/rules.yml` 의 `DBDown` · 심각도 critical(사람을 깨운다) · 마지막 점검 2026-10-11

## 무엇을 뜻하나
Prometheus 가 `db` 의 `/metrics` 를 15초 넘게 긁지 못했다. db 프로세스가 죽었거나, 멈췄거나, 네트워크에서 떨어졌다.

## 영향
db 를 부르는 서비스 다섯(orders, payments, cart, search, inventory) 전부가 요청마다 1초 타임아웃 뒤 실패한다.
이 경고가 울리는 동안 `DependencyDown`, `HighErrorRate`, `HighLatency` 는 Alertmanager 억제 규칙으로 가려진다(`alertmanager/d-inhibit.yml`).

## 확인 순서 (위에서부터, 5분 안에)
1. db 컨테이너 상태: `docker compose ps db` 의 STATUS 가 `Up` 인지, `Paused` 나 `Exited` 인지 본다.
2. 직접 불러 본다: `docker compose exec orders-1 wget -qO- -T 2 http://db:8080/health`. 2초 안에 `ok` 가 안 오면 db 쪽 문제다.
3. 증상이 정말 db 때문인지: Prometheus 에서 `app_dependency_up == 0` 인 인스턴스 수를 본다. 10개 전부면 db, 일부면 그 인스턴스 쪽 네트워크를 의심한다.
4. 최근 변경: db 를 마지막으로 다시 띄우거나 설정을 바꾼 기록(배포 이력)을 본다.

## 완화
- `Paused` 면 `docker compose unpause db`, `Exited` 면 `docker compose up -d db`.
- 되살린 뒤 1분 안에 `up{job="db"}` 가 1, `HighErrorRate` 가 풀리는지 확인한다(에러 비율은 1분 창이라 풀리는 데 최대 1분 걸린다).

## 올려 보낼 때
- 확인 순서 1~2 를 마쳤는데 원인을 모르면 15분 안에 db 담당(2차 온콜)을 부른다.
- 30분 안에 복구 전망이 없으면 장애 지휘를 선언한다.

## 자동화 후보
- 1~2 는 매번 같은 명령이다. 알림에 결과를 붙여 보내는 자동 진단으로 옮길 수 있다.

## 링크
- 대시보드: Prometheus `http://localhost:27090/graph?g0.expr=up%7Bjob%3D%22db%22%7D`
- 경고 규칙: `prometheus/rules.yml`
