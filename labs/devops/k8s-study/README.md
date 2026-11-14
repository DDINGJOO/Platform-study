# k8s 스터디 실습 원자료

`posts/CS/DevOps/k8s-study/` 시리즈가 인용하는 실행 출력이다. 글의 숫자와 화면은 모두 여기서 나왔다.

## 환경

실습 클러스터는 [k8s-playground](https://github.com/DDINGJOO/k8s-playground) 저장소의 `./lab up` 으로 만들었다.

| 항목 | 값 |
|---|---|
| 호스트 | Apple Silicon Mac, Lima 2.2.1 (vmType: vz) |
| 노드 | k8s-master 1대 + k8s-worker1~3, 각 CPU 2 · 메모리 4GiB |
| OS | Ubuntu 24.04.5 LTS, 커널 6.8.0-142-generic (arm64) |
| 쿠버네티스 | v1.37.2 (kubeadm · kubelet · kubectl) |
| 런타임 | containerd 2.4.1 (Lima 의 nerdctl-full 번들) |
| CNI | Calico v3.33.0 (매니페스트 설치, IPIP) |
| 노드 네트워크 | eth0 = Lima user-v2 192.168.104.0/24 (VM 끼리), lima1 = vzNAT 192.168.64.0/24 (Mac 에서 VM 으로) |
| 파드 / 서비스 대역 | 10.244.0.0/16 / 10.96.0.0/12 |

여기 나오는 192.168.x · 10.x 주소는 모두 이 Mac 안에서만 존재하는 실습 VM·파드 주소다.

## 파일

| 파일 | 내용 | 쓰는 편 |
|---|---|---|
| `out/01-components.txt` | kube-system 파드와 소유자(Node · DaemonSet · ReplicaSet), 정적 파드 매니페스트 | 1편 |
| `out/02-pod-flow.txt` | Deployment 하나를 만들 때의 이벤트, etcd 키, 노드의 컨테이너, iptables 규칙 | 2편 |
| `out/03-lab-up-first-run.txt` | VM 생성부터 노드 4대 Ready 까지 `./lab up` 첫 실행 출력 | 3편 |
| `out/03-network-matrix.txt` | 두 네트워크의 도달 가능성(VM↔VM, Mac→VM) ping 결과 | 3편 |
| `out/04-node-prep.txt` | swap · 커널 모듈 · sysctl · containerd 설정 · cgroup 드라이버 · node-ip | 4편 |
| `out/04-swap-experiment.txt` | 워커 한 대에 swap 을 켰을 때 kubelet 이 시작을 거부하고 노드가 NotReady 가 되는 과정 | 4편 |
| `out/05-kubeadm-init.txt` · `05-kubeadm-join.txt` | kubeadm init · join 출력 | 5편 |
| `out/05-kubeadm-artifacts.txt` | kubeadm 설정 파일, 만들어진 인증서·kubeconfig, 노드 CSR | 5편 |
| `out/06-calico.txt` | Calico 설정, 노드별 파드 대역, 라우팅 표, 노드 간 통신, NetworkPolicy 실험 | 6편 |
| `out/07-hostpath.txt` | Mac 폴더를 hostPath 로 붙인 nginx 에서 파일 수정이 바로 반영되는 과정 | 7편 |
| `out/07-stale-ready-first-seen.txt` · `07-stale-ready-repro.txt` · `07-restart-after-fix.txt` | 재시작 직후 Ready 판정 문제의 첫 발견, 재현 시도, 수정 후 | 7편 |
| `out/07-kubectl-skew.txt` | Mac 의 kubectl 과 클러스터 버전 차이 | 7편 |
| `out/07-partial-restart.txt` | 대기 조건 2차 수정 뒤, worker3 한 대만 꺼져 있던 상태에서 `./lab up` | 7편 |
| `out/07-boot-hang.txt` | VM 한 대가 부팅 첫 단계에서 멈춘 기록과 강제 재시작 | 7편 |
| `out/08-observability-checks.txt` | 이벤트 보관 시간(--event-ttl 기본 1시간)으로 지워진 파드의 이벤트가 사라지는 과정, Metrics API 유무, `up`·`absent()` 질의 | 8편 |
| `out/09-dashboard-retired.txt` | Kubernetes Dashboard 저장소 아카이브, README 의 Headlamp 권고, helm 저장소 404, v2.7.0 호환표 | 9편 |
| `out/09-headlamp-install.txt` · `09-headlamp-resources.txt` | Headlamp Helm 설치와 함께 생긴 리소스 | 9편 |
| `out/09-apiserver-proxy.txt` · `09-apiproxy-infinite-loading.txt` · `09-baseurl-attempt.txt` | API 서버 프록시 접속: 인증서 유무, 로그인 뒤 404 반복, base URL 시도 | 9편 |
| `out/09-macos-local-network.txt` · `09-nodeport-close.txt` | macOS 로컬 네트워크 권한, 포트포워드로 바꾸고 NodePort 닫기 | 9편 |
| `out/10-admin-user.txt` · `10-namespace-move.txt` · `10-alias.txt` · `10-long-lived-token.txt` | admin-user RBAC, 전용 네임스페이스 이전, getToken 별칭, 토큰 수명 | 10편 |
| `out/10-recheck.txt` | 글을 쓰며 다시 확인한 apiserver 플래그, `--duration=0` 토큰의 수명, 평소 kubeconfig 로 본 whoami | 10편 |
| `out/11-kps-install.txt` | kube-prometheus-stack 설치 시도, Operator 이미지 ImagePullBackOff 와 같은 노드에서 다시 받아 본 오류 원문 | 11편 |
| `out/11-lecture-prometheus.txt` · `11-prometheus-targets.txt` | 강의 매니페스트 적용과 수집 대상 14개 | 11편 |
| `out/11-node-exporter-before.txt` · `11-node-exporter-after.txt` | node-exporter Service 가 파드를 못 고른 문제와 고친 뒤 | 11편 |
| `out/12-grafana-6417.txt` · `12-jobs-panel.txt` | 6417 대시보드가 찾는 메트릭과 지금 이름, Jobs 패널 확인 | 12편 |
| `out/12-recheck.txt` | 글을 쓰며 다시 조회한 노드 할당량·요청량 합계, 노드 조건 종류, node-exporter 가 보는 파일 시스템과 노드의 실제 df | 12편 |
| `out/13-ebpf-kernel.txt` · `13-kprobe-demo.txt` | 노드 커널의 eBPF·kprobe 설정, worker1 의 tcp_v4_connect 에 5초 건 kprobe 결과(외부 공인 IP 1건은 가림) | 13편 |
| `out/14-ks-cli.txt` · `14-ks-tap.txt` | Kubeshark CLI 설치와 ks 별칭, 사용자가 실행한 ks tap·ks proxy 출력 | 14편 |
| `out/14-ks-resources.txt` · `14-ks-license.txt` · `14-ks-resource-usage.txt` | Helm 리소스 21개, worker 권한·마운트, ClusterRole, 라이선스 창, 대상 좁히기 전후 메모리, kubeshark clean | 14편 |
| `out/15-myweb-setup.txt` · `15-phases.txt` · `15-nginx-counts.txt` | 샘플 앱 준비, 4단계 트래픽 실험(traffic.sh, KFL 필터), nginx 접근 로그로 센 파드별 요청 수 | 15편 |
| `out/16-portainer-manifest.txt` · `16-local-path.txt` · `16-portainer-install.txt` | 슬라이드 매니페스트 404 와 공식 주소, local-path 설치와 기본 지정 해제, 정적 PV·Portainer 설치·첫 관리자(값은 싣지 않음) | 16편 |
| `out/17-portainer-steps.txt` · `17-portainer-quota.txt` | kubectl 로 넣고 빼며 본 Portainer 화면 변화, Quota 512M 네임스페이스와 두 앱(0/2, 3/5) | 17편 |
| `out/18-k9s-install.txt` · `18-k9s-tour.txt` · `18-k9s-01-start.txt` ~ `18-k9s-12-help.txt` | k9s 설치, tmux 안에서 k9s 를 돌리며 저장한 화면 12장 | 18편 |
| `out/19-architecture-snapshot.txt` · `19-arch-diagram-check.txt` · `19-cluster-overview.txt` | 클러스터 구성 요소 스냅숏, API 서버 인증·인가·어드미션 플래그, BGP 피어, 서비스 이름 풀이 | 19편 |
| `out/19-hub-and-authz.txt` · `19-authn-and-spokes.txt` (+ `.sh`) | 구성 요소별 TCP 연결(누가 6443·2379·10250 에 붙나), 10.96.0.1:443 으로 붙는 파드, 익명·가짜 토큰·권한 없는 요청, 어드미션이 붙이는 필드 | 19·32·33편 |
| `out/20-stop-apiserver.txt` · `20-stop-scheduler.txt` · `20-stop-controller-manager.txt` (+ `20-stop-control-plane.sh`) | 정적 파드 매니페스트를 잠시 옮겨 API 서버·스케줄러·컨트롤러 매니저를 하나씩 멈춘 기록 | 20편 |
| `out/20-api-resources.txt` · `20-crd-origin.txt` (+ `.sh`) | `kubectl api-resources` 94종과 그룹별 개수, CRD 23개가 만들어진 시각 | 20편 |
| `out/21-ha-capacity.txt` · `21-leases.txt` · `21-n-plus-one.txt` (+ `.sh`) | kubeadm ClusterConfiguration, etcd 멤버, 리더 Lease, 워커별 allocatable·requests, worker3 를 후보에서 뺀 N+1 실험 | 21편 |
| `out/22-etcd-ssot.txt` · `22-etcd-access.txt` · `22-optimistic-lock.txt` (+ `.sh`) | etcd 키, resourceVersion 과 mod_revision, 저장 형식, 실습용 Secret 의 etcd 원본, etcd 접근 인증서, 409 Conflict | 22편 |
| `out/22-etcd-encryption.txt` (+ `.sh`) | etcd 스냅숏 안의 평문 Secret, EncryptionConfiguration(aescbc) 을 켰다가 문서 순서대로 끈 기록 | 22편 |
| `out/23-scheduler-filter.txt` · `23-scheduler-score.txt` · `23-worker3-priority.txt` (+ `.sh`) | FailedScheduling 메시지, 스케줄러 /configz, preferred·required·조건 없는 파드의 점수 계산과 실제 배치, worker3 파드 우선순위 | 23편 |
| `out/24-ccm.txt` · `24-calico-lb.txt` · `24-calico-lb-log.txt` (+ `.sh`) | KCM 컨트롤러 목록, CCM 없을 때 LoadBalancer pending, Calico LoadBalancer IPAM 으로 IP 받기, 그때의 calico-kube-controllers 로그 | 24편 |
| `out/25-node-object.txt` · `25-kubelet-stop.txt` · `25-endpointslice.txt` (+ `.sh`) | 노드 객체·Lease 하트비트·KCM 기본값, kubelet 정지 뒤 Unknown·taint, EndpointSlice ready | 25편 |
| `out/25-eviction.txt` (+ `.sh`) | worker3 kubelet 을 약 29분 멈춘 기록: taint 300초 뒤 축출·재생성, Terminating 으로 남은 옛 파드 강제 삭제, IPAM 에 남은 IP | 19·21·25·34편 |
| `out/25-felix-route-remove.txt` (+ `.sh`) | 강제 삭제 순간 worker3 의 Felix 가 그 파드 경로를 지운 calico-node 로그(Local endpoint deleted, RouteRemove) | 25·34편 |
| `out/26-oci.txt` · `26-pstree.txt` · `26-restart-runtime.txt` · `26-kubelet.txt` · `26-extra-check.txt` (+ `.sh`) | runc 와 OCI 번들, 마스터 pstree, containerd·kubelet 재시작, 컨테이너 재시작·미러 파드, 부팅·시작 시각 | 26편 |
| `out/27-container-runtime.txt` · `27-image-service.txt` · `27-oom-group.txt` · `27-overlay-share.txt` · `27-sandbox-lifecycle.txt` · `27-endpoint-check.txt` (+ `.sh`) | CRI 호출 순서, cgroup cpu.max·memory.max, OOMKilled 와 memory.oom.group, overlayfs 레이어 공유, 샌드박스 수명, CRI 엔드포인트 | 27편 |
| `out/28-kube-proxy.txt` · `28-proxy-modes.txt` · `28-clusterip-wire.txt` · `28-nat-hooks.txt` (+ `.sh`) | ClusterIP iptables 규칙, 규칙 갱신, kube-proxy 삭제 중 트래픽, tcpdump 로 본 DNAT, 연결 분배, 모드 목록 | 28편 |
| `out/28-kubeproxy-stale.txt` (+ `.sh`) | worker1 의 kube-proxy 만 잠시 뺀 동안 파드 수를 바꿨을 때 그 노드의 옛 규칙과 curl 실패 | 19·28편 |
| `out/29-coredns-redis.txt` · `29-addons.txt` · `29-dns-search.txt` · `29-coredns-dnspolicy.txt` (+ `.sh`) | redis-dns Service 이름 풀이(같은·다른 네임스페이스), search·ndots 질의 수, 환경 변수 시점, CoreDNS·add-on 상태 | 29편 |
| `out/30-calico-bird.txt` · `30-stop-bird.txt` · `30-route-del.txt` · `30-route-owner.txt` (+ `.sh`) | BIRD·Felix·BGP 세션, BIRD 정지와 경로 삭제 실험, 경로를 넣는 쪽(programClusterRoutes) | 30편 |
| `out/30-calicoctl-install.txt` · `30-calicoctl-tour.txt` · `30-calicoctl-node-status.txt` (+ `.sh`) | calicoctl 설치·둘러보기, node status 가 "not running" 으로 나오는 이유 | 30편 |
| `out/31-ip-lifecycle.txt` · `31-ipam-blocks.txt` · `31-veth-and-empty-block.txt` · `31-containerd-cni-timeline.txt` · `31-kube-controllers-ipam-log.txt` · `31-pool-sizing.txt` (+ `.sh`) | CNI ADD·DEL 과 IPAM 핸들·블록, podCIDR 과 Calico 블록, 블록이 찼을 때·빈 블록 반납, veth 이름 규칙, 풀 크기 | 31·34편 |
| `out/31-leak-gc-blocked.txt` | 노드가 죽은 동안 새로 뜬 calico-kube-controllers 가 IPAM 정리를 시작하지 못한 로그와 v3.33.0 소스 발췌, IP 를 돌려준 CNI DEL | 19·34편 |
| `out/32-tls-authn.txt` · `32-rbac-sa.txt` · `32-node-authz.txt` · `32-kubectl-messages.txt` · `32-anon-cluster-info.txt` (+ `.sh`) | TLS·인증서 신원, 401 과 403, RoleBinding 전후, Node 인가자·NodeRestriction, 관문별 kubectl 오류 문구, 익명으로 읽히는 cluster-info | 32편 |
| `out/33-admission.txt` (+ `.sh`) | 어드미션 플러그인 목록(바이너리·문서), mutating 결과, ResourceQuota·LimitRange·PodSecurity 거절 | 33편 |

## 35~50편 원자료 (2026-11-14)

글별 링크와 교정·검증 결과는 [35~50편 작성·검토 기록](review-35-50.md)에서 확인할 수 있다.

숫자와 시각은 파일에 기록된 실험 시점의 값이다. 설정 변경·복원 실험이 서로 다른 시점에 진행됐으므로 리비전과 누적 메트릭을 파일 사이에서 합산하지 않는다.

| 편 | 출력 파일 (`out/`) | 확인한 내용 |
|---|---|---|
| 35편 | [35-apiserver-clients.txt](out/35-apiserver-clients.txt) · [35-connection-map.txt](out/35-connection-map.txt) · [35-apiserver-protocols.txt](out/35-apiserver-protocols.txt) · [35-etcd-clients.txt](out/35-etcd-clients.txt) · [35-etcd-certs.txt](out/35-etcd-certs.txt) · [35-control-plane.txt](out/35-control-plane.txt) · [35-apiserver-where.txt](out/35-apiserver-where.txt) · [35-node-roles.txt](out/35-node-roles.txt) · [35-scheduler-cycle.txt](out/35-scheduler-cycle.txt) · [35-controller-manager.txt](out/35-controller-manager.txt) | 프로세스·포트·프로토콜·신원별 연결 지도와 정적 파드 |
| 36편 | [36-apiserver-manifest.txt](out/36-apiserver-manifest.txt) · [36-apiserver-where.txt](out/36-apiserver-where.txt) · [36-apiserver-requests.txt](out/36-apiserver-requests.txt) · [36-apiserver-metrics-snapshot.txt](out/36-apiserver-metrics-snapshot.txt) · [36-apiserver-request-mix.txt](out/36-apiserver-request-mix.txt) · [36-apf-classify.txt](out/36-apf-classify.txt) · [36-aggregation-idle.txt](out/36-aggregation-idle.txt) · [36-kubelet-serving-cert.txt](out/36-kubelet-serving-cert.txt) · [36-privileged-ds.txt](out/36-privileged-ds.txt) · [36-validation-vs-admission.txt](out/36-validation-vs-admission.txt) · [36-order-and-nodename.txt](out/36-order-and-nodename.txt) | API 서버 플래그, 요청 구성·APF, 객체 검증 422와 어드미션 403의 순서 |
| 37편 | [37-master-workload.txt](out/37-master-workload.txt) · [37-node-roles.txt](out/37-node-roles.txt) · [37-master-taints-now.txt](out/37-master-taints-now.txt) | 마스터 taint와 toleration, nodeSelector·nodeName에 따른 배치 |
| 38편 | [38-control-plane.txt](out/38-control-plane.txt) · [38-etcd-btree.txt](out/38-etcd-btree.txt) · [38-etcd-compaction-defrag.txt](out/38-etcd-compaction-defrag.txt) · [38-etcd-flags.txt](out/38-etcd-flags.txt) · [38-etcd-watch-registry.txt](out/38-etcd-watch-registry.txt) | MVCC·리비전·bbolt, 컴팩션과 조각 모음, 파드 하나의 키 변경 |
| 39편 | [39-cache-consistency.txt](out/39-cache-consistency.txt) · [39-dns-source.txt](out/39-dns-source.txt) · [39-kubectl-get-v6.txt](out/39-kubectl-get-v6.txt) · [39-read-semantics.txt](out/39-read-semantics.txt) | watch 캐시와 읽기 일관성, 410·409, CoreDNS 반영 |
| 40편 | [40-etcd-backup-cronjob.txt](out/40-etcd-backup-cronjob.txt) · [40-etcd-snapshot-restore.txt](out/40-etcd-snapshot-restore.txt) · [40-etcd-restore-rehearsal.txt](out/40-etcd-restore-rehearsal.txt) · [40-restore-aftermath.txt](out/40-restore-aftermath.txt) | etcd 3.7 스냅숏·CronJob, 실제 복원과 리비전 증가·복원 뒤 상태 |
| 41편 | [41-scheduler-cycle.txt](out/41-scheduler-cycle.txt) · [41-scheduler-steps.txt](out/41-scheduler-steps.txt) · [41-apiserver-requests.txt](out/41-apiserver-requests.txt) · [41-etcd-clients.txt](out/41-etcd-clients.txt) | 스케줄러 대상·바인딩·캐시·큐와 확장 지점 |
| 42편 | [42-controller-manager.txt](out/42-controller-manager.txt) · [42-controller-identities.txt](out/42-controller-identities.txt) | 내장 컨트롤러 목록과 재조정, ServiceAccount·RBAC·ServiceCIDR·EndpointSlice |
| 43편 | [43-pod-sandbox.txt](out/43-pod-sandbox.txt) · [43-pause-vs-app-kill.txt](out/43-pause-vs-app-kill.txt) · [43-pause-kill-timeline.txt](out/43-pause-kill-timeline.txt) | 파드 샌드박스·네임스페이스, 앱과 pause 종료의 차이 및 복구 시각 |
| 44편 | [44-maxpods-capacity.txt](out/44-maxpods-capacity.txt) · [44-fill-110.txt](out/44-fill-110.txt) | maxPods·노드 할당량, 111번째 파드 거절과 PLEG·메모리·IPAM 관찰 |
| 45편 | [45-runtime-no-docker.txt](out/45-runtime-no-docker.txt) · [45-docker-sock.txt](out/45-docker-sock.txt) | Docker 없는 런타임 구성, docker.sock 유무와 CRI 소켓 |
| 46편 | [46-apiserver-protocols.txt](out/46-apiserver-protocols.txt) · [46-client-content-types.txt](out/46-client-content-types.txt) · [46-grpc-vs-rest.txt](out/46-grpc-vs-rest.txt) | API 클라이언트의 REST·protobuf와 etcd·CRI의 gRPC 경계 |
| 47편 | [47-proxy-mode-and-iptables-backend.txt](out/47-proxy-mode-and-iptables-backend.txt) · [47-iptables-vs-nftables.txt](out/47-iptables-vs-nftables.txt) | Service 1,000개에서 iptables·nftables 규칙·동기화·연결 시간 비교와 원복 |
| 48편 | [48-etcd-raft-single-member.txt](out/48-etcd-raft-single-member.txt) | 단일 etcd 멤버의 Raft 지표와 30초 동안의 커밋·리비전 차이 |
| 49편 | [49-heartbeat-numbers.txt](out/49-heartbeat-numbers.txt) · [49-heartbeat-etcd-cost.txt](out/49-heartbeat-etcd-cost.txt) | 하트비트 설정과 60초 동안 Node·Lease 쓰기 횟수·저장 크기 |
| 50편 | [50-evict-30-vs-300.txt](out/50-evict-30-vs-300.txt) · [50-three-workers-down.txt](out/50-three-workers-down.txt) | toleration 30초·300초 축출 비교, 워커 3대 동시 정지 시 부분 장애 전환 |

- 같은 이름의 `.sh`는 출력을 만든 스크립트이며 실습 저장소 루트에서 실행한다. 일부 출력은 스크립트 실행 뒤 별도로 조회한 결과를 덧붙였고, 이 경우 파일 머리나 해당 절의 설명을 함께 읽는다.
- `40-etcd-backup-cronjob.yaml`은 백업 실험용 매니페스트다. `50-watch_nodes.py`는 노드·taint·파드의 변화를 기록한 관찰 도구다.
- 40편 복원은 `--bump-revision`과 `--mark-compacted`를 사용했다. 그 뒤 원자료의 큰 리비전 값은 이 복원 실험의 영향이다.
- 50편의 전체 워커 정지 실험은 VM 전원이나 데이터 경로를 끊은 실험이 아니라 kubelet을 정지한 실험이다. 두 장애 방식의 차이는 본문에 적었다.

## 손댄 곳

- 각 블록 첫 줄의 `노드$ 명령` 은 그 출력을 만든 명령을 그대로 적은 것이다. 실제로는 Mac 에서 `./lab ssh <노드> bash -c '<명령>'` 으로 실행했다.
- `05-kubeadm-*.txt` 는 `./lab up` 의 로그 파일에서 발췌했고, 부트스트랩 토큰은 `abcdef.0123456789abcdef`, CA 해시는 `sha256:<CA 공개키 해시>` 로 바꿨다.
- `03-lab-up-first-run.txt` 는 출력의 색 코드를 지우고 저장소 경로를 `~/k8s-playground` 로 바꿨다.
- `07-stale-ready-first-seen.txt` · `07-boot-hang.txt` · `09-macos-local-network.txt` · `09-baseurl-attempt.txt` · `11-kps-install.txt`(뒷부분) 는 작업 세션의 명령 기록에서 옮겼다(그 실행의 원본 로그 파일은 없다). 홈 경로의 사용자 이름은 `<사용자>` 로 바꿨다.
- `14-ks-tap.txt` · `16-portainer-install.txt` 의 홈 경로·파일 소유자 사용자 이름은 `<사용자>` 로 바꿨다. `16-portainer-install.txt` 에는 Portainer 관리자 비밀번호와 setup token 값을 싣지 않았다.
- `15-nginx-counts.txt` 의 괄호 안 비율은 반올림 값이다.
- `10-*.txt` 에는 토큰 본문을 싣지 않았다. 토큰은 `iat`·`exp`·`sub` 만 꺼내 찍었고, `10-recheck.txt` 의 클라이언트 인증서 지문은 `<클라이언트 인증서 지문>` 으로 바꿨다.
- `19-*` ~ `31-*` 의 `.sh` 는 실습 저장소 `shared/arch-exp/` 의 스크립트를 그대로 옮긴 것이다. 실습 저장소 루트에서 `bash <스크립트>` 로 돌린다. 구성 요소를 멈추는 스크립트(20·25·26·30편)는 끝에서 원래대로 되돌린다.
- `30-calicoctl-*.txt` · `22-etcd-encryption.txt` 등의 홈 경로 사용자 이름은 `<user>` 로, `29-*.txt` 의 공유기 검색 도메인은 `<router-domain>` 으로 바꿨다. `22-etcd-encryption.txt` 에는 암호화 키 값을 싣지 않았다.
- `26-kubelet.txt` 의 '(이어서 6초마다 …)' 아래 줄은 스크립트 밖에서 같은 조회를 6초 간격으로 10번 돌린 결과다. `30-route-del.txt` 의 '이어서 관찰' 줄은 5초 간격 조회 결과를 옮겨 적은 것이다.
- `28-kubeproxy-stale.txt` 실험은 kube-proxy DaemonSet 에 nodeAffinity 를 잠시 넣었다가 지웠다(그동안 다른 노드의 kube-proxy 도 다시 떴다). `22-etcd-encryption.txt` 실험은 API 서버 매니페스트를 바꿨다가 원래대로 되돌렸다.

## 8~18편 환경 추가

- Helm v3.22.1(마스터), Headlamp 0.46.0(차트 0.46.0, 네임스페이스 headlamp), Prometheus 3.16.0 · node-exporter(latest) · Grafana 13.3.0 · kube-state-metrics v2.20.0 (강의 저장소 github.com/brayanlee/k8s-prometheus 매니페스트를 고쳐 적용, 네임스페이스 monitoring)
- 강의 저장소에서 고친 내용은 실습 저장소 `shared/k8s-prometheus` 의 `git diff` 로 볼 수 있다. 강의 저장소에는 라이선스가 없어 파일 전체를 이 저장소에 옮기지 않았다.
- 13~18편(2026-11-11): Kubeshark v53.6.0(Helm 차트 53.6.0, default 네임스페이스, 실습 뒤 kubeshark clean), local-path-provisioner v0.0.37(기본 지정 해제), Portainer CE 2.45.3 LTS(portainer 네임스페이스, 정적 PV portainer-pv = worker1 의 /DATA1), k9s v0.51.0(마스터)
- 19~31편(2026-11-14): calicoctl v3.33.0(마스터 /usr/local/bin). 이날 노드 커널은 6.8.0-147-generic. 실험용으로 만든 리소스(파드·Service·IPPool·네임스페이스)는 실험마다 지웠다.
