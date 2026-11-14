#!/usr/bin/env bash
# 46편: kubelet 과 kube-proxy 가 API 서버에 보내는 요청 본문 형식(contentType)을 실제 적용된 설정(/configz)에서 읽는다. 조회만.
# 실습 저장소 루트(./lab 이 있는 곳)에서 bash <이 스크립트> 로 실행한다.
echo "# kubelet·kube-proxy 의 API 요청 형식 ($(date '+%F %T %Z'), Mac 에서 실습 저장소 루트로 실행, 조회만)"
echo; echo "## 1. kubelet (worker1, API 서버를 거쳐 /configz)"
./lab kubectl get --raw /api/v1/nodes/k8s-worker1/proxy/configz \
  | python3 -c "import json,sys;d=json.load(sys.stdin)['kubeletconfig'];print('  contentType:',d.get('contentType'),'/ kubeAPIQPS:',d.get('kubeAPIQPS'),'/ kubeAPIBurst:',d.get('kubeAPIBurst'))"
echo; echo "## 2. kube-proxy (worker1, 127.0.0.1:10249/configz)"
./lab ssh worker1 -- sudo bash -s <<'R'
curl -s 127.0.0.1:10249/configz | python3 -c "import json,sys;d=json.load(sys.stdin);c=d.get('kubeproxy.config.k8s.io',d)['clientConnection'];print('  contentType:',c.get('contentType'),'/ qps:',c.get('qps'),'/ burst:',c.get('burst'))"
R
echo "  (ConfigMap kube-proxy 의 clientConnection.contentType 은 \"\" 이고 위 값은 기본값이 채워진 결과)"
