# 57편 사실관계 패널 2차: 변경 부분 재확인

- 판정: **통과, 남은 지적 0건**.
- 현재 HTML SHA-256: `da424347c95234fd95793d3f1563ee6631e94e116a50ed3bd457887f3a98a7ea`
- 검수 범위: 1차 지적 F1의 도입부 수정과 이번에 추가·이동된 독자 설명만 확인했어요. HTML은 수정하지 않았어요.

| 변경 | 대조 근거 | 결과 |
|---|---|---|
| 초기 실패를 브라우저 관찰 대신 노드30057번 포트의 curl 관찰로 수정 | `03-early-direct-*`, `04-early-nodeport.json`, `run.py` | F1 해결 |
| 같은 순간이라는 표현을 같은 초기 준비 구간의 순차 요청으로 한정 | 동일 원본의 순서 및 기록 시각 | F1 해결 |
| client.json 적용·Ready 대기·실제 노드에 맞춘 nodeSelector 조정 안내 | `client.json`은 k8s-worker2, `run.py`의 apply/wait, `08-client-create.json` | 확인 |
| NodePort 설명을 첫 화면 이전으로 이동 | 매니페스트 Service의 type·nodePort | 내용 유지, 사실 변경 없음 |
| UID를 처음 등장할 때 객체 식별자라고 설명 | 기존 UID 교체 관측 | 정확 |
| Downward API 공식 링크 추가 | [공식 Downward API 문서](https://kubernetes.io/docs/concepts/workloads/pods/downward-api/)의 fieldRef와 환경 변수 필드 목록 | metadata.name·spec.nodeName·status.podIP 주입과 일치 |
| 임시 client 삭제 명령 추가 | `28-client-cleanup.json`의 delete pod request-client 성공 | 확인 |

1차 1건을 해결했고, 변경 부분에서 새 사실관계 지적은 없어요.
