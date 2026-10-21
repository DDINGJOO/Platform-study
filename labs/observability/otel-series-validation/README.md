# OTel 8편 시리즈: 반복 가능한 자동 검사

이 디렉터리의 산출물은 **발행하지 않는 검증 자료**다. 기존 글·시리즈 설정·업로드 매니페스트는
읽기만 하고 변경하지 않는다. `report.json`, `report.md`, `screenshots/`만 이 디렉터리에 생성한다.
원자료 주장에 대한 독립 사실 감사나 독립 퇴고를 대신하지 않는다.

```sh
# 작성 중: 존재하는 편만 검사하고 나머지는 대기로 표시
python3 labs/observability/otel-series-validation/validate.py

# 실제 원본 해시 + 기존 Playwright/Chrome으로 데스크톱·모바일 검사
/Users/dding/.local/share/tistory-uploader/venv/bin/python \
  labs/observability/otel-series-validation/validate.py --verify-sources --browser

# 집필 완료 뒤에는 8편 모두 요구
/Users/dding/.local/share/tistory-uploader/venv/bin/python \
  labs/observability/otel-series-validation/validate.py --final --verify-sources --browser
```

Python 3.9 이상을 사용한다. 브라우저 검사는 이미 설치된 Playwright와 시스템 Chrome만 사용한다.
브라우저 프로필, 인증 정보, 새 의존성 설치, 서버 발행, 업로더 sync는 사용하지 않는다.

## 검사 범위

- 확정한 파일명·편 번호·제목, 현재 편을 포함한 최근 세 편만 표시하는 상단 안내와 현재 편 강조. 별도의 전체 목차는 제공하지 않는다.
- 원래 템플릿과 바이트 단위로 같은 style 본문, 태그 3~5개와 공통 태그 5~6개, lead 80~150자.
- 기존 `validate_html.py`와 일반 `mask-check.py` 함수를 읽기 전용으로 호출한다. 마스킹 적중 값은
  보고서에 복사하지 않고 패턴 종류만 남긴다. 코드·로그의 원문 보존과 본문 엠대시 금지를 구분한다.
- 상대 이미지 또는 이 시리즈의 고정 jsDelivr 주소를 로컬 PNG에 대응시켜 존재·alt와 source manifest의
  전체 SHA·해시·연속 범위·원문 permalink, PNG 기본 정보를 검사한다. 허용하는 외부 접두어는
  `https://cdn.jsdelivr.net/gh/DDINGJOO/Platform-study@main/posts/CS/Observability/otel/images/` 하나다.
  그 뒤에는 `01`~`08` 디렉터리와 PNG 파일명만 허용하며 다른 저장소·브랜치·호스트·쿼리·프래그먼트는 거부한다.
  `--verify-sources`를 주면 고정 raw URL을 읽어 실제 파일/발췌 해시를 검증한다.
- 업로더 모듈을 `runpy`로 읽되 main은 실행하지 않는다. HEAD 설정과 현재 설정을 같은 기존 글에
  적용해 제목·카테고리·태그 변화가 없는지 확인하며, `tistory-manifest.json`도 HEAD와 비교한다.
- 선택적 브라우저 검사: 1100×850, 390×844. 폰트 준비와 모든 이미지 decode를 기다리고 문서 가로 넘침,
  깨진 이미지, SVG 밖으로 나간 텍스트를 검사한다. 코드·표의 내부 가로 스크롤은 허용한다.
- 각 편/화면에서 상단과 첫 SVG·표 위치를 화면 크기 PNG로 남긴다. 전체 길이 이미지는 만들지 않는다.

HTML fragment를 로컬 파일로 열고 화면 검사를 위한 viewport meta만 DOM에 넣는다. 글의 CSS나
내용을 고쳐 검사를 통과시키지 않는다. CDN 주소가 있으면 브라우저가 그 주소에서 실제로 이미지를 내려받는다.
로컬 파일로 대체하거나 응답을 가로채지 않는다. 따라서 이미지를 main에 푸시하기 전에는 정적 검사만 실행하고,
푸시한 뒤 `--browser`로 CDN 로딩까지 검사한다. 티스토리 스킨·업로드 후 환경은 별도 확인이 필요하다.
원본 다운로드 실패·글이 검사 중 수정된 경우도 보고하므로 집필이 끝난 뒤 최종 검사를 다시 실행한다.

미작성 편은 기본 모드에서 대기 상태다. 기존 편의 실제 오류는 부분 검사에서도 실패로 판정한다.
정상 부분 결과는 `PASS_PARTIAL`, 최종 전체 결과는 `PASS`, 오류가 있으면 `FAIL`이며 종료 코드는 1이다.

## 이미지 경로 회귀 검사

네트워크나 보고서 생성 없이 상대 경로와 허용 CDN 주소가 같은 파일로 대응되고, 잘못된 URL이 거부되는지 확인한다.

```sh
python3 - <<'PY'
import runpy

check = runpy.run_path("labs/observability/otel-series-validation/validate.py")
resolve = check["resolve_image_path"]
post = check["SERIES"] / "example.html"
prefix = check["CDN_IMAGE_PREFIX"]
expected = (check["SERIES"] / "images/01/api-noop.png").resolve()
assert resolve(post, "images/01/api-noop.png") == expected
assert resolve(post, prefix + "01/api-noop.png") == expected
invalid = [
    "", "https://example.com/01/api-noop.png", "//cdn.jsdelivr.net/anything.png",
    prefix.replace("@main/", "@other/") + "01/api-noop.png",
    prefix.replace("DDINGJOO/", "someone/") + "01/api-noop.png",
    prefix.replace("cdn.jsdelivr.net/", "cdn.jsdelivr.net.evil.example/") + "01/api-noop.png",
    prefix + "01/api-noop.png?raw=1", prefix + "01/api-noop.png#fragment",
    prefix + "01/../api-noop.png", prefix + "01/%2e%2e/api-noop.png",
    prefix + "09/api-noop.png", "../../../../outside.png",
]
for src in invalid:
    try:
        resolve(post, src)
    except ValueError:
        continue
    raise AssertionError(f"unexpectedly accepted image reference: {src}")
print(f"PASS: 2 valid mappings, {len(invalid)} invalid references rejected")
PY
```
