# dl-02 ON DUPLICATE KEY UPDATE 반환값 실습

MySQL 교착 시리즈 2편 "ON DUPLICATE KEY UPDATE 반환값으로 중복을 판정하면 안 된다"의 재현 실습입니다.

같은 문장 13개(`sql/cases.txt`)를 세 가지 클라이언트로 돌려 반환값을 비교합니다.

| 클라이언트 | CLIENT_FOUND_ROWS |
|---|---|
| mysql CLI | 켜지 않는다 |
| Connector/J 기본값 (`useAffectedRows=false`) | 켠다 |
| Connector/J `useAffectedRows=true` | 켜지 않는다 |

그리고 ODKU·INSERT IGNORE 가 거는 잠금을 `performance_schema.data_locks` 로 봅니다(`scripts/locks.sh`).
Java 쪽은 INSERT IGNORE 가 0 을 돌려준 직후 같은 트랜잭션의 잠금 없는 SELECT 가 그 행을 보는지도 확인합니다(RR/RC).

## 돌리기

필요한 것: Docker, JDK 21 이상(단일 파일 소스 실행), curl.

```bash
./scripts/run_all.sh        # MySQL 8.4 (127.0.0.1:39020) 띄우고 CLI → JDBC 두 모드 → 잠금
docker compose down -v
```

- 드라이버 jar 는 `lib/` 에 Maven Central 에서 받습니다. 버전은 `CJ_VERSION=26.7.0 ./scripts/jdbc.sh` 처럼 바꿉니다. 이미 받아 둔 jar 는 `JAR=<경로>` 로 넘깁니다.
- 원자료는 `out/`(gitignore), 글이 인용하는 요약은 `results/` 에 있습니다.

## 파일

| 파일 | 내용 |
|---|---|
| `sql/schema.sql` | `item`(반환값용), `lk`(잠금용, PK + 보조 유니크) |
| `sql/cases.txt` | 번호·설명·문장. 매 문장 전에 `item` 을 한 행 `(1,'a',1)` 로 되돌린다 |
| `java/RowCount.java` | `executeUpdate` 반환값, 직후 `SELECT ROW_COUNT()`, 경고 코드, `getWarnings()` 뒤의 `ROW_COUNT()`, 스냅숏 확인 |
| `scripts/cli.sh` | 같은 문장을 `mysql -vvv` 로 |
| `scripts/locks.sh` | 트랜잭션 안에서 문장 실행 후 같은 세션의 `data_locks` |

## 결과 (MySQL 8.4.11, Connector/J 9.7.0·26.7.0, JDK 25)

반환값·잠금·스냅숏은 두 번 실행해 같았다. 경고 코드와 `getWarnings()` 뒤 `ROW_COUNT()` 는 측정 순서를 고친 2차 실행 한 번에서 쟀다.

| 문장 | mysql CLI | Connector/J 기본값 | useAffectedRows=true |
|---|---|---|---|
| INSERT IGNORE 새 행 / 중복 | 1 / 0 | 1 / 0 | 1 / 0 |
| ODKU 새 행 | 1 | 1 | 1 |
| ODKU 중복, 무변경 (v=v, 같은 값) | 0 | **1** | 0 |
| ODKU 중복, 값 변경 | 2 | 2 | 2 |
| ODKU 두 행 (무변경 중복 + 새 행) | 1 | 2 | 1 |
| UPDATE 같은 값 | 0 | 1 | **0** |

- INSERT IGNORE 의 경고 코드: 중복 1062, 길이 초과 1265(값은 잘려 저장, 반환값 1).
- `getWarnings()` 를 먼저 부르면 경고가 있던 문장 뒤의 `SELECT ROW_COUNT()` 가 -1.
- RR 에서 읽기 뷰를 먼저 만든 트랜잭션은 INSERT IGNORE 가 0(중복)을 돌려준 행을 잠금 없는 SELECT 로 0행, `FOR SHARE` 로 1행 본다. RC 는 둘 다 1행.
- 잠금은 `results/locks.txt`. ODKU 유니크 중복은 v=v 로 무변경이어도 uk_code 에 X 넥스트키(RC 에서도), PK 에 X,REC_NOT_GAP.
