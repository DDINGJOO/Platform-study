# co-03-resolution: Maven과 Gradle이 같은 의존성 그래프를 다르게 푼다

소스 코드 관찰 시리즈 실습-3 의 코드. 파일 기반 Maven 저장소에 작은 합성 라이브러리를 올려 두고,
같은 소스와 같은 의존성 선언을 Maven 과 Gradle 로 빌드해서 jar 에 무엇이 들어가는지, 실행하면 어디서
깨지는지, 미사용/미선언 분석기가 무엇을 보고하는지 본다. 끝으로 쓰지 않는 Spring Data REST starter 가
Spring Boot 앱에 무엇을 더하는지 잰다.

## 구성

| 경로 | 내용 |
|---|---|
| `libs/` | 합성 라이브러리 소스와 `libs.txt`(이름, 버전, 의존성). `scripts/make-repo.sh` 가 컴파일해 `repo/` 에 Maven 저장소 배치로 올린다 |
| `maven/` | 소비자 모듈 7개(`m1`~`m5`, `an`, `an-decl`). 부모 POM 이 `file:///work/repo` 를 저장소로 쓴다 |
| `gradle/` | 같은 7개 모듈의 Gradle 빌드. 소스는 `maven/<모듈>/src` 를 그대로 쓴다 |
| `boot/` | Spring Boot 앱 둘. `plain`(`-Punused` 로 data-rest, data-jpa, h2 추가), `audit`(`-Prest` 로 data-rest 추가) |
| `scripts/lab.sh` | 단계별 실행. 결과는 `results/` |
| `scripts/boot.py` | Spring Boot 변형 넷의 jar 크기, 기동 시간, 빈 수, 매핑 수, 열린 경로 |

합성 그래프는 이렇다. `c` 2.0 은 1.0 의 `legacy()` 를 지우고 `encodeFast()` 를 더했다.

```
a 1.0 -> c 1.0            (a 는 c.legacy() 를 부른다)
b 1.0 -> d 1.0 -> c 2.0   (d 는 c.encodeFast() 를 부른다)
b 2.0 -> (없음)
x 1.0 -> c 2.0,  y 1.0 -> c 1.0   (둘 다 c.encode() 만 부른다)
e, drv, konst              (분석기 시험용: 안 씀 / 리플렉션으로만 씀 / 상수만 씀)
```

| 모듈 | 선언(순서대로) |
|---|---|
| m1 | a, b |
| m2 | b, a |
| m3 | x, y |
| m4 | y, x |
| m5 | a, b, c 2.0 |
| an | b, e, drv, konst. 코드는 c 를 직접 import 한다(선언 안 함) |
| an-decl | b, c 2.0. 코드는 c 를 직접 import 한다(선언함) |

## 버전

| 구성 요소 | 버전 |
|---|---|
| Maven | 3.10.0 (`maven:3.10.0-eclipse-temurin-21-noble`) |
| maven-dependency-plugin | 3.11.0 |
| Gradle | 9.8.1 (`gradle:9.8.1-jdk21-noble`) |
| dependency-analysis-gradle-plugin | 3.19.2 (`com.autonomousapps.build-health`) |
| Spring Boot | 4.1.1 |
| JDK | Temurin 21 |

## 돌리는 법

호스트 포트는 31081 하나(Spring Boot 앱)만 쓴다. Docker 와 python3 가 필요하다.

```bash
cd labs/devops/co-03-resolution
./scripts/lab.sh repo       # 합성 저장소
./scripts/lab.sh resolve    # 해소 결과와 실행 결과
./scripts/lab.sh analyze    # dependency:analyze, buildHealth
./scripts/remove-check.sh   # 보고된 의존성을 하나씩 빼고 an 실행 (호스트 JDK 17+)
./scripts/const-check.sh    # 상수를 쓰는 방식별로 상수 풀에 클래스 참조가 남는지 (extra/const)
# 컨테이너 JDK 21 로: docker run --rm -v "$PWD":/work -w /work maven:3.10.0-eclipse-temurin-21-noble bash scripts/const-check.sh
./scripts/lab.sh bump       # b 를 2.0 으로 올리고 컴파일
./scripts/lab.sh boot       # Spring Boot 측정 (RUNS=4 기본)
./scripts/lab.sh down
```

## 결과 (results/)

| 파일 | 내용 |
|---|---|
| `resolve-maven.txt`, `resolve-gradle.txt`, `resolve-summary.txt` | 모듈별 해소 트리와 실행 결과. m1, m2, m4 에서 고른 c 가 다르다 |
| `analyze-maven.txt`, `analyze-gradle.txt` | 두 분석기 모두 미선언 1(an:c), 미사용 3(an:e, an:drv, m5:c) |
| `const-check-jdk21.txt`, `const-check-jdk25.txt` | 상수 사용 방식별 상수 풀의 `Class lab/konst/K` 항목 수(표현식 1, case 라벨 0, 어노테이션 0) |
| `remove-check.txt` | drv 를 빼면 ClassNotFoundException, e 와 konst 는 빼도 실행된다 |
| `bump-*.txt` | b 2.0 에서 an 만 컴파일 실패 |
| `boot.txt`, `boot-*.json` | Spring Boot 변형 넷의 측정값과 매핑 목록 |

## 돌리다 만난 함정

- **`mvn -q` 는 `dependency:analyze` 결과를 지운다.** 결과가 WARNING 으로 찍히는데 `-q` 는 오류만 남긴다.
  처음에 m1~m5 를 `-q` 로 돌려 m5 의 경고를 못 봤다. 스크립트는 `-q` 없이 WARNING 줄만 거른다.
- **오류 수가 두 번 세어진다.** Maven 과 Gradle 모두 컴파일 오류를 요약과 상세에 두 번 찍는다. `sort -u` 로 줄을 합친다.
  Gradle 쪽은 줄 번호까지만 보이고 열 번호가 없어서 같은 줄의 오류 둘이 하나로 합쳐진다(2개로 보인다).
- **상수만 쓰는 의존성(konst)은 이 사례에서 "쓴다"로 나온다.** an 은 상수를 표현식 안에서 쓰고, javac 는 그때 상수 풀에
  `Class lab/konst/K` 를 남긴다(JDK-7153958, JDK-8073372). switch case 라벨이나 어노테이션 값에만 쓰면 남지 않는다
  (`results/const-check-jdk21.txt`, `const-check-jdk25.txt`). 그 두 경우로 분석기를 다시 돌리지는 않았다.
- **`JAVA_TOOL_OPTIONS` 를 주면 모든 java 실행이 `Picked up ...` 을 찍는다.** results 의 로그에서는 지웠다.
- **측정 중 호스트 부하.** boot 측정 동안 load average 가 약 8~10 이었다(다른 실습이 같은 Docker Desktop 에서 돌았다).
