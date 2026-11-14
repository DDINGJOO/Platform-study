#!/usr/bin/env bash
# 실습 저장소의 shared/why/04-dockershim-removal/01-runtime-no-docker.sh 를 옮긴 것. 실습 저장소 루트에서 실행한다.
# dockershim 이 빠진 뒤의 노드 확인(조회만): 노드별 런타임 이름, kubelet 이 부르는 CRI 엔드포인트, docker 계열 바이너리·소켓 유무, kubelet 에 남은 docker 흔적, containerd CRI 플러그인 설정, cgroup 버전, docker.sock 을 마운트한 파드 (Mac 에서 실행)
cd "$(dirname "$0")/../../.."   # 실습 저장소 루트 (./lab 이 있는 곳)
K="./lab kubectl"
echo "# 04 dockershim 제거 뒤 우리 노드 ($(date '+%F %T %Z'))"

echo; echo "## 1. API 서버가 아는 노드별 런타임 (status.nodeInfo)"
$K get nodes -o custom-columns='NAME:.metadata.name,KUBELET:.status.nodeInfo.kubeletVersion,CONTAINER-RUNTIME:.status.nodeInfo.containerRuntimeVersion,KERNEL:.status.nodeInfo.kernelVersion'

echo; echo "## 2. 노드마다: docker 계열 바이너리·소켓, kubelet 이 부르는 엔드포인트, cgroup 버전"
for n in master worker1 worker2 worker3; do
  echo "### $n"
  ./lab ssh $n -- sudo bash -s <<'R'
for b in docker dockerd cri-dockerd containerd runc crictl nerdctl; do printf '  %-12s %s\n' "$b" "$(command -v $b || echo '(없음)')"; done
for s in /var/run/docker.sock /var/run/dockershim.sock /var/run/cri-dockerd.sock /run/containerd/containerd.sock; do
  if [ -S "$s" ]; then echo "  소켓 있음: $s"; else echo "  소켓 없음: $s"; fi
done
echo "  systemd: docker=$(systemctl is-active docker 2>/dev/null) containerd=$(systemctl is-active containerd 2>/dev/null)"
echo "  kubelet config.yaml: $(grep -E '^containerRuntimeEndpoint' /var/lib/kubelet/config.yaml)"
echo "  kubelet 실행 인자 중 runtime·docker 관련: $(ps -o args= -C kubelet | tr ' ' '\n' | grep -E 'runtime|docker' || echo '(없음)')"
echo "  /sys/fs/cgroup 파일시스템 = $(stat -fc %T /sys/fs/cgroup)"
R
done

echo; echo "## 3. kubelet v1.37.2 바이너리에 남은 런타임·docker 관련 플래그 (worker1, kubelet --help)"
./lab ssh worker1 -- sudo bash -s <<'R'
kubelet --version
for fl in container-runtime container-runtime-endpoint image-service-endpoint docker-endpoint network-plugin cni-bin-dir; do
  L=$(kubelet --help 2>&1 | grep -E -- "--$fl ")
  if [ -z "$L" ]; then echo "  --$fl : (플래그 없음)"; else
    echo "  --$fl : 있음 $(echo "$L" | grep -oE '\(default "[^"]*"\)') $(echo "$L" | grep -q DEPRECATED && echo '(DEPRECATED: config 파일로 옮기라는 표시)')"; fi
done
echo "docker 라는 낱말이 나오는 플래그 수: $(kubelet --help 2>&1 | grep -ci docker)"
kubelet --help 2>&1 | grep -i docker | sed -E 's/ +/ /g' | cut -c1-200
R

echo; echo "## 4. containerd 의 CRI 플러그인 (worker1)"
./lab ssh worker1 -- sudo bash -s <<'R'
containerd --version
echo "--- 설치 때 쓴 설정 파일 (config.toml + conf.d/k8s.toml, 옛 v2 형식: io.containerd.grpc.v1.cri)"
for f in /etc/containerd/config.toml /etc/containerd/conf.d/*.toml; do echo "# $f"; sed -E 's/^ +/  /' "$f"; done
echo "--- ctr plugins ls 중 cri"
ctr plugins ls | awk 'NR==1 || /cri/'
echo "--- containerd namespaces (k8s.io = CRI 플러그인이 쓰는 곳, moby = Docker 가 쓰는 곳)"
ctr namespaces ls
echo "--- containerd config dump 중 CRI 플러그인 핵심 줄 (containerd 2.x 가 v4 형식으로 옮겨 읽은 결과: io.containerd.cri.v1.images / .runtime)"
containerd config dump 2>/dev/null | grep -E "^\s*\[plugins\.'io\.containerd\.cri\.v1\.(images|runtime)'\]$|sandbox = |default_runtime_name|runtime_type = 'io|SystemdCgroup|^\s*\[plugins\.'io\.containerd\.cri\.v1\.runtime'\.cni\]|bin_dirs|conf_dir = '/" | sed -E 's/^ +/  /'
R

echo; echo "## 5. 런타임 소켓을 hostPath 로 마운트한 파드 (공식 문서 'Migrating telemetry and security agents' 의 찾기 스크립트를 넓혀 씀)"
HP=$($K get pods -A -o=jsonpath='{range .items[*]}{.metadata.namespace}{"/"}{.metadata.name}{"\t"}{range .spec.volumes[*]}{.hostPath.path}{" "}{end}{"\n"}{end}')
echo "전체 파드 수: $(echo "$HP" | grep -c .) / hostPath 를 하나라도 쓰는 파드 수: $(echo "$HP" | awk -F'\t' '$2 ~ /[a-z]/' | grep -c .)"
M=$(echo "$HP" | grep -E 'docker\.sock|dockershim|cri-dockerd|containerd|( |\t)/var/run( |$)|( |\t)/run( |$)')
echo "docker.sock·dockershim·cri-dockerd·containerd 소켓 또는 /var/run 통째 마운트: ${M:-(없음)}"
echo "portainer 파드의 hostPath: $(echo "$HP" | awk -F'\t' '$1 ~ /^portainer\//{print ($2 ~ /[a-z]/ ? $2 : "(없음)")}')"

echo; echo "## 6. docker CLI 없이 노드의 컨테이너 보기: crictl(CRI) 과 nerdctl(containerd 직접, k8s.io 네임스페이스) (worker1)"
./lab ssh worker1 -- sudo bash -s <<'R'
echo "crictl pods (파드 샌드박스 수) = $(crictl pods -q | wc -l), crictl ps (앱 컨테이너 수) = $(crictl ps -q | wc -l)"
echo "nerdctl -n k8s.io ps (pause 포함 전체) = $(nerdctl -n k8s.io ps -q | wc -l)"
echo "nerdctl -n default ps = $(nerdctl -n default ps -q | wc -l)  (k8s 가 만든 컨테이너는 k8s.io 에만 있음)"
R
