# OpenTelemetry 01: API와 SDK 분리 읽기

공개 릴리스 `open-telemetry/opentelemetry-java` **v1.67.0**의 커밋
`b4b3a1b354425c3f1411173c0e48cb24a1cba224`를 기준으로 코드 캡처와 API-only 실험을 재현한다.
상위 저장소 코드는 수정하지 않으며 이 디렉터리는 별도 학습용 실험이다.

## 코드 캡처 재생성

이미 설치된 Playwright와 시스템 Chrome을 사용한다. 별도 의존성을 설치하거나 브라우저 프로필,
GitHub 인증 정보, 티스토리 세션을 사용하지 않는다.

```sh
/Users/dding/.local/share/tistory-uploader/venv/bin/python \
  labs/observability/otel-01-api-sdk/capture.py
```

다른 편의 매니페스트에도 같은 도구를 사용할 수 있다.

```sh
/Users/dding/.local/share/tistory-uploader/venv/bin/python \
  labs/observability/otel-01-api-sdk/capture.py \
  --manifest labs/observability/otel-02-context/source-manifest.json \
  --output-dir posts/CS/Observability/otel/images/02
```

매니페스트는 `repository`, `tag`, 전체 `commit`, `captures`를 가진다. 각 캡처 항목은
`path`, `start`, `end`, `output`, `sha256`, `permalink`, 선택적 `highlight`,
`excerpt_sha256`를 가진다. `sha256`은 전체 원본 파일의 바이트 해시이며 `excerpt_sha256`은
해당 줄들을 LF로 연결하고 마지막 LF를 붙인 UTF-8 텍스트의 해시다.

도구는 태그가 지정 커밋을 가리키는지 확인하고, 커밋 SHA가 들어간 raw URL에서 원본을
읽어 임시 디렉터리에 보관한 뒤 전체 파일 해시와 발췌 해시를 대조한다. 줄을 생략하거나
재구성하지 않고 연속한 원본 범위만 렌더링한다. 렌더링된 코드 텍스트가 원본 줄과 같은지,
가로 넘침이 없는지도 검사한다. 원본 임시 파일과 인증 없는 브라우저 컨텍스트는 종료 시 정리한다.
카드 바깥의 넘침뿐 아니라 실제 코드 행이 잘리지 않는지도 검사한다. 긴 원문 행은
텍스트를 생략하지 않고 글자 크기를 조절하며, 최소 크기에서도 넘치면 실패한다.
`--report <JSON 경로>`를 주면 해시·이미지 크기·실제 글자 크기를 생성 기록으로 저장한다.

이 PNG는 **GitHub 화면을 찍은 것이 아니라 원본 코드를 로컬에서 렌더링한 캡처**다.
줄 번호, 파일 경로, 태그, 짧은 커밋 SHA를 표시하며 배경 강조만 추가했다.
브라우저/OS 글꼴 버전 차이로 PNG 바이트는 달라질 수 있으므로 소스 해시와 텍스트 검사를
재현성의 기준으로 삼는다.

출력은 `posts/CS/Observability/otel/images/01/`의 `api-noop.png`, `sdk-build.png`,
`sdk-trace-policy.png`, `sdk-no-processor.png`다. 글의 상대 경로 이미지는 로컬 미리보기용이다. 이 도구는 이미지를
티스토리에 업로드하거나 공개 URL을 만들지 않는다.

## API-only 동작 검증

```sh
python3 labs/observability/otel-01-api-sdk/verify.py
```

JDK 11 이상이 필요하다. Maven Central에서 `opentelemetry-api`,
`opentelemetry-context`, 전이 의존성인 `opentelemetry-common` 1.67.0 JAR 세 개를
임시 디렉터리에 내려받아 SHA-256을 확인한다. 이 버전의 API POM은 context를,
context POM은 common을 요구한다. API와 context 두 개만 넣으면 Context 초기화 시
`ComponentLoader`를 찾지 못하므로 완전한 API-only 클래스 경로가 아니다.
SDK, exporter, 자동 구성 모듈은 클래스 경로에 넣지 않는다. `javac --release 11`로
실험 코드를 컴파일한 뒤 실제로 실행하고 두 경우의 출력과 조건을 모두 검사한다.

검사 범위는 부모 없는 noop span의 recording/유효성, 명시적 유효 부모가 있는 noop span의
recording/부모 SpanContext 보존이다. SDK 등록 전후 비교, context 전파 전체, exporter 동작,
성능이나 0 오버헤드는 이 실험으로 검증하지 않는다.

심화판의 API/SDK 구성별 비교는 별도 [runtime probes](../otel-runtime-probes/README.md)에서
확인한다. 특히 Java 1.67.0은 SpanProcessor가 없으면 SDK Provider도 noop tracer를 반환하므로,
SDK 객체 생성만으로 기록 상태가 참이 된다고 가정하지 않는다.

실행 시점의 출력·검사 범위·PNG 크기와 해시는 [validation.json](validation.json)에 남겼다.
재실행 시 도구의 실제 출력이 과거 기록보다 우선한다.

## 원본과 라이선스

원본은 OpenTelemetry Authors가 저작권을 가진 Apache-2.0 코드다.
정확한 파일·줄 범위·불변 링크는 [source-manifest.json](source-manifest.json)에 기록했다.
원본 저장소의 [LICENSE](https://github.com/open-telemetry/opentelemetry-java/blob/b4b3a1b354425c3f1411173c0e48cb24a1cba224/LICENSE)를 함께 확인한다.
이미지에 원본 코드의 라이선스 헤더를 반복해서 넣지 않는 대신 이 출처와 저작권 표시를 유지한다.
