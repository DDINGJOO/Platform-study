# DependencyDown

> 심각도 warning · 마지막 점검 2026-10-11

## 무엇을 뜻하나
해당 인스턴스가 2초마다 부르는 db 헬스 체크가 15초 넘게 실패했다.

## 확인 순서
1. `DBDown` 도 울리고 있으면 [DBDown](DBDown.md) 절차를 따른다. 이 경고는 그동안 억제된다.
2. `DBDown` 은 조용한데 이 경고만 울리면, 그 인스턴스에서 db 로 가는 경로를 본다:
   `docker compose exec <인스턴스> wget -qO- -T 2 http://db:8080/health`

## 올려 보낼 때
한 서비스의 인스턴스 전부가 울리면 그 서비스 담당에게 알린다. 업무 시간 안에 처리한다.
