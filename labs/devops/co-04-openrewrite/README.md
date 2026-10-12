# co-04-openrewrite: grep, OpenRewrite, 커버리지가 센 호출 수가 다르다

소스 코드 관찰 시리즈 실습-4 의 코드. 작은 HTTP 서버(`app/`) 안에 SLF4J `Logger.info` 호출과,
글자만 비슷한 것(주석, 문자열, JUL Logger, 사내 AuditLogger)을 섞어 두고 세 방법으로 센다.

1. `grep -rnE '\b(log|logger|LOG)\.info\('`
2. OpenRewrite `org.openrewrite.java.search.FindMethods` (`methodPattern=org.slf4j.Logger info(..)`),
   `matchOverrides` 끔/켬, 그리고 로깅 라이브러리를 클래스패스에서 뺀 경우
3. JaCoCo 에이전트를 붙인 앱에 k6 로 60초 부하를 건 뒤 실행된 줄

정답표는 소스 꼬리 주석의 `#S<n>`(대상 호출 9곳), `#G<n>`(대상이 아닌 곳 4곳)이다.

## 버전

| 구성 요소 | 버전 | 메모 |
|---|---|---|
| Maven | 3.10.0 | `maven:3.10.0-eclipse-temurin-21-noble` |
| rewrite-maven-plugin | 6.46.1 | Maven Central 에 있는 마지막 판(2026-08-12). 6.47 이후는 OpenRewrite 모듈이 인증이 필요한 Code Genome Project 저장소(`https://artifacts.codegenomeproject.org/maven`)로 옮겨 가 Central 에 없다 |
| SLF4J / Logback | 2.0.20 / 1.6.5 | |
| JaCoCo | 0.8.15 | agent(runtime), cli(nodeps) |
| k6 | 2.3.0 | `grafana/k6:2.3.0` |
| JDK | Temurin 21 | |

## 돌리는 법

호스트 포트는 31180(앱) 하나만 쓴다. JaCoCo 6300 번은 compose 네트워크 안에서만 쓴다.

```bash
cd labs/devops/co-04-openrewrite
./scripts/lab.sh build
./scripts/lab.sh grep
./scripts/lab.sh rewrite 4     # 기본값과 matchOverrides 를 4번씩. 첫 회는 의존성 내려받기
./scripts/lab.sh notypes
./scripts/lab.sh runtime
./scripts/lab.sh score
./scripts/lab.sh down
```

## 결과 (results/score.txt)

```
grep                     찾은 곳  9  정탐 5  과다 4  누락 4
FindMethods 기본           찾은 곳  8  정탐 8  과다 0  누락 1
FindMethods matchOverrides 찾은 곳  9  정탐 9  과다 0  누락 0
FindMethods 타입 없음        찾은 곳  0  정탐 0  과다 0  누락 9
JaCoCo(부하 중 실행)          찾은 곳  6  정탐 6  과다 0  누락 3
```

## 돌리다 만난 함정

- **패치 파일 위치.** 6.46.1 은 `target/rewrite/rewrite.patch` 에 쓴다(문서 한 곳에는 `target/site/rewrite/` 로 적혀 있다).
  처음에 그쪽을 봐서 "no patch" 가 났다.
- **rewrite-maven-plugin 최신판은 Central 에 없다.** 문서의 6.50.0 은 Code Genome Project(인증 필요)에만 있다. 6.46.1 을 쓴다.
- **타입이 없으면 조용히 0건.** `-Dnotypes` 로 로깅 라이브러리를 빼고 `dryRunNoFork` 를 돌리면 종료 코드 0, 경고 없이 결과가 비어 있다.
  `dryRun` 은 `process-test-classes` 까지 포크해 컴파일하므로 이 실험에는 쓸 수 없다.
- **죽은 분기는 JaCoCo 에 존재하지 않는다.** `static final boolean` 상수 조건의 블록은 javac 가 바이트코드를 만들지 않아 리포트에 줄이 없다.
- **MethodCalls 의 method 칸에 윗줄 주석이 붙는다.** LST 가 주석을 다음 노드의 prefix 로 보존하기 때문으로 보인다.
- **JDK HttpServer 응답이 약 41ms 로 일정하다.** 부하 결과의 지연은 이 실습의 관심사가 아니라 손대지 않았다.
