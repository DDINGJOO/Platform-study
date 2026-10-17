# pii-07-log-leaks: 개인정보가 로그로 새는 다섯 경로와 막는 법

블로그 글 「7편. 개인정보가 로그로 새는 다섯 경로와 막는 법」의 재현 실습입니다. Docker 는 쓰지 않습니다.
호스트의 Java 25 와 `javac` 만 있으면 됩니다(mvn/gradle 불필요). 값은 전부 가짜입니다(생년월일 000000, 국번 0000).

## 무엇을 재현하나

| 경로 | 코드 | 새는 모양 |
|---|---|---|
| ① DTO 통째 로깅 | `log.info("가입 요청 {}", dto)` | Lombok `@Data` 와 record 의 toString 이 모든 필드를 찍는다 |
| ② 예외 메시지 | `new IllegalArgumentException("... " + v)` | 형식이 틀린 값이 메시지에 그대로 실린다 |
| ③ 원인 예외 · 제약 위반 | `throw new IllegalStateException("...", e)` | H2 의 유니크 위반 메시지 `VALUES ( /* 1 */ '...' )` 가 `Caused by:` 로 찍힌다 |
| ④ HTTP 클라이언트 덤프 | Apache HttpClient 5.6.5, `org.apache.hc.client5.http.wire` DEBUG | 요청 본문과 응답 본문이 그대로 찍힌다. 한글은 `[0xffffffea]` 바이트 표기로 |
| ⑤ 정규식이 놓치는 입력 | `log.info("검색 q={}", q)` | 공백·en dash·전각 숫자·구분자 없음·뒷자리만·URL 인코딩 |

막는 법(하나씩 켠다): `@ToString.Exclude`, `@ToString.Include` 마스킹 메서드, `onlyExplicitlyIncluded`,
Logback `%replace` (메시지만 / 예외 포함 / 넓힌 정규식), `TurboFilter`(@Pii 인자 차단), wire 로거 끄기,
코드 규칙(DTO 통째 로깅 금지, 예외 메시지에 길이만, 원인 예외 떼기), ArchUnit 규칙 세 개.

## 실행

```bash
./scripts/build.sh                       # Maven Central 에서 jar 를 받아(sha1 대조) javac 로 빌드. LIB_DIR 로 jar 위치 변경 가능
./scripts/run.sh d0-none                 # 아무것도 안 켠 채 다섯 경로를 돌린다 → out/d0-none.log
./scripts/run.sh x mask=FULL_WIDE wire=INFO dto=allow code=safe turbo=true
./scripts/matrix.sh                      # 막는 법을 하나씩 켠 11번의 실행 → out/matrix.txt
python3 scripts/compare.py out/d0-none.log out/d10-all.log   # 새는 쪽 / 막은 쪽을 경로별로 붙여 본다
python3 scripts/leaks.py --lines out/d0-none.log             # 값이 남은 줄
./scripts/arch.sh                        # ArchUnit 규칙 세 개 → out/arch.txt
```

`leaks.py` 는 wire 바이트 표기를 되돌리고, URL 인코딩을 풀고, NFKC 로 전각을 반각으로 바꾸고, 공백·점·대시를 지운 뒤
가짜 값(이름, 주민번호 뒷자리, 전화번호 숫자열)을 찾습니다. 표의 숫자는 "남은 값의 개수(줄마다 종류 수의 합)"입니다.

## 결과 (2026-10-17, 같은 행렬 3번 실행, 세 번 모두 같음)

```
실행           ①    ②    ③    ④    ⑤   합계
d0-none        6    1    1    4   10     22
d1-exclude     5    1    1    4   10     21
d2-include     3    1    1    4   10     19
d3-allow       3    1    1    4   10     19
d4-msg         2    1    1    1    9     14
d5-full        2    1    0    1    9     13
d6-wide        2    0    0    1    2      5
d7-turbo       0    1    1    4   10     16
d8-wireoff     6    1    1    0   10     18
d9-code        0    0    0    4   10     14
d10-all        0    0    0    0    2      2
```

- d2/d3 의 ① 3개는 record 한 줄이다. Lombok 은 record 의 toString 을 건드리지 않는다
- d4~d6 의 ① 2개, ④ 1개는 이름이다. 정규식은 이름을 모른다. wire 로그의 이름은 바이트 표기라 더 안 보인다
- d4(`%replace(%msg)`)는 ③ 을 못 막는다. PatternLayout 이 자동으로 붙이는 `%ex` 는 replace 밖에 있다
- d10 에 남은 2개는 `뒷자리 9876543` 과 `010%200000%200000` 이다
- ArchUnit 규칙 1(toString 이 @Pii 필드·getter 를 직접 부르면 위반)은 SignupData·SignupExclude 를 잡고 SignupRecord 는 못 잡는다. record toString 은 invokedynamic 으로 ObjectMethods.bootstrap 을 부르고, 필드는 부트스트랩 인자의 REF_getField 핸들에만 있어 ArchUnit 이 필드 접근으로 세지 않는다. 직접 접근만 보므로 maskedRrn() 같은 메서드를 거친 접근도 보지 않는다
- 규칙 2 는 LeakyMemberRepo 를 잡는다
- 규칙 3(@Pii record 의 toString 에 필드 접근도 메서드 호출도 없으면 위반)은 SignupRecord 를 잡고 SignupRecordSafe 는 통과시킨다. 위반 합계 7건
- 규칙 3 첫 실행(`out/arch-rule3-first.txt`)에서는 SignupRecordSafe 의 toString 이 rrn 을 직접 읽어 규칙 1 에 걸렸다. 마스킹 메서드를 거치게 바꿨다
- `%nopex` 는 필수가 아니다. Logback 1.5.18 은 %replace 안의 %ex 를 예외 변환어로 인정해 자동 %ex 를 붙이지 않았고, %nopex 만 뺀 설정도 같은 13개였다. 의도를 적어 두는 용도로 남겼다
- LabCrypto 는 실습 전용이다(HMAC 키와 AES 키 분리, 둘 다 소스에 박힌 값). 키를 나눈 뒤 다시 돌려도 행렬 숫자는 같았다
- 첫 ArchUnit 실행(`out/arch-first.txt`)에서 규칙 2 가 SafeMemberRepo 도 잡았다. 예외 클래스가 `super(m, null, false, false)` 를 불렀기 때문이다(값이 null 이어도 시그니처에 Throwable 이 있다). `super(m)` 으로 바꿔 다시 돌렸다

## 파일

- `src/lab/Lab.java` 다섯 경로, `src/lab/dto/` DTO 다섯 벌, `src/lab/repo/` 새는/막은 저장소, `src/lab/guard/PiiArgTurboFilter.java`, `src/lab/arch/PiiRules.java`
- `conf/logback.xml` 마스킹 appender 네 벌과 wire 로거 수준, TurboFilter 스위치
- `out/` 원자료(d*.log, matrix*.txt, arch*.txt)
- `src/lab/dto/SignupRecordSafe.java` 는 ArchUnit 규칙 3 확인용이고 로그 실행에는 쓰지 않는다
