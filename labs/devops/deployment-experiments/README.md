# 배포 관측과 A/B 실험

사용자가 요청한 Netflix 도구 기반 카나리 시각화와 기능 A/B 실험 방법을 실제 로컬 실행으로 확인한다. 모든 서비스·사용자·전환은 가상 데이터다. 운영 트래픽이나 제품 효과를 측정한 결과가 아니다.

| 편 | 실습 | 질문 |
|---|---|---|
| 1 | [canary](canary/README.md) | 새 베이스라인 A′와 B를 실제 Kayenta로 비교하면 어떻게 판정하나? |
| 2 | [sticky-ab](sticky-ab/README.md) | 재요청·재기동에도 사용자 할당과 노출·전환 분모가 유지되나? |
| 3 | [decision](decision/README.md) | SRM·표본·에러·지연을 거른 뒤 전환율 차이를 어떻게 해석하나? |

각 디렉터리는 독립 실행 안내, 버전, 실제 결과와 한계를 제공한다. 글은 [시리즈 지도](../../../posts/CS/DevOps/deployment-experiments/ROADMAP.md)에 연결한다. 검수 결과는 `validation/`에 기록한다.

A는 먼저 기동한 기존 버전, A′는 같은 버전과 설정을 새로 띄운 대조군, B는 같은 시점에 띄운 변경본이다. 주 비교는 A′와 B이며 A와 A′는 재배포 영향 진단에 사용한다. 배포 안전성 판정과 사용자 단위 기능 실험은 다른 의사결정이다.

다른 Docker 프로젝트는 정리하지 않는다. 각 실습의 `docker compose down`으로 자기 프로젝트만 종료한다. 최초 설치·실행은 인터넷과 Docker Engine/Desktop, Compose, 각 실습에 적힌 Python 버전이 필요하다. 재캡처는 기존 Playwright·Chrome 환경을 사용하며 실행 코드와 분리한다.


## 실행 순서

다른 실습에 영향을 주지 않도록 한 번에 하나씩 실행한다. 1편은 몇 분의 실제 측정이 필요하다.

```sh
python3 labs/devops/deployment-experiments/canary/run.py
python3 labs/devops/deployment-experiments/canary/verify.py
python3 labs/devops/deployment-experiments/sticky-ab/run.py
# 3편은 고정 fixture의 계산과 HTTP 보고서를 함께 실행한다.
docker compose -f labs/devops/deployment-experiments/decision/compose.yaml up -d --force-recreate
python3 labs/devops/deployment-experiments/decision/verify.py
```

1편 runner는 자기 프로젝트의 Redis·Prometheus 볼륨을 초기화하므로 같은 실행을 확인할 때는 `verify.py`를 쓴다. 2편 저장 데이터로 UI만 재확인할 때는 해당 README의 `EXPERIMENT_ID` 복구 명령을 따른다. 기본 `compose up`은 저장된 실행 ID를 자동으로 복원하지 않는다. 3편 고정 fixture의 날짜는 합성 사건 시각이며 실제 일주일간 운영한 결과가 아니다.

기본 URL은 1편 Deck `http://localhost:28100`, Grafana `http://localhost:28105`; 2편 Grafana `http://localhost:28200`; 3편 자체 분석 보고서 `http://localhost:28300`이다. 종료된 스택에서는 접근되지 않는다. 1편은 Kayenta의 메모리 저장소를 사용하므로 종료 뒤 재시작하면 원래 보고서 객체가 남는다고 보장하지 않는다. 저장된 원자료와 캡처는 파일에 유지한다.

## 검사

```sh
python3 labs/devops/deployment-experiments/validation/validate.py
# 기존 Playwright·Chrome 환경이 있을 때:
python3 labs/devops/deployment-experiments/validation/validate.py --browser
```

형식·브라우저 검사는 기술 내용의 정확성을 증명하지 않는다. 네 관점 퇴고와 별도 원자료 감사, 실제 서비스 검증 기록을 함께 확인한다.
