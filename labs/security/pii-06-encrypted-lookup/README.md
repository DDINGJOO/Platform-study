# pii-06 암호화한 컬럼을 WHERE 로 찾는 세 방식

JPA `AttributeConverter` 로 암호화한 컬럼을 `findByXxx` 로 찾을 때 세 방식이 무엇을 내주는지 잰다.

| 컬럼 | 방식 |
|---|---|
| `ssn_det` | ① 결정적 암호화(Tink AES256_SIV). 같은 평문이면 같은 암호문 |
| `ssn_gcm` | ② 랜덤 IV(AES-256-GCM, 12바이트 IV 매번 새로) |
| `ssn_bidx` | ③ 블라인드 인덱스: 정규화한 평문의 HMAC-SHA256(별도 키), `ssn_gcm` 과 한 쌍 |
| `ssn_bidx12` | ③' HMAC 을 12비트로 자른 짧은 인덱스(일부러 충돌을 낸다) |

비교하려고 한 테이블에 모았다. 실제로는 ① 한 컬럼, 또는 ③ 두 컬럼 한 쌍만 둔다.
데이터는 전부 가짜다(주민번호 모양이지만 생년월일 자리가 `000000`). 키는 `seed` 가 새로 만들어 `out/lab-keys.properties` 에 평문으로 둔다(실습용, 커밋하지 않는다).

## 실행

```bash
./scripts/build.sh        # JDK 21 이상. app/build/libs/lookup.jar
./scripts/run_all.sh      # MySQL(127.0.0.1:38060)을 띄우고 세 바퀴 (약 3분)
docker compose down -v
```

모드는 `java -jar app/build/libs/lookup.jar <mode>` 로 하나씩 돌릴 수도 있다: `seed <행 수>`, `demo`, `bench <반복>`, `freq`, `rotate`, `ivreuse`.
`demo` 에 `--logging.level.org.hibernate.SQL=debug --logging.level.org.hibernate.orm.jdbc.bind=trace` 를 주면 Hibernate 가 바인딩한 값(컨버터를 거친 암호문)이 보인다.

## 결과

주의: `rotate` 의 ② GCM 회전 시간에는 절반 시점의 검증(전 행 복호화)과 정답 세기(전 행 복호화 한 번 더)가 들어 있다. 순수 다시 쓰기 시간보다 그만큼 길게 찍힌다. ① 은 절반 시점 조회를 시간에서 뺐고, ③ 은 인덱스 조회 두 번(1ms 안쪽)만 들어 있다.

`results/summary.txt` 에 세 바퀴 요약이 있다. `results/` 의 나머지는 글의 실행 화면 원자료다. `out/` 은 원자료(실행 시각 포함)라 커밋하지 않는다.

버전: MySQL 8.4, Spring Boot 4.1.1, Hibernate ORM 7.4.5.Final, Tink 1.23.0, Java 25.0.3, Docker 29.5.3.
