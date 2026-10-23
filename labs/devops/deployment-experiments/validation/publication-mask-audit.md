# 배포 실험 발행 전 마스킹 독립 감사

## 판정

**APPROVE — 제공된 고유 후보 1,179개와 모든 매칭 문맥 6,306개를 원문과 대조했다. 설명되지 않은 후보 0개, 확인한 실제 자격 증명·계정 식별자·개인정보 0개다.**

작성자 및 퇴고자와 분리된 감사자가 `/tmp/deployment-mask-candidates.json`의 전체 후보를 확인했다. 제공 범위는 새 발행 파일 117개이며, 각 문맥 문자열이 실제 해당 파일에 존재하는지 확인했다. `.mask-allow`나 검사기, 글·실습·원자료는 수정하지 않았다. 이 보고서와 root용 임시 분류 맵만 작성했다.

숫자 후보 1,174개, 로컬 Docker IP 4개, 합성 연락처 예시 1개다. AWS 계정 ID 패턴도 함께 적중한 12자리 숫자 2개는 측정 소수부와 겹치는 중복 분류이므로 고유 후보 수에 더하지 않는다.

## 고유 값별 분류 집계

| 분류 | 고유 값 수 | 직접 대조한 근거 |
|---|---:|---|
| 로컬 실행 Unix 시각 | 512 | HTTP 관측 epoch, 서비스 시작 시각, Zipkin timestamp, Kayenta 밀리초, Prom/Grafana 시계열과 URL 창. 단위를 초/밀리초/마이크로초로 환산해 실행일 범위도 확인했다. |
| 로컬 실측·계산 지표의 소수부 | 629 | Prom 원시 series, Kayenta 입력·통계, Grafana 실제 응답, HTTP/쿼리 실행시간. 모든 문맥에서 실제 소수 토큰의 일부인지 확인했다. |
| 합성 A/B 통계 결과·공식 수식 회귀 기준 | 24 | decision summary/source integration의 비율·Wilson/Newcombe 구간 및 test_analysis.py 수치. 원자료 감사에서 별도 수식으로 재계산했다. |
| Deck query step의 분 단위 반복 소수 | 1 | 실제 Deck DOM의 2초 step 표시 및 README/capture.py의 해당 값 설명을 대조했다. |
| 공식 Java 서비스 객체 출력 해시 | 2 | 공식 Gate/Front50 이미지의 compose.log에 Spring Security 필터 객체 이름 뒤 출력된 런타임 해시다. 계정·저장소 ID 필드가 아니다. |
| Go 메모리 한도 | 1 | 공식 Prometheus automemlimit의 GOMEMLIMIT 바이트 수다. |
| Go 이전 최대 정수 메모리 한도 | 1 | 같은 로그의 previous 값이며 2^63−1과 일치한다. |
| 소프트웨어 빌드 날짜 | 1 | 공식 Prometheus 로그 build_context의 date 필드다. |
| Prometheus 미설정 span ID | 1 | query log의 영(0) spanID다. |
| Prometheus 미설정 trace ID | 1 | query log의 영(0) traceID다. |
| Docker CPU 설정 | 1 | 저장 inspect의 NanoCpus와 verify.py의 0.5 CPU assert가 일치한다. |
| 로컬 Docker 사설 IP | 4 | Deck Apache, Gate localEndpoint, Kayenta runtime, Prom query-log clientIP의 동일 Compose 네트워크 출처를 대조했다. |
| 합성 연락처 예시 | 1 | run.py가 Front50 실습 application에 명시적으로 제출한 테스트 도메인의 예시 주소이며 실제 API/브라우저 응답도 같은 값이다. |
| **합계** | **1,179** | 미분류 0개 |

정확한 후보 값과 사유의 1:1 맵은 `/tmp/deployment-mask-classified.json`에 작성했다. 저장소 보고서에는 실제 후보 값이나 조직 목록의 내용을 싣지 않는다. root가 필요한 정확한 값만 별도로 허용 목록에 반영한다.

## 압축 원자료 별도 검사

일반 텍스트 검사에서 빠질 수 있는 `decision/out/` gzip 6개를 메모리에서 해제하고 UTF-8 JSON으로 파싱했다. 5개 fixture는 각각 이벤트 12,464 / 12,544 / 689 / 12,512 / 12,544개이며, 실제 HTTP 연계 원문은 803개다. fixture source_sha256와 해제 원문 해시가 일치하고 연계 gzip은 sticky-ab 원본 export와 바이트 단위로 같다.

파일을 다시 쓰지 않고 기존 검사기의 일반 패턴을 허용 목록 없이 적용한 결과, **6개 해제 본문 일반 적중 0개·조직 적중 0개**였다. 조직 목록은 저장소 밖 `Path.home()/'.config/blog-mask.txt'`가 존재하고 비어 있지 않음을 확인해 `load_extra`로 읽었다. 전체 제공 문맥 6,306개에도 같은 조직 목록을 직접 적용해 적중 0개를 확인했다. 목록 내용이나 실제 needle은 출력·저장하지 않았다.

이 판정은 확인한 후보와 제공된 문맥 및 압축 원자료에 대한 독립 분류 결과다. 허용값만으로 이후 모든 변경의 안전성을 보장하지 않으며, 최종 발행 파일과 staged 내용의 검사는 root의 발행 절차에서 다시 수행한다.
