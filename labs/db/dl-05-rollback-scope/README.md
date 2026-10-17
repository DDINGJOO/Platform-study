# dl-05 교착(1213)과 lock wait timeout(1205)의 롤백 범위, Spring 예외 타입

같은 트랜잭션 모양에서 1213 과 1205 가 각각 무엇을 되돌리는지(mysql CLI), 그리고 Spring 이 그 둘을 어떤 예외로 넘겨주는지(JdbcTemplate, JPA)를 잰다.

| 파일 | 내용 |
|---|---|
| `compose.yaml` | MySQL 8.4 두 대. `mysql`(39050, 기본값), `mysql-rbt`(39051, `--innodb-rollback-on-timeout=ON`) |
| `sql/schema.sql` | `item`(잠글 행 2개), `note`(잠금 앞에 남기는 기록) |
| `scripts/cli.sh s1..s7` | mysql CLI 두 세션 시나리오. 맨 위 주석에 각 시나리오 설명 |
| `scripts/app.sh <port> <mode> [kind] [code]` | Spring Boot 앱. `throw <jdbc|repo|commit|em> <1213|1205>`, `catch <jdbc|repo> <1213|1205>`, `versions`. `ERRCODES=1` 이면 `errcodes/sql-error-codes.xml` 을 클래스패스 루트에 얹는다 |
| `scripts/run_all.sh` | 스택을 띄우고 전부 세 바퀴 → `out/` |

## 실행

```bash
./scripts/build.sh        # JDK 21 이상, Gradle wrapper. app/build/libs/scope.jar
./scripts/run_all.sh
docker compose down -v
```

`cli.sh s5..s7` 은 실행 중에 `innodb_deadlock_detect` 를 끄고 끝나면 다시 켠다(전역 변수라 다른 세션에도 영향).

## 결과

`results/summary.txt` 에 요약, `results/*-r1.txt` 에 대표 1바퀴. 세 바퀴 모두 같았다. `out/` 은 원자료라 커밋하지 않는다.

버전: MySQL 8.4.11, Connector/J 9.7.0, Spring Boot 4.1.1 (Spring Framework 7.0.9), Hibernate ORM 7.4.5.Final, Java 25.0.3.
