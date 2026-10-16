# pc-02-clone-drift: 복사해 붙인 코드는 함께 고쳐지는가

플랫폼 엔지니어링 시리즈 실습-2 의 코드. 실제 OSS 저장소의 한 릴리스에서 PMD CPD 로 복제 묶음을 찾고,
다음 릴리스까지 1년 동안 어떤 커밋이 묶음의 어느 사본을 바꿨는지 센다. 직접 만든 코드는 쓰지 않는다.

## 대상과 고른 이유

- **spring-projects/spring-framework**, `v6.1.0`(2023-11-16) 의 제품 코드에서 복제를 찾고 `v6.2.0`(2024-11-14) 까지 따라간다.
  창 안의 머지 아닌 커밋 2,395개.
- 서블릿(webmvc)과 리액티브(webflux), RestTemplate 과 RestClient, jdbc 와 r2dbc 처럼 **같은 일을 두 스택으로 하는 코드가 나란히 있다.**
  복사해 붙일 이유가 구조에 있는 저장소라 묶음이 생긴다.
- 창 안의 머지 아닌 커밋 2,395개 중 1,660개(69%)가 메시지에 이슈 번호(gh-NNNNN)를 달고 있어, 한쪽만 고친 이유를 이슈에서 확인할 수 있다.
- 한 회사가 아니라 여러 유지보수자와 외부 기여자가 고친다.

다음 1년(v6.2.0 -> v7.0.0)은 쓰지 않았다. 7.0 은 JSpecify null 표기로 거의 모든 파일을 한 번에 바꿔서, 그 커밋이 "일관 변경"을 부풀린다.

## 정의: Juergens 외(ICSE 2009)와 다른 점

원 논문("Do Code Clones Matter?", <https://arxiv.org/abs/1701.05472>)은 **한 시점의 코드**에서 갭이 있는(type 3) 복제를 찾는다.
묶음 안에 편집 거리가 임계값 이하로 다른 사본 쌍이 하나라도 있으면 *불일치 복제 묶음*(IC)이다. 그다음 그 묶음을 그 시스템의 개발자에게 보여 주고
의도했는지(UIC), 결함인지(F) 판정받는다. 판정할 수 없으면 의도했고 결함 아님으로 친다. 저장소 이력은 일부러 보지 않았다
(7.1 절: 한 커밋에서 복사하고 바로 고친 경우도 세고 싶었고, 산업 시스템 이력이 불완전했다).

이 실습은 그럴 수 없어서 다르게 한다.

| | Juergens 외 2009 | 이 실습 |
|---|---|---|
| 복제 검출 | ConQAT, 문장 단위, 최소 10문장, 편집 거리 5 이하, 메서드 경계를 넘지 않음, 식별자·상수 정규화 | PMD CPD 7.28.0, 토큰 단위, 최소 100 토큰(75, 150 으로도 돌림), **글자가 같거나 값만 다른 묶음**(리터럴만 정규화, 이름이 다른 type 2 는 제외), 메서드 경계를 넘을 수 있음 |
| 불일치의 정의 | 한 시점에 사본끼리 다르다 | 기준 릴리스에서 같았던 사본 중 **일부만 바꾼 커밋**이 있다(Krinke, WCRE 2007 의 이력 기반 정의) |
| 의도 판정 | 그 시스템의 개발자 | 필자가 diff, 커밋 메시지, 이슈, 이후 이력을 읽고 판정. 판단할 수 없으면 의도로 친다(원 논문 규칙) |
| 결함 판정 | 개발자 | 나중에 유지보수자가 같은 수정을 다른 사본에 넣었거나, 릴리스된 jar 로 실행해 확인한 것만 |

- 식별자 정규화(`--ignore-identifiers`)를 못 쓴 이유: PMD 7.28.0 은 이 저장소 전체에 그 옵션을 주면
  `NullPointerException ... JavaCpdLexer$ConstructorDetector.restoreConstructorToken` 으로 멈춘다. 파일 하나씩은 괜찮고
  특정 순서의 세 파일이 모이면 멈춘다(앞 파일의 생성자 감지 상태가 다음 파일로 남는다). pmd/pmd#7133, 7.29.0 에서 고쳐질 예정이다(#7138, 2026-10-16 현재 미출시).
  7.29.0 이 나오기 전에는 식별자 정규화를 끈다.
  그래서 이름만 바꾼 사본(type 2)은 이 실습에서 묶음으로 잡히지 않는다.
- 벤더링한 코드(`org.springframework.asm`, `cglib`, `objenesis`, `javapoet`)는 뺐다. 원 논문이 생성 코드를 뺀 것과 같은 이유다.

## 돌리는 법

Docker 는 쓰지 않는다. 호스트의 Java(이번에는 OpenJDK 25.0.3), git, python3 로 돈다.
받은 저장소와 아카이브는 전부 `WORK`(저장소 밖 빈 디렉터리)에 두고, 받은 저장소 안의 스크립트(gradlew 등)는 실행하지 않는다.

```bash
cd labs/devops/pc-02-clone-drift
export WORK=/tmp/clone-drift                        # 저장소 밖
./scripts/fetch.sh v6.1.0 v6.2.0                    # 클론(--no-checkout), git archive 로 스냅숏, PMD 7.28.0
./scripts/cpd.sh v6.1.0 100; ./scripts/cpd.sh v6.2.0 100
python3 scripts/track.py "$WORK" v6.1.0 v6.2.0 100  # 사본마다 git log -L (28초)
python3 scripts/analyze.py v6.1.0 v6.2.0 100        # -> results/summary-*.md, results/events-*.tsv
python3 scripts/dossier.py "$WORK" v6.1.0 v6.2.0 100  # 불일치 묶음마다 diff 모음 -> out/review/ (손 판정용)
./scripts/run_demos.sh                              # 릴리스 jar 로 세 묶음을 실행 확인 -> out/demo/
```

| 파일 | 내용 |
|---|---|
| `scripts/track.py` | 기준 릴리스의 사본 줄 범위를 끝 릴리스로 옮기고(git diff 의 hunk), 그 범위로 `git log -L ... v6.1.0..v6.2.0 --no-merges`. 커밋마다 범위 안 diff 가 주석·공백만인지 코드인지 가른다 |
| `scripts/analyze.py` | 커밋 단위로 일관/불일치를 가르고, 묶음을 unchanged / consistent_only / has_inconsistent / collapsed 로 나눈다. 끝 릴리스 CPD 에서 사본들이 다시 한 묶음인지 본다 |
| `results/review-v6.1.0-v6.2.0-t100.md` | 불일치 묶음 40개를 손으로 본 판정과 근거 |
| `demo/*.java` | 릴리스된 jar 로 돌리는 확인 코드(소스 파일 실행, 빌드 없음) |
| `out/demo/*.txt` | 데모 출력. HeadersDemo 는 `asSingleValueMap()` 뷰의 `toString()` 이 원래 맵을 찍어서 `get` 과 `size` 로 본다 |
| `scripts/count_issue_refs.sh` | 창 안 커밋 중 메시지에 `gh-<숫자>` 가 있는 수(대소문자 무시) -> `out/issue-refs.txt`: 2,395 중 1,661(69.4%) |
| `out/cpd-ignore-identifiers-error.txt`, `out/track-time.txt` | `--ignore-identifiers` 로 돌렸을 때의 출력 원문, track.py 한 번의 벽시계 시간(28.0초) |

`out/cpd-*.xml`(스냅숏 절대 경로와 시각, 2MB 안팎), `out/track-*.json`(수백 KB), `out/review/` 는 커밋하지 않는다. 위 명령으로 다시 만든다.

## 결과 (최소 100 토큰)

```
묶음 256개 (사본 2개 245, 3개 7, 4개 3, 5개 1)
unchanged 176 / consistent_only 38 / has_inconsistent 40 / collapsed 2
커밋 단위 이벤트: 일관 81, 불일치 69   (주석·공백만 바꾼 (커밋, 사본) 쌍 55 는 제외)
(스크립트 출력 그대로. 묶음 65 를 손으로 고치면 unchanged 175 / consistent_only 39, 일관 83)
```

| 최소 토큰 | 묶음 | 코드가 바뀐 묶음 | 그중 불일치가 있었던 묶음 | 불일치 이벤트 / 전체 |
|---|---|---|---|---|
| 75 | 450 | 128 | 70 (55%) | 116 / 240 (48%) |
| 100 | 256 | 79 | 40 (51%) | 69 / 152 (45%) |
| 150 | 127 | 49 | 23 (47%) | 40 / 92 (43%) |

100 토큰 줄은 묶음 65 를 고친 숫자, 75 와 150 은 스크립트 출력 그대로다. Krinke 의 "절반"과 같은 단위는 마지막 열(변경 단위)이다.

손 판정(100 토큰, 40개): 창 안에서 따라 고쳐짐 9, 동작 차이 없음 11, 한쪽만의 요구 또는 판단 불가 17,
확인 못 한 후보 2, 다른 사본에 빠진 것이 확인됨 1. 자세한 것은 `results/review-v6.1.0-v6.2.0-t100.md`.

### 확인 방법의 한계

- **사본 추적은 줄 범위다.** 기준 범위를 끝 릴리스로 옮길 때 범위 안에 끼워 넣은 줄도 범위에 들어간다. 그래서 "사본을 바꿨다"에는 사본 경계에 붙여 넣은 새 메서드가 섞인다(예: 묶음 1 의 새 메서드 추가).
- **사본 끝에서 지운 줄은 놓친다.** `git log -L` 은 끝 릴리스에 남은 범위를 거슬러 올라가므로, 범위 가장자리에서 통째로 지워진 줄을 바꾼 커밋은 보이지 않는다.
  사본 범위가 절반 아래로 줄어든 사본은 10개였고, 그중 묶음 65(webflux/webmvc `PathResourceLookupFunction`)는 이 때문에 unchanged 로 잘못 분류됐다.
  실제로는 c6fa180602(gh-33574)가 두 사본을 각 스택의 `ResourceHandlerUtils` 로 같이 옮겼다(일관 변경). 나머지 8개(묶음 12, 70, 107, 139, 172 의 사본)는 남은 줄에서 바꾼 커밋이 잡혔다. 손으로 고치면 unchanged 175, consistent_only 39 다. `scripts/recheck_g65.py` 가 범위를 c6fa180602 의 부모까지만 옮겨 다시 돌리면 두 사본을 함께 바꾼 커밋 둘(d86bf8b205, c6fa180602)이 나와 일관 변경이 81 에서 83 이 된다(`out/recheck-g65.txt`). 나머지 8개도 가장자리에서 지운 변경을 놓쳤을 수 있다.
- 기준 릴리스 뒤에 사본 안에 새로 들어온 코드는 추적 대상이 아니다. 예: 94c04821ff(gh-33568)는 2024-09 에 새로 쓴 webflux 쪽 경로 검사 한 줄만 고쳤는데, 그 줄은 v6.1.0 에 없었다.
- 끝 릴리스에서 "다시 한 묶음"인지 보는 검사는 범위가 절반 이상 겹치는 CPD 묶음을 찾는다. 공통 유틸리티로 옮겨 사본이 줄어든 묶음(12, 65, 70, 172)은 "다시 한 묶음 아님"이 된다.
  그런데 그 유틸리티(`ResourceHandlerUtils`)는 webflux 와 webmvc 에 하나씩 생겨, v6.2.0 의 CPD 에서 서로 복제 묶음 4개로 다시 잡혔다.
- `git log -L` 에 `--no-merges` 를 줬다. 머지 충돌을 풀면서 바뀐 줄은 세지 않는다.

## 고친 것과 버린 실행 (2026-10-16)

- 첫 CPD 실행은 `--ignore-identifiers --ignore-literals` 로 했다가 위 NPE 로 멈췄다(보고서 없음). 파일 목록을 반씩 잘라 37개까지 줄였고,
  하나씩 빼 보며 세 파일(`PropertySource.java`, `PropertySourceRegistry.java`, `AotApplicationContextInitializer.java`)까지 줄였다. 각각 따로는 멈추지 않았다. 같은 증상의 이슈(pmd/pmd#7133)를 찾아 옵션을 뺐다.
- `-z`(경로 상대화)를 줘 봤지만 XML 의 경로가 그대로 절대 경로였다. 옵션을 빼고 `track.py` 가 스냅숏 접두사를 잘라 쓴다.
- `analyze.py` 첫 판은 사본이 하나만 남은 묶음(collapsed)에도 이벤트를 세어 "일관 1/1" 이 두 줄 나왔다. 사본이 2개 미만이면 이벤트를 세지 않게 고쳤다(일관 83 -> 81).
- `fetch-jars.sh` 첫 판은 7.0.0 에서 `spring-jcl` 을 받다 멈췄다. 7.0 의 spring-core 는 commons-logging 1.3.5 를 쓴다.
- 데모의 6.1.3 실행에도 reactor-core 3.7.0 을 썼다(6.1.3 이 원래 쓰던 3.6.x 가 아니다). 데모가 쓰는 API 는 두 판에 다 있다.
