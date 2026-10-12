# 소스 코드 관찰 실습-2: 서비스 열 개에서 취약한 라이브러리를 쓰는 곳을 SBOM 으로 찾는다

스프링 부트 서비스 열 개(한 Gradle 빌드의 하위 프로젝트)를 띄우고, 몇 개에 옛 logback 을 운영에서 볼 법한 방식으로 숨긴다.
"logback-core 1.5.13 미만(CVE-2024-12798 수정 이전)을 쓰는 서비스"를 세 가지 방법으로 찾고, 실행 중인 JVM 에 직접 물은 정답과 비교한다.

| 방법 | 무엇을 읽나 |
|---|---|
| A. Git HEAD 빌드 파일 | 작업 저장소 HEAD 의 `sNN/build.gradle` 에서 `ch.qos.logback:logback-core:버전` 꼴 |
| B. 배포본 POM → Maven | 운영에 떠 있는 커밋으로 만든 POM 을 `mvn dependency:list` 로 해소 |
| C. 실행 중 SBOM | 플랫폼(`docker ps --filter label=lab.co02=1`)에서 받은 서비스마다 `/actuator/sbom/application` |
| 정답 | 서비스마다 넣은 `/lab/logback`: logback 클래스를 실제로 읽은 jar 위치 |

## 서비스

| 서비스 | 장치 |
|---|---|
| s01, s10 | 기본형(webmvc, webflux) |
| s02 | `resolutionStrategy.force` 로 logback 1.5.12 |
| s03 | `logback-core:1.5.12` 직접 선언(충돌 해소로 BOM 버전이 이김) |
| s04 | 커밋1 에 s02 와 같은 force, 커밋2 에서 삭제. 운영에는 커밋1 이미지 |
| s05 | Log4j2, `spring-boot-starter-logging` 제외 |
| s06 | 빌드는 기본형. 이미지(`docker/Dockerfile.s06`)에서 옛 logback 을 `loader.path` 로 얹음. jar 는 `services/ops/overlay.gradle` 이 받는다 |
| s07 | 버전 카탈로그 `logback = { strictly = "1.5.12" }` |
| s08 | `logback-core:1.5.+` |
| s09 | `logback-classic` 버전 없이 선언 |

## 돌리기

```bash
cd labs/devops/co-02-sbom-inventory
python3 scripts/lab.py prepare     # CO02_WORK(기본 /tmp/co-02-work)에 git 저장소·커밋 둘, jar·POM·이미지 빌드
python3 scripts/lab.py deploy      # 서비스 열 개를 30101~30110 에 하나씩(기동이 끝나면 다음)
python3 scripts/lab.py query       # results/query.txt, query.json
python3 scripts/lab.py trace s04   # results/trace.txt
python3 scripts/lab.py down        # 컨테이너, co02/* 이미지, 빌드 캐시 볼륨 삭제
```

- 필요한 것: Docker, Python 3, git. 빌드는 `gradle`, `maven` 컨테이너 안에서 하고 캐시는 이 compose 프로젝트의 볼륨에만 둔다
- 첫 `prepare` 는 의존성 내려받기로 몇 분 걸린다
- 컨테이너마다 `-m 256m`, `JAVA_TOOL_OPTIONS=-Xmx72m -XX:+UseSerialGC -XX:TieredStopAtLevel=1`

## 버전

| 부품 | 버전 | 고른 이유 |
|---|---|---|
| Spring Boot | 4.1.1 | 다른 실습과 같은 최신 안정판. `/actuator/sbom` 은 3.3 부터 |
| CycloneDX Gradle plugin | 3.0.0 | 스프링 부트 4.1.1 문서(Generate a CycloneDX SBOM)의 예시 버전 |
| gradle-git-properties | 4.0.1 | 문서 예시의 2.4.1 은 Gradle 9.8.1 에서 실패한다(아래 함정) |
| Gradle | 9.8.1 (`gradle:9.8.1-jdk21`) | 최신 안정판 |
| Maven | 3.10.0 (`maven:3.10.0-eclipse-temurin-21`) | 최신 GA. B 방법의 해소용 |
| logback | BOM 기본 1.5.38, 옛 버전 1.5.12 | 1.5.12 는 CVE-2024-12798 수정(1.5.13) 직전 |

## 결과

2026-10-12, 처음부터 다시 돌린 회차. 원자료는 `results/`.

| 서비스 | A. Git HEAD | B. POM→Maven | C. SBOM | 정답(JVM) |
|---|---|---|---|---|
| s01 | 없음 | 1.5.38 | 1.5.38 | 1.5.38 |
| s02 | 1.5.12 | 1.5.38 | 1.5.12 | **1.5.12** |
| s03 | 1.5.12 | 1.5.12 | 1.5.38 | 1.5.38 |
| s04 | 없음 | 1.5.38 | 1.5.12 | **1.5.12** |
| s05 | 없음 | 없음 | 없음 | 없음 |
| s06 | 없음 | 1.5.38 | 1.5.38 | **1.5.12** (`/app/extra` 의 jar) |
| s07 | 없음 | 1.5.12 | 1.5.12 | **1.5.12** |
| s08 | `1.5.+` (판정 불가) | 해소 실패 | 1.5.38 | 1.5.38 |
| s09 | classic 만, 버전 없음 | 1.5.38 | 1.5.38 | 1.5.38 |
| s10 | 없음 | 1.5.38 | 1.5.38 | 1.5.38 |

| 방법 | 정탐 | 오탐 | 미탐 | 맞게 제외 | 판정 불가 |
|---|---|---|---|---|---|
| A. Git HEAD 빌드 파일 | 1 | 1 | 3 | 4 | 1 |
| B. 배포본 POM 을 Maven 으로 | 1 | 1 | 3 | 4 | 1 |
| C. 실행 중 SBOM | 3 | 0 | 1 | 6 | 0 |

- 질의는 다섯 번 돌렸다. `results/query.txt` 에는 마지막 회차만 남는다(회차별 판정 파일은 남기지 않았다)
- 질의 시간(캐시가 찬 3~5회차): A 0.00s, B 27.4 / 24.8 / 23.3s(Maven 컨테이너 하나에서 POM 열 개를 차례로), C 0.07 / 0.04 / 0.04s, 정답 0.04 / 0.03 / 0.02s, 플랫폼 질의(`docker ps`) 0.04s.
  1회차는 Maven 캐시가 비어 B 34.3s. 2회차 B 986.9s 는 원인을 확인하지 못해 버렸다(다른 실습 두 개가 같은 Docker 에서 돌고 있었다)
- 운영본 → 소스: 플랫폼(이미지 `co02/s04:9d208f4`, 라벨 `org.opencontainers.image.revision`) → 앱(`/actuator/info` `git.commit.id`) → 저장소(`git rev-parse`, HEAD 와 다름) → 소스(`git show 9d208f4:s04/build.gradle` 의 force 줄). 4단계
- SBOM: CycloneDX 1.6, 구성 요소 56~79개(`results/extra.txt`)

## 돌리다 만난 함정

- **gradle-git-properties 2.4.1 은 Gradle 9.8.1 에서 깨진다.** `generateGitProperties` 가
  `No signature of method: java.io.FilterOutputStream.write() is applicable for argument types: (Integer)` 로 실패한다. 4.0.1 로 올렸다.
- **Gradle 은 동적 버전 `1.5.+` 를 POM 에 그대로 적고, Maven 은 그 POM 을 풀지 못한다**(`dependency: ch.qos.logback:logback-core:jar:1.5.+`).
  처음 스크립트는 이 실패를 "logback 없음"으로 셌다. 지금은 `(해소 실패)` 로 따로 표시한다.
- **처음에는 s06 의 옛 jar 를 s06 빌드 파일에서 받았다.** 그러면 A(빌드 파일 정규식)가 그 줄을 보고 우연히 맞힌다.
  "운영 쪽 오버레이"라는 설정에 맞게 `services/ops/overlay.gradle` 로 옮겼다.
- **옛 logback(1.5.12)으로 내린 서비스는 로그 형식이 깨진다.** 스프링 부트 4.1.1 기본 설정의 `%clr` 변환기를 등록하지 못해
  `PARSER_ERROR` 가 섞여 찍힌다. 앱은 정상 기동하고 헬스 체크도 UP 이다.
- 같은 Docker 를 쓰는 다른 실습의 지연 측정에 영향을 덜 주려고 서비스를 동시에 띄우지 않고 하나씩 띄운다.
