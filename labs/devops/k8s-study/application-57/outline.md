# 57편: 실제 앱 배포로 기초 학습 마무리

- 목표: replicas=1 앱의 첫 응답, Ready 전후 차이, DNS/Service 요청, v2 rollout, Pod 교체를 실제로 관찰한다.
- 범위: 배포 완료 판단과 사용자 요청의 연속성. 2편 생성 원리, 23/41 스케줄링, 28/29 Service·DNS, 51–56 Calico 심층은 반복하지 않는다.
- 출력: HTML 1편, 소스와 재현 매니페스트, 원본 JSON/요청 표본, 실행 화면, 검수·감사 결과.
- 종료: 실제 NodePort와 내부 Service가 v2로 응답하고 임시 클라이언트가 삭제되며 앱1개가 Ready. 게시/커밋은 별도 승인.

## 구성
1. 앱의 성공 기준과 실제 화면
2. Deployment→ReplicaSet→이번 Pod 소유 관계와 런타임·CNI 결과
3. Running/Ready/Endpoint/실제 HTTP를 구분하는 준비 지연 및 readiness 실패
4. DNS→Service→이번 Pod의 요청 ID와 로그 연결
5. v2 준비 전후의 rollout과 연속 HTTP 표본
6. Pod 교체 후 유지되는 Service와 바뀌는 identity; 단일 replica의 한계

앱 소스는 학습상 ConfigMap에 고정하고 Python 이미지는 digest로 고정한다. v2 실험은 APP_VERSION 구성 변경이며 이미지 교체·CI/CD 검증이라고 하지 않는다. 메모리 요청 수는 영속 저장이 아니다. 리소스는 최소 requests/limits만 두고 심층은 후속 학습 범위다.
