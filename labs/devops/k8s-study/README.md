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

## 손댄 곳

- 각 블록 첫 줄의 `노드$ 명령` 은 그 출력을 만든 명령을 그대로 적은 것이다. 실제로는 Mac 에서 `./lab ssh <노드> bash -c '<명령>'` 으로 실행했다.
- `05-kubeadm-*.txt` 는 `./lab up` 의 로그 파일에서 발췌했고, 부트스트랩 토큰은 `abcdef.0123456789abcdef`, CA 해시는 `sha256:<CA 공개키 해시>` 로 바꿨다.
- `03-lab-up-first-run.txt` 는 출력의 색 코드를 지우고 저장소 경로를 `~/k8s-playground` 로 바꿨다.
- `07-stale-ready-first-seen.txt` 와 `07-boot-hang.txt` 는 작업 세션의 명령 기록에서 옮겼다(그 실행의 원본 로그 파일은 없다). 홈 경로의 사용자 이름은 `<사용자>` 로 바꿨다.
