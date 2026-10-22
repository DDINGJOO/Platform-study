# Debezium · grammars-v4 재현 기록

2026-10-22 실행. 저장소는 scratchpad 에 `--filter=blob:none` 으로 받았고 끝난 뒤 지웠다.

## 환경

- JDK: Amazon Corretto 21.0.11 (`/usr/libexec/java_home -v 21`). Debezium CI 의 `.github/actions/setup-java/action.yml` 기본값이 `temurin` 21 이라 같은 메이저 버전을 썼다. (`pom.xml`: `debezium.java.source=21`, connector target 17)
- Maven: 저장소의 `./mvnw` (3.9.12), `MAVEN_OPTS=-Xmx2g`
- grammars-v4 는 같은 `mvnw` 로 문법 폴더 하나의 `pom.xml` 만 돌렸다(`antlr4-maven-plugin` 4.13.2 + `antlr4test-maven-plugin` 1.22). sparse checkout 으로 `sql/mysql/Oracle`, `sql/mariadb` 만 받았다.

## PR 상태 (gh 재확인, 2026-10-22)

| PR | 상태 | 머지 커밋 / head | 머지한 사람 |
|---|---|---|---|
| debezium#8220 | MERGED 2026-10-21T07:18:57Z | 8787caaa (rebase 머지, 문법 변경 커밋 4b6aaedc) | vsantonastaso |
| debezium#8225 | OPEN | head 73aa4a2a (두 번째 부모가 8787caaa) | - |
| grammars-v4#5037 | MERGED 2026-10-20T21:34:15Z | a5802dc9 | teverett |
| grammars-v4#5039 | MERGED 2026-10-20T21:35:59Z | 84b3dca1 | teverett |

## 0. 준비 빌드 (8787caaa)

```
./mvnw -B -pl debezium-connector-mysql,debezium-connector-mariadb -am install -Dquick -DskipTests -DskipITs \
  -Dcheckstyle.skip -Dformat.skip -Dimpsort.skip -Drevapi.skip -Dmaven.javadoc.skip -Dmaven.source.skip -Ddocker.skip
```
- 결과: BUILD SUCCESS, 17분 38초 (23개 모듈, 의존성 내려받기 포함)
- 이후 테스트 실행 때 formatter·checkstyle 플러그인이 `debezium-ide-configs`, `debezium-checkstyle` SNAPSHOT 을 찾아서 `support/ide-configs`, `support/checkstyle` 을 따로 `install` 했다.

테스트 실행 공통 플래그(`$T`): `-Dcheckstyle.skip -Dformatter.skip -Dimpsort.skip -Ddocker.skip -Dsurefire.failIfNoSpecifiedTests=false`. 통합 테스트(Docker)는 돌리지 않았다.

## 1. debezium#8220 (생성된 MySQL 문법 `schemaRef?`)

### 1-1. 기준 상태 (8787caaa)
```
./mvnw -B -pl debezium-connector-mysql test $T \
  -Dtest='MySqlAntlrDdlParserTest#shouldParseAlterDatabaseWithoutDatabaseName+shouldParseAlterDatabaseWithDefaultCharsetWithoutDatabaseName'
```
- `Tests run: 2, Failures: 0, Errors: 0` / BUILD SUCCESS / 9초
- `shouldParseAlterDatabaseWithoutDatabaseName` 은 `BinlogAntlrDdlParserTest` 에 정의되고 `MySqlAntlrDdlParserTest` 가 상속해 실행된다.

### 1-2. 문법만 되돌림
`debezium-ddl-parser/.../mysql/generated/MySqlParser.g4` 의 `DATABASE_SYMBOL schemaRef? alterDatabaseOption+` 를 `schemaRef` 로 되돌렸다. 리스너(`ctx.schemaRef() == null` 분기)와 테스트는 그대로.

```
./mvnw -B -pl debezium-ddl-parser clean install -Dquick -DskipTests -Dcheckstyle.skip -Dformatter.skip -Dimpsort.skip -Drevapi.skip
./mvnw -B -pl debezium-connector-mysql test $T -Dtest=(위와 같음)
```
- install 14초, 테스트 4초
- `Tests run: 2, Failures: 0, Errors: 2` / BUILD FAILURE

```
io.debezium.text.ParsingException:
DDL statement couldn't be parsed. Please open a GitHub issue at https://github.com/debezium/dbz/issues with the statement 'ALTER DATABASE CHARACTER SET utf8mb4;'
mismatched input 'CHARACTER' expecting {ACCOUNT_SYMBOL, ACTION_SYMBOL, ADDDATE_SYMBOL, ...
```
두 번째 테스트는 `mismatched input 'DEFAULT' expecting {ACCOUNT_SYMBOL, ...`.

**주의(실패한 첫 시도)**: 처음에는 `clean` 없이 `install` 해서 ddl-parser 가 2초 만에 끝났고, 테스트가 `CREATE DATABASE db1 ...` 에서부터 `mismatched input 'CREATE'` 로 실패했다. 증분 빌드로 생성 코드가 어긋난 상태였다. `clean install` 로 다시 만든 뒤에는 위처럼 의도한 문장(`ALTER DATABASE ...`)에서만 실패했다. 이 첫 결과는 버렸다.

## 2. debezium#8225 (MariaDB·legacy MySQL 문법, 옵션 먼저)

### 2-1. 기준 상태 (PR head 73aa4a2a)
8787caaa 와의 차이는 이 PR 의 4개 파일뿐이다(`git diff --stat 8787caaa HEAD`: 4 files, +64 -2).
```
./mvnw -B -pl debezium-ddl-parser clean install -Dquick -DskipTests ...      # 15초
./mvnw -B -pl debezium-connector-mysql,debezium-connector-mariadb test $T \
  -Dtest='MySqlPtAntlrDdlParserTest#shouldParseAlterDatabaseWithDefaultCharset*,MariaDbOnlyAntlrDdlParserTest#shouldParseAlterDatabaseWithDefaultCharset*'
```
- MySqlPtAntlrDdlParserTest: `Tests run: 2, Failures: 0, Errors: 0`
- MariaDbOnlyAntlrDdlParserTest: `Tests run: 2, Failures: 0, Errors: 0`
- BUILD SUCCESS / 11초

### 2-2. 문법만 되돌림
`git checkout 8787caaa -- .../mariadb/generated/MariaDBParser.g4 .../mysql/legacy/MySqlParser.g4` (2 files, +2 -6). 테스트는 그대로.
- ddl-parser clean install 14초, 테스트 4초 (`-fae`)
- 두 클래스 모두 `Tests run: 2, Failures: 1, Errors: 0`
  - 실패: `shouldParseAlterDatabaseWithDefaultCharsetWithoutDatabaseName`
  - 통과: `shouldParseAlterDatabaseWithDefaultCharsetAndDatabaseName`

```
org.opentest4j.AssertionFailedError:
expected: "utf8mb4"
 but was: "latin1"
ignoring case considerations
	at io.debezium.connector.mysql.antlr.MySqlPtAntlrDdlParserTest.shouldParseAlterDatabaseWithDefaultCharsetWithoutDatabaseName(MySqlPtAntlrDdlParserTest.java:93)
```
PR 본문의 "Without the grammar change, the first test fails in both classes and the second passes" 와 같다. 파싱 예외가 아니라 값 검증 실패라는 점이 8220 과 다르다.

### 2-3. 머지 충돌 재현
`git merge-tree --write-tree 25093b1e 8787caaa` (PR 의 이전 head 와 당시 main):
```
CONFLICT (content): Merge conflict in debezium-connector-mysql/src/test/java/io/debezium/connector/mysql/antlr/MySqlPtAntlrDdlParserTest.java
```
충돌 구간: 한쪽은 이 PR 의 두 테스트, 다른 쪽은 main 의 `@FixFor("debezium/dbz#2217") shouldApplyRealHandlingMode` (커밋 188b9d62 "Move legacy-parser REAL handling test to MySqlPtAntlrDdlParserTest"). 같은 위치에 테스트를 추가해서 생긴 텍스트 충돌이었고, 머지 커밋 73aa4a2a 는 둘 다 남겼다. `MariaDbOnlyAntlrDdlParserTest` 는 자동 병합됐다.

## 3. grammars-v4#5037 (Oracle MySQL 문법)

### 3-1. 기준 상태 (a5802dc9)
```
./mvnw -B -f sql/mysql/Oracle/pom.xml test
```
- 예제 24개 파일 파싱(`ddl_alter.sql` 포함), BUILD SUCCESS, 10초

### 3-2. 문법만 되돌림 (`schemaRef?` → `schemaRef`, 예제는 유지)
```
./mvnw -B -f sql/mysql/Oracle/pom.xml clean test
```
- BUILD FAILURE, 8초
```
line 61:15 mismatched input 'character' expecting {ACCOUNT_SYMBOL, ...
line 62:15 mismatched input 'default' expecting {ACCOUNT_SYMBOL, ...
line 63:13 mismatched input 'default' expecting {ACCOUNT_SYMBOL, ...
Unable execute mojo: found 3 errors, but missing file ddl_alter.sql.errors
```
61~63행은 PR 이 추가한 세 줄(`alter database character set = utf8;`, `alter database default character set = utf8;`, `alter schema default character set = utf8;`)이다.

## 4. grammars-v4#5039 (MariaDB 문법)

### 4-1. 예제 코퍼스: 전후 모두 통과
- 84b3dca1: `./mvnw -B -f sql/mariadb/pom.xml clean test` → 23개 파일, BUILD SUCCESS, 12초
- 문법만 되돌림(`git checkout 84b3dca1^1 -- sql/mariadb/MariaDBParser.g4`): 23개 파일, BUILD SUCCESS, 11초
- PR 본문 "No example added, on purpose ... would pass either way" 와 같다.

### 4-2. 파스 트리 비교
입력 `ALTER DATABASE DEFAULT CHARSET latin2;`, `org.antlr.v4.gui.TestRig MariaDB root -tree` (클래스패스: `sql/mariadb/target/classes`, antlr4 4.13.2, antlr4-runtime 4.13.2, ST4, antlr-runtime)

되돌린 문법(변경 전):
```
(root (sqlStatements (sqlStatement (ddlStatement (alterDatabase ALTER DATABASE (uid (simpleId (keywordsCanBeId DEFAULT))) (createDatabaseOption (charSet CHARSET) (charsetName (charsetNameBase latin2)))))) (emptyStatement_ ;)) <EOF>)
```
84b3dca1(변경 후):
```
(root (sqlStatements (sqlStatement (ddlStatement (alterDatabase ALTER DATABASE (createDatabaseOption DEFAULT (charSet CHARSET) (charsetName (charsetNameBase latin2)))))) (emptyStatement_ ;)) <EOF>)
```

## 5. CI 실패 확인 (gh, 읽기만)

#8225 head 73aa4a2a 의 실행 39574509122 (2026-10-21T09:07:27Z 시작):
- MariaDB 11.8 mariadb-ci / MariaDB 12.3 mariadb-ci 실패: `ReadOnlyIncrementalSnapshotIT` (Failures 10·12, 대부분 182초 근처 `[Too many no data record results, 0 < 1000]`), `MariaDbConnectorIT`, `MariaDbMetricsIT` 등 통합 테스트. 같은 잡에서 `MariaDbOnlyAntlrDdlParserTest` 10개, `MariaDbAntlrDdlParserTest` 175개 통과.
- MySQL 9.7 mysql-ci-ssl 실패: `MysqlDefaultValueIT>BinlogDefaultValueIT.timeTypeWithConnectModeWhenEventConvertingFail:878` (AssertionFailedError). 같은 잡에서 `MySqlPtAntlrDdlParserTest` 181개, `MySqlAntlrDdlParserTest` 190개 통과(3 skipped).
- 그 밖의 실패: Debezium Server, Platform conductor (`io.debezium.service.spi.InstanceResolver` 컴파일 오류), MongoDB Apicurio (`Container startup failed for image quay.io/debezium/official-mongo:8.0`).
- MySQL 8.0/8.4/9.7 의 다른 잡과 MariaDB 11.4 잡들은 통과. 통과 30, 실패 6.

#8220 head 81981af2 의 실행 38394417581 (2026-10-13): MariaDB 12.3 mariadb-ci 실패, `ReadOnlyIncrementalSnapshotIT` Failures 9, `MariaDbConnectorIT`, `MariaDbMetricsIT` 오류. 나머지 35개 통과. 이 상태로 10-21 머지됐다.

## 6. 정리

- 받은 저장소(dbz, g4)와 로그 디렉터리를 지웠다. `~/.m2` 에 설치된 `io/debezium/*/3.8.0-SNAPSHOT` 도 지웠다.
