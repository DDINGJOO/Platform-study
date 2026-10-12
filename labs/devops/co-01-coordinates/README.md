# 소스 코드 관찰 실습-1: 같은 좌표가 다른 바이너리를 가리키는 순간을 만든다

로컬 Maven 저장소(Reposilite)와 도커 레지스트리를 띄우고, 같은 이름(그룹:이름:버전, 이미지:태그)에 다른 내용을 올린다.
캐시를 따로 가진 빌드 컨테이너들("개발자 PC")이 그때마다 받은 jar 의 SHA-256 과 이미지 다이제스트를 적는다.

| 실험 | 명령 | 결과 파일 |
|---|---|---|
| SNAPSHOT 두 번 게시, 캐시 상태가 다른 소비자 여섯, 시각이 붙은 버전으로 고정, `preserveSnapshots` | `lab.py snapshot` | `results/snapshot.txt` |
| 릴리스 재게시(Gradle, 직접 PUT), 목록 파일 덮어쓰기 | `lab.py release` | `results/release.txt` |
| 같은 태그 재푸시 전후 컨테이너 둘, 옛 다이제스트로 받기 | `lab.py tag` | `results/tag.txt` |
| `2.10.+`, `latest.release`(rc 거르기 포함), `[2.10,2.11)`, Maven `RELEASE`/`LATEST`, 의존성 잠금 | `lab.py dynamic` | `results/dynamic.txt`, `results/extra.txt` |
| 같은 소스 두 번 빌드: Gradle/Maven jar, 도커 이미지 | `lab.py rebuild` | `results/rebuild.txt`, `results/extra.txt` |
| 목록 파일(`maven-metadata.xml`)을 깨뜨렸을 때 잠금 빌드·잠금 없는 빌드·고정 버전 빌드 | `bash scripts/lockcheck.sh` (`up` 직후 빈 저장소에서) | `results/lockcheck.txt` |

## 돌리기

```bash
cd labs/devops/co-01-coordinates
python3 scripts/lab.py up        # Reposilite :30080, registry :30500
python3 scripts/lab.py snapshot
python3 scripts/lab.py release
python3 scripts/lab.py tag
python3 scripts/lab.py dynamic
python3 scripts/lab.py rebuild
python3 scripts/lab.py down      # compose 프로젝트의 컨테이너와 볼륨 삭제
docker rm -f co01-node-a co01-node-b; docker images 'localhost:30500/lab/*' -q | xargs docker rmi -f
```

- 필요한 것: Docker(buildx 포함), Python 3. 빌드는 `gradle-a/b/ci`, `maven-a/b` 컨테이너(profile `tools`)에서 한다
- 컨테이너마다 Gradle 캐시·Maven 로컬 저장소를 다른 이름 있는 볼륨에 둔다. 볼륨 하나가 캐시를 가진 기계 한 대다. 호스트의 `~/.m2`, `~/.gradle` 은 쓰지 않는다
- `snapshot` 은 실행 중 Reposilite 관리 API 로 `preserveSnapshots` 를 잠깐 켰다가 끈다
- `dynamic` 은 저장소에 버전을 쌓으므로 처음부터 다시 재려면 `down` 후 `up` 부터

## 버전

| 부품 | 버전 | 고른 이유 |
|---|---|---|
| Reposilite | 3.6.3 (`dzikoysk/reposilite`) | 최신 안정판, 단일 컨테이너. 임시 토큰(`--token lab:lab-secret-123`)으로 게시 |
| registry | 3.1.2 (CNCF Distribution) | 최신 안정판 |
| Gradle | 9.8.1 (`gradle:9.8.1-jdk21`) | 최신 안정판. 9.0 부터 재현 가능 아카이브가 기본 |
| Maven | 3.10.0 (`maven:3.10.0-eclipse-temurin-21`) | 최신 GA. Super POM 이 `project.build.outputTimestamp` 기본값을 넣는다 |
| busybox | 1.37.0 | 태그 실험용 작은 이미지 |
| Docker | Engine 29.5.3, buildx 0.34.1 (Docker Desktop, Apple M5 Pro) | |

## 결과 (2026-10-12, 처음부터 다시 돌린 회차)

| 실험 | 결과 |
|---|---|
| SNAPSHOT 두 번 게시 뒤 여섯 소비자 | 옵션 없이 다시 받은 gradle-a, maven-a 둘은 첫 jar(`7a5a47c1…`), 캐시 없는 둘과 `--refresh-dependencies`, `-U` 는 두 번째 jar(`b30c4627…`). 오류 0 |
| 기본 설정 Reposilite 의 옛 스냅숏 | 두 번째 게시 때 첫 타임스탬프 파일 삭제(`preserveSnapshots: false`). `1.0.0-20261012.064614-1` 고정 → jar 404, BUILD FAILED |
| `preserveSnapshots: true` | 두 파일 다 남음. 시각 고정 버전은 첫 jar, `1.0.0-SNAPSHOT` 은 두 번째 jar |
| 릴리스 재게시 | Gradle `Received status code 409 from server: Conflict`, 직접 PUT 409 `Redeployment is not allowed`, jar 해시 그대로(`a2cb82ca…`) |
| 목록 파일 덮어쓰기 | `releases/lab/lib/maven-metadata.xml` 에 `<metadata/>` PUT → 200, 그대로 저장됨 |
| 태그 재푸시 | 같은 `lab/app:1.0` 으로 띄운 두 컨테이너가 `sha256:7ffe3490…`(v1), `sha256:ed86a2fc…`(v2). `docker ps` 는 먼저 뜬 쪽 IMAGE 를 `7ffe34901be2` 로 표시. 옛 다이제스트 pull 성공 |
| `2.10.+` | 2.10.10 (2.10.11 게시 후 2.10.11). 글자 순 정렬이 아니라 숫자 비교 |
| `latest.release` | 2.11.0-rc1 (게시 전후 모두). `excludeVersionByRegex` 로 rc 를 거르면 2.10.10 / 2.10.11 |
| `[2.10,2.11)` | Gradle 2.10.10 / 2.10.11, Maven 2.11.0-rc1 / 2.11.0-rc1 |
| Maven `RELEASE`, `LATEST` | 2.11.0-rc1 → 2.10.11 게시 후 2.10.11 (목록 파일의 `<release>`, `<latest>` 가 마지막 게시를 따름) |
| 잠금 | 새 버전 두 개 게시 뒤 다시 빌드: 잠금 없음 2/2 바뀜, 잠금 있음 0/2. 잠금 상태에서 빌드 파일을 `2.11.+` 로 바꾸면 `{strictly 2.10.10}` 제약과 충돌해 BUILD FAILED |
| 목록 파일을 `<metadata/>` 로 덮어쓴 뒤 | 잠금 없는 `2.10.+` 빌드는 `Could not find any matches for lab:dyn:2.10.+ as no versions of lab:dyn are available` 로 실패. 잠금(2.10.10) 빌드와 고정 버전 빌드는 2.10.10 을 받음(별도 실행) |
| 재빌드 jar | Gradle 기본·Maven 기본은 두 번 빌드 해시 같음. Gradle `-PkeepTimestamps`, Maven `-Dproject.build.outputTimestamp=x` 는 다름 |
| 재빌드 이미지 | `--no-cache` 두 번: 다름. `SOURCE_DATE_EPOCH=0` + `rewrite-timestamp`: 이미지 매니페스트(arm64 `2bfce8c5…`)는 같지만 인덱스 다이제스트는 다름. buildx 기본 출처 증명의 `invocationId`, `startedOn` 때문. `--provenance=false` 면 같음 |

## 돌리다 만난 함정

- **Maven 3.8.1 이상은 http 저장소를 막는다**(`maven-default-http-blocker`). `maven/settings.xml` 에서 그 미러의 `blocked` 를 false 로 덮었다
- **호스트 셸에서 `$(...)` 가 먼저 풀렸다.** `docker compose run … sh -c "…$(sha256sum $f)…"` 를 문자열로 넘기자 호스트의 `sha256sum` 이 표준 입력을 기다리며 멈췄다. 명령을 리스트로 넘겨 호스트 셸을 거치지 않게 했다
- **`-Pdeps` 를 쉼표로 나누면 `[2.10,2.11)` 이 깨진다.** 구분자를 세미콜론으로 바꿨다
- **해소 실패를 삼키는 확인 태스크.** `incoming.resolutionResult` 만 읽으면 해소에 실패한 의존성이 조용히 빠지고 빌드는 성공한다. `rc.files` 를 먼저 요구해 실패하게 했다
- Reposilite 기본 설정은 스냅숏 저장소의 옛 타임스탬프 파일을 지운다. 일부러 남기려면 `preserveSnapshots: true`
- buildx 는 기본으로 SLSA 출처 증명을 이미지 인덱스에 붙인다. 증명 안에 빌드한 Git 저장소 주소와 커밋도 들어 있었다(`results/extra.txt`)
