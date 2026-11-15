from pathlib import Path
import re,json,html
root=Path('/Users/dding/orca/workspaces/Platform-study/k8s-study');d=Path(__file__).resolve().parent
manifest=json.loads((d.parent/'manifest.json').read_text());entry=next(x for x in manifest if x['number']==54)
template=Path('/Users/dding/orca/Platform-study/.claude/skills/tistory-sketch-post/assets/template.html').read_text();style=re.search(r'<style>.*?</style>',template,re.S).group()
series=(d.parent/'series.html').read_text().replace('{number}','54');line='54편. '+entry['title'];series=series.replace('  '+line+'<br>','  <b>'+line+'</b> &larr; 지금 이 글<br>')
def term(title,text):return f'<div class="obsv-term"><div class="obsv-tt">📖 용어: {title}</div>{text}</div>'
def call(title,text):return f'<div class="obsv-callout"><div class="obsv-ct">{title}</div>{text}</div>'
def code(s):return '<div class="obsv-code">'+html.escape(s)+'</div>'
def svg_start(n,h,label):return f'<div class="obsv-fig"><svg viewBox="0 0 700 {h}" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:700px;height:auto;" role="img" aria-label="{label}"><defs><marker id="p54-arr{n}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M1 1.5 Q5 3 8.5 5 Q5 7 1 8.5" fill="none" stroke="#3d3a34" stroke-width="1.6"/></marker></defs>'
def box(x,y,w,h,color='#4a7fb5',fill='#fffdf7'):
 return f'<path d="M{x} {y} C{x+w*.3} {y-2},{x+w*.7} {y+2},{x+w} {y} Q{x+w+2} {y+h/2},{x+w} {y+h} C{x+w*.7} {y+h+2},{x+w*.3} {y+h-2},{x} {y+h} Q{x-2} {y+h/2},{x} {y} Z" fill="{fill}" stroke="{color}" stroke-width="2.3" stroke-linejoin="round"/>'
def txt(x,y,t,size=22,color='#3d3a34'):return f'<text x="{x}" y="{y}" text-anchor="middle" font-family="\'Nanum Pen Script\',cursive" font-size="{size}" fill="{color}">{html.escape(t)}</text>'
def arrow(n,x1,y1,x2,y2):return f'<path d="M{x1} {y1} Q{(x1+x2)/2} {(y1+y2)/2-3},{x2} {y2}" fill="none" stroke="#3d3a34" stroke-width="2" marker-end="url(#p54-arr{n})"/>'
def end(n,cap):return f'</svg></div><div class="obsv-figcap">그림 {n}. {cap}</div>'
fig1=svg_start(1,230,'정책끼리는 합집합이고 발신 egress와 수신 ingress는 모두 허용되어야 함')+box(30,35,250,115)+txt(155,65,'client-a의 egress')+txt(155,98,'허용 정책들의 합집합',20)+txt(155,128,'server TCP 80 허용',20,'#2e6b41')+box(420,35,250,115)+txt(545,65,'server의 ingress')+txt(545,98,'허용 정책들의 합집합',20)+txt(545,128,'client-a TCP 80 허용',20,'#2e6b41')+arrow(1,290,92,408,92)+txt(350,75,'AND',20)+txt(350,199,'한쪽 방향만 허용해도 된다는 뜻은 아니에요',23,'#b3502f')+end(1,'각 방향 안에서는 허용을 더하고 두 방향 사이에서는 모두 허용돼야 해요.')
fig2=svg_start(2,240,'DNS를 UDP만 허용한 상태와 TCP도 허용한 상태의 관측')+box(30,35,250,130,'#e5a33c','#fdf3dd')+txt(155,68,'UDP 53만 허용')+txt(155,105,'UDP 질의: 응답',22,'#2e6b41')+txt(155,139,'TCP 질의: timeout',22,'#b3502f')+box(420,35,250,130,'#5a9e6f')+txt(545,68,'TCP 53 허용 정책 추가')+txt(545,105,'UDP 질의: 응답',22,'#2e6b41')+txt(545,139,'TCP 질의: 응답',22,'#2e6b41')+arrow(2,293,100,405,100)+txt(350,209,'같은 DNS 이름과 같은 서버를 프로토콜만 바꿔 조회했어요',22)+end(2,'DNS 허용 여부는 이름 조회 한 번의 성공만으로 판단하지 않아요.')
fig3=svg_start(3,280,'기존 TCP 연결의 established 처리와 새 SYN의 정책 검사 비교')+box(25,30,200,80)+txt(125,59,'정책 전 TCP 연결')+txt(125,88,'같은 source port 56494',18)+box(290,30,385,80,'#5a9e6f')+txt(482,60,'RELATED,ESTABLISHED → ACCEPT',21)+txt(482,89,'허용된 연결의 후속 패킷',20)+arrow(3,235,70,280,70)+box(25,145,200,80)+txt(125,177,'정책 후 새 연결')+txt(125,205,'새 TCP SYN',20)+box(290,145,385,80,'#e5533c','#fbeee7')+txt(482,177,'선택된 ingress 허용 규칙 없음',21)+txt(482,205,'새 요청 timeout',21,'#b3502f')+arrow(3,235,185,280,185)+txt(350,259,'이번 Calico 3.33 iptables 경로에서 관찰한 결과예요',22)+end(3,'HTTP 요청이 새로 생겨도 TCP 연결까지 새로 생기는 것은 아니에요.')
body='''
<p>서버로 들어오는 트래픽을 막았는데 HTTP 요청은 계속 200을 받았어요. 정책이 적용되지 않은 걸까요? 같은 시각에 새로 실행한 wget은 timeout으로 끝났어요. 성공한 쪽은 정책 전에 열어 둔 TCP 연결을 재사용했고, 실패한 쪽은 새 연결을 만들고 있었어요.</p>
<p>6편에서는 정책 하나로 요청이 막히는 모습을 봤어요. 이번에는 <b>어느 Pod의 어느 방향을 막았는지, 여러 허용 정책이 어떻게 합쳐지는지, 이미 열린 연결은 어떻게 되는지</b>를 각각 나눠 확인해요. Calico가 설치된 클러스터라도 표준 Kubernetes NetworkPolicy와 Calico 자체 정책은 구분해서 읽어야 해요.</p>
<p>실험은 Kubernetes v1.37.2, Calico v3.33.0인 Lima 클러스터의 전용 namespace <code>calico-blog-54</code>에서 했어요. worker1에 client-a·client-b, worker2에 nginx 서버를 배치했어요. 서버 IP는 <code>10.244.126.25</code>, client-a는 <code>10.244.194.81</code>였어요. 모두 개인 실습 주소예요.</p>
<p><b>이 글에서 다룰 것</b><br>· deny 정책을 추가했는데 allow 정책이 있으면 왜 통할까요?<br>· 서버 ingress만 열면 요청이 통할까요?<br>· Pod IP 요청은 되는데 DNS는 왜 실패할까요?<br>· 기존 연결과 새 연결은 어떻게 나눠 검증할까요?<br>· YAML이 노드의 어느 규칙으로 반영됐을까요?</p>
<h2>1. default deny는 선택한 Pod의 선택한 방향부터 바꾼다</h2>
<p>처음에는 이 namespace에 정책이 없었고 A·B 모두 서버에 요청할 수 있었어요. 서버만 선택하는 아래 정책을 추가했더니 두 클라이언트의 새 요청은 모두 실패했어요.</p>
'''+term('NetworkPolicy와 격리','Pod를 선택하고 그 Pod의 ingress 또는 egress에 허용할 통신을 정하는 Kubernetes 객체예요. 여기서 격리는 선택한 방향을 허용 목록으로 제한한다는 뜻이에요.')+code('''apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: deny-server-ingress
  namespace: calico-blog-54
spec:
  podSelector:
    matchLabels:
      role: server
  policyTypes: [Ingress]
  ingress: []''')+'''
<p><code>podSelector</code>는 같은 namespace의 <code>role: server</code> Pod를 골라요. <code>Ingress</code>만 적었으므로 서버로 들어오는 방향만 이번 정책의 대상이에요. namespace의 모든 Pod나 서버의 egress를 함께 막는 설정은 아니에요. 전체 Pod를 고르려면 <code>podSelector: {}</code>를 써야 해요.</p>
'''+term('ingress와 egress','판단 기준은 정책이 선택한 Pod예요. 그 Pod로 들어오는 통신은 ingress, 그 Pod에서 나가는 통신은 egress예요. 여기서 ingress는 Ingress HTTP 라우팅 리소스와 다른 뜻이에요.')+call('⚠️ 정책 객체가 생긴 시각과 적용 완료 시각은 달라요','kubectl apply 성공만 확인하고 곧바로 차단됐다고 단정하지 않아요. 이번에는 정책을 추가한 뒤 새 연결을 실제로 보내 결과를 확인했어요. 특정 적용 지연을 보장하는 실험은 아니에요.')+'''
<h2>2. 허용 정책은 순서대로 덮어쓰지 않고 합쳐진다</h2>
<p>deny 정책을 둔 채 서버의 TCP 80에 client-a를 허용하는 정책을 추가했어요. A는 성공했고 B는 여전히 실패했어요. 이어 B를 허용하는 정책을 하나 더 넣자 B도 성공했어요. 먼저 만든 deny가 모든 요청을 우선 차단하는 구조라면 나올 수 없는 결과예요.</p>
'''+term('선택자와 허용 목록의 합집합','선택자는 라벨 조건으로 Pod나 namespace를 고르는 설정이에요. 같은 Pod의 같은 방향에 적용되는 표준 NetworkPolicy의 허용 목록은 서로 합쳐져요. 정책 이름이나 생성 순서로 우선순위를 정하지 않아요.')+'''
<p>여기서 <code>ingress: []</code>는 다른 정책의 허용까지 무효로 하는 명시적 Deny 규칙이 아니에요. 그 정책 자체에는 허용 항목이 없다는 뜻이에요. 이 구분은 <a href="https://kubernetes.io/docs/concepts/services-networking/network-policies/#the-two-sorts-of-pod-isolation">Kubernetes의 격리·정책 합집합 설명</a>과 맞아요. 아래 결과는 매번 별도의 wget 프로세스로 새 연결을 만들어 확인했어요.</p>
'''+code('''적용 상태                         A → server    B → server
정책 없음                         성공          성공
deny-server-ingress                timeout       timeout
+ allow-a                         성공          timeout
+ allow-b                         성공          성공''')+call('💡 Calico 자체 정책과 구분해요','이 실험의 apiVersion은 networking.k8s.io/v1이에요. Calico 자체 정책의 order·Deny·tier를 이 합집합 설명에 섞지 않았어요. 이름이 NetworkPolicy로 같아도 API 그룹과 정책 모델을 먼저 확인해요.')+'''
<h2>3. 서버 ingress를 열어도 클라이언트 egress가 막히면 실패한다</h2>
<p>A와 B를 서버에서 허용한 다음 client-a의 egress를 빈 목록으로 제한했어요. 서버 ingress에는 A 허용이 남아 있었지만 A의 새 요청은 다시 timeout이 났어요. A의 egress에도 server Pod의 TCP 80을 허용하자 성공했어요.</p>
'''+fig1+'''
<p>확인할 것은 두 군데예요. 출발 Pod가 egress로 격리되어 있다면 그 허용 목록을 보고, 목적 Pod가 ingress로 격리되어 있다면 그 허용 목록도 봐요. 허용된 연결의 응답을 위해 반대 방향에 같은 신규 연결 허용 규칙을 기계적으로 복제하는 것과는 달라요.</p>
<p>실습에서 A의 egress를 열 때도 목적지를 Pod IP 숫자로 고정하지 않고 같은 namespace의 <code>role: server</code> 선택자로 골랐어요. IP는 재생성 때 바뀔 수 있지만 라벨 조건은 의도한 서버 Pod를 계속 선택할 수 있어요. 실제 선택 결과는 <code>kubectl get pod --show-labels</code>로 먼저 확인해야 해요.</p>
<h2>4. 서버로 가는 길과 DNS로 가는 길은 별개다</h2>
<p>이제 A에서 서버 Pod IP로 HTTP 요청은 성공해요. 하지만 A의 egress는 server TCP 80만 허용하므로 DNS 서버 <code>10.96.0.10:53</code>은 포함하지 않아요. 같은 A의 netns에서 <code>server-svc.calico-blog-54.svc.cluster.local</code>을 UDP와 TCP로 각각 직접 질의하자 둘 다 timeout이 났어요.</p>
'''+term('DNS의 UDP·TCP 질의','DNS는 UDP뿐 아니라 TCP로도 질의할 수 있어요. 이번에는 같은 이름을 같은 kube-dns Service IP에 두 프로토콜로 직접 질의했어요. UDP 응답의 자동 TCP 재시도를 재현한 실험은 아니에요.')+'''
<p>CoreDNS를 목적지로 하는 UDP 53 허용 정책을 더하자 UDP 응답은 돌아왔지만 TCP 질의는 계속 실패했어요. TCP 53 정책을 추가한 뒤에는 TCP도 응답했고, 마지막으로 A 안에서 Service DNS 이름을 사용하는 wget도 성공했어요. DNS를 고쳤다는 판단은 이 구간까지 확인한 결과예요.</p>
'''+fig2+code('''# a-dns-udp의 spec. TCP는 별도 정책에서 protocol만 TCP로 바꿨어요.
podSelector:
  matchLabels: {role: a}
policyTypes: [Egress]
egress:
  - to:
      - namespaceSelector:
          matchLabels:
            kubernetes.io/metadata.name: kube-system
        podSelector:
          matchLabels: {k8s-app: kube-dns}
    ports:
      - protocol: UDP
        port: 53''')+'''
<p><code>namespaceSelector</code>와 <code>podSelector</code>가 <b>같은 to 목록 항목</b>에 있어요. kube-system 안이면서 kube-dns 라벨을 가진 Pod라는 교집합이에요. 두 선택자를 별도의 목록 항목으로 나누면 허용 범위가 달라져요. 이 실험에서 관측한 Service DNAT와 정책 적용 결과를 NodeLocal DNSCache 등 다른 DNS 구성에 그대로 적용하지는 않아요.</p>
<p><img src="https://raw.githubusercontent.com/DDINGJOO/Platform-study/main/posts/CS/DevOps/k8s-study/images/calico-54/matrix.png" alt="실측 17개 검사 결과, ingress egress 분리와 DNS UDP TCP 허용 비교" style="max-width:100%"></p>
<p>위 이미지는 commands.json에 대응하는 결과 표본을 읽어 만든 텍스트를 렌더링한 화면이에요. 실패 검사의 exit 1·2는 의도한 차단을 확인한 결과이며 전체 실험의 실패를 뜻하지 않아요.</p>
<h2>5. HTTP 요청이 새로 생겨도 TCP 연결은 같을 수 있다</h2>
<p>가장 처음의 ingress deny 실험에서는 별도 클라이언트도 함께 실행했어요. 노드의 Python을 A의 네트워크 네임스페이스 안에서 실행하고 HTTPConnection 하나로 약 0.6초마다 요청했어요. 응답 본문을 끝까지 읽고 같은 객체를 재사용해요. 노드의 기본 네트워크에서 요청한 실험과 구분해야 해요.</p>
'''+term('HTTP keep-alive와 TCP 연결','HTTP 요청 여러 번을 같은 TCP 연결로 보낼 수 있어요. 이번에는 응답 코드만 세지 않고 매 요청의 소켓 출발지·목적지 주소와 포트를 기록해 TCP 연결 재사용도 확인했어요.')+'''
<p>첫 응답을 받은 다음 서버 ingress deny를 적용했어요. 그 뒤 새 wget은 timeout이 났지만 기존 연결에서는 총 12회의 요청이 모두 200이었어요. 12회 전체가 정책 적용 후 요청이라는 뜻은 아니에요. 첫 요청은 정책 전에 보냈고, 이후 정책 변경과 새 연결 차단을 확인하는 동안 같은 연결의 성공이 이어졌어요.</p>
<p>기록된 연결은 <code>10.244.194.81:56494 → 10.244.126.25:80</code>으로 같았어요. pcap에도 연결 시작의 SYN과 같은 연결의 HTTP 요청·응답이 남았어요. 요청마다 새 연결을 만들던 wget과 비교해야 정책 적용 실패라는 오진을 피할 수 있어요.</p>
'''+fig3+'''
<p><img src="https://raw.githubusercontent.com/DDINGJOO/Platform-study/main/posts/CS/DevOps/k8s-study/images/calico-54/keepalive.png" alt="같은 TCP 출발 포트 56494에서 12회 HTTP 200, 정책 후 새 연결 A B는 차단된 실측" style="max-width:100%"></p>
<p>수집된 JSONL을 읽어 소켓 정보와 클라이언트 내부 경과 시간을 표시한 화면이에요. Mac의 명령 시작 시각과 VM의 요청 시각은 서로 다른 시계이므로 두 값의 밀리초 차이로 정책 적용 시간을 계산하지 않았어요.</p>
<h2>6. YAML 다음에는 커널 규칙과 새 연결을 확인한다</h2>
'''+term('conntrack','리눅스 커널이 연결의 주소·포트·프로토콜과 상태를 추적하는 기능이에요. TCP의 NEW와 ESTABLISHED 등을 구분해 후속 패킷을 처리할 수 있어요. HTTP 상태 코드와는 다른 계층의 상태예요.')+'''
<p>실험 마지막 단계의 worker2 규칙을 저장해 서버의 cali 인터페이스에 대응하는 체인을 찾았어요. 그 체인의 앞부분에는 <code>RELATED,ESTABLISHED</code>를 ACCEPT하는 규칙이 있고 그 뒤에 정책 체인으로 가는 규칙이 있었어요. 마지막 단계에 수집한 규칙이므로 그 카운터 숫자를 ingress deny 순간의 수치로 읽지는 않아요.</p>
'''+code('''# iptables-save -c의 서버 endpoint 체인에서 관련 부분 발췌
-m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
-m conntrack --ctstate INVALID -j DROP
...
-m comment --comment "Start of tier default" ...
...
-m comment --comment "End of tier default. Drop if no policies passed packet" ... -j DROP''')+'''
<p><a href="https://github.com/projectcalico/calico/blob/v3.33.0/felix/rules/endpoints.go">Calico v3.33.0의 appendConntrackRules</a>에서도 연결 상태 허용 규칙을 만드는 코드를 확인했어요. <a href="https://docs.tigera.io/calico/latest/reference/architecture/overview#felix">정책이 커널 규칙으로 반영되는 과정은 Felix가 담당</a>하고, 이후 패킷 처리는 커널이 수행해요. <code>iptables v1.8.10 (nf_tables)</code>라는 도구 출력만으로 Calico의 native nftables 데이터플레인을 사용한다고 결론 내리면 안 돼요.</p>
<p><a href="https://docs.tigera.io/calico/latest/network-policy/get-started/calico-policy/calico-network-policy#create-policy-for-established-connections">Calico의 기존 연결 설명</a>은 열린 연결과 새 연결을 구분해요. <a href="https://kubernetes.io/docs/concepts/services-networking/network-policies/#networkpolicy-s-impact-on-existing-connections">Kubernetes 문서</a>는 정책 변경이 기존 연결에 미치는 효과를 구현에 맡겨요. 따라서 이 실험의 유지 동작을 모든 CNI·Calico 모드의 보장으로 쓰지는 않아요.</p>
'''+call('💡 정책 검증 순서','대상 Pod·라벨 → ingress/egress → 각 방향의 허용 정책 전체 → DNS 목적지·프로토콜 → 새 TCP 연결 순으로 확인해요. 기존 세션도 함께 관찰하되 새 연결 결과와 별도로 적어요. 공유 노드의 conntrack 전체 삭제는 검증 절차에 넣지 않았어요.')+'''
<p>전용 namespace의 17개 검사와 같은 연결의 12개 응답을 원문으로 남겼어요. 재현 스크립트·정책 JSON·명령 기록·pcap·규칙 발췌는 <a href="https://github.com/DDINGJOO/Platform-study/tree/main/labs/devops/k8s-study/calico-51-56/54">54편 실험 자료</a>에 있어요. 끝에는 생성한 namespace를 삭제하고 NotFound를 확인했으며 노드 4대도 Ready였어요. 기존 워크로드의 정책이나 전역 규칙은 수정하지 않았어요.</p>
<div class="obsv-summary"><div class="obsv-st2">✍️ 오늘의 요약</div><b>정책을 읽을 때는 Pod 선택 범위·방향·허용 목록과 연결 상태를 함께 봐요.</b><br><br>표준 NetworkPolicy의 허용 정책은 합쳐지고, 격리된 발신 egress와 수신 ingress가 모두 허용해야 새 연결이 통해요. 이번 Calico 3.33 실험에서는 정책 전의 TCP 연결이 유지되는 동안 새 연결은 차단됐어요. HTTP 요청 횟수와 TCP 연결 횟수를 분리해야 정책을 정확히 검증할 수 있어요.</div>
'''
head='<!-- tags: NetworkPolicy, default deny, conntrack, keep-alive, DNS 정책 -->\n<!-- lead: 서버 ingress를 막았는데 기존 HTTP 연결에서는 200이 이어지고 새 연결은 timeout이 났어요. Calico에서 허용 정책의 합집합, ingress·egress, DNS UDP·TCP와 연결 상태를 나누어 직접 검증했어요. -->\n'
(root/entry['file']).write_text(head+style+'\n<div class="obsv-wrap">\n'+series+body+'\n</div>\n')
print(root/entry['file'])
