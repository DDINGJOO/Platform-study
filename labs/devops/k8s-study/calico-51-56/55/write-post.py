from pathlib import Path
import re,json
ROOT=Path('/Users/dding/orca/workspaces/Platform-study/k8s-study')
D=ROOT/'labs/devops/k8s-study/calico-51-56'
row=next(x for x in json.loads((D/'manifest.json').read_text()) if x['number']==55)
style=re.search(r'<style>.*?</style>',(ROOT/'.claude/skills/tistory-sketch-post/assets/template.html').read_text(),re.S).group()
series=(D/'series.html').read_text().replace('{number}','55')
line=f"  55편. {row['title']}<br>"
series=series.replace(line,f"  <b>55편. {row['title']}</b> &larr; 지금 이 글<br>")

def box(x,y,w,h,color='#4a7fb5',fill='#fffdf7'):
 return f'<path d="M{x} {y} C{x+w*.33} {y-2},{x+w*.67} {y+2},{x+w} {y} C{x+w+2} {y+h*.33},{x+w-2} {y+h*.67},{x+w} {y+h} C{x+w*.67} {y+h+2},{x+w*.33} {y+h-2},{x} {y+h} C{x-2} {y+h*.67},{x+2} {y+h*.33},{x} {y} Z" fill="{fill}" stroke="{color}" stroke-width="2.2"/>'
def label(x,y,t,size=22,color='#3d3a34',mono=False):
 font='Menlo,monospace' if mono else "'Nanum Pen Script',cursive"
 return f'<text x="{x}" y="{y}" text-anchor="middle" font-family="{font}" font-size="{size}" fill="{color}">{t}</text>'
def arrow(x1,y1,x2,y2,mid):
 return f'<path d="M{x1} {y1} C{(x1+x2)/2} {y1-2},{(x1+x2)/2} {y2+2},{x2} {y2}" fill="none" stroke="#3d3a34" stroke-width="2" marker-end="url(#{mid})"/>'
def svg(n,h,inner,caption):
 inner=re.sub(r'\d+\.\d{4,}',lambda m:f'{float(m.group()):.2f}',inner)
 mid=f'cb55-a{n}'
 defs=f'<defs><marker id="{mid}" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M1 1.5 C4 3,6 4,8.5 5 C6 6,4 7,1 8.5" fill="none" stroke="#3d3a34" stroke-width="1.6"/></marker></defs>'
 return f'<div class="obsv-fig"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 {h}" role="img" aria-label="{caption}" style="width:100%;max-width:700px;height:auto;">{defs}{inner}</svg></div><div class="obsv-figcap">그림 {n}. {caption}</div>'
fig1=svg(1,270,
 box(25,45,205,120)+label(127,77,'일반 Pod의 패킷')+label(127,106,'10.244.194.92',14,mono=True)+label(127,133,'출발 포트 45555',18)+
 box(265,45,170,120,'#e5a33c','#fdf3dd')+label(350,78,'worker1 커널')+label(350,108,'POSTROUTING',13,mono=True)+label(350,137,'MASQUERADE',13,mono=True)+
 box(470,45,205,120,'#5a9e6f')+label(572,77,'수신기가 본 패킷')+label(572,106,'192.168.104.3',14,mono=True)+label(572,133,'출발 포트 7165',18)+arrow(231,105,263,105,'cb55-a1')+arrow(437,105,468,105,'cb55-a1')+
 label(350,210,'목적지는 모든 지점에서 192.168.104.4:18555',20)+label(350,245,'이번 연결에서는 출발지 IP와 포트가 함께 바뀌었어요',23,'#b3502f'),
 'cali와 eth0의 같은 TCP 연결을 대조해 SNAT 구간을 찾았어요')
fig2=svg(2,330,
 box(35,43,630,105)+label(350,76,'original: 처음 연결을 시작한 방향')+label(350,113,'10.244.194.92:45555 → 192.168.104.4:18555',15,mono=True)+
 box(35,172,630,105,'#5a9e6f')+label(350,205,'reply: 변환 후 응답을 받는 방향')+label(350,242,'192.168.104.4:18555 → 192.168.104.3:7165',15,mono=True)+
 arrow(350,149,350,169,'cb55-a2')+label(350,312,'커널이 두 방향의 대응을 보관해 응답 목적지를 되돌려요',23,'#b3502f'),
 'conntrack의 reply 목적지는 NAT 전 Pod 주소와 달라요')
fig3=svg(3,270,
 box(25,62,190,100)+label(120,95,'Pod 네트워크')+label(120,128,'10.244.0.0/16',13,mono=True)+
 box(255,62,190,100,'#5a9e6f')+label(350,95,'VM 노드 네트워크')+label(350,128,'192.168.104.0/24',12,mono=True)+
 box(485,62,190,100,'#8a8272')+label(580,95,'Mac · 상위망')+label(580,128,'공인 인터넷',20)+arrow(217,112,252,112,'cb55-a3')+arrow(447,112,482,112,'cb55-a3')+
 label(235,39,'이번 실험에서 확인한 SNAT',23,'#2e6b41')+label(350,212,'수신기는 worker2의 호스트 주소에 두었어요',22)+label(350,247,'상위 NAT와 공인 출발지 IP는 이 실험의 관측 범위 밖이에요',21,'#b3502f'),
 'Pod 대역 밖의 수신기로 Calico NAT를 검증했고 인터넷 NAT와 구분했어요')
content='''
<p>Pod에서 출발 포트를 45555로 지정해 요청했는데 수신기에는 <b>192.168.104.3:7165</b>가 찍혔어요. 같은 노드의 hostNetwork Pod와 노드 셸에서 보낸 요청은 지정한 포트 45556과 45557을 그대로 유지했어요. HTTP 응답은 세 요청 모두 정상이었지만 출발지 주소가 같아진 과정은 달랐어요.</p>
<p>수신기는 인터넷 서버가 아니라 worker2의 호스트 주소 <code>192.168.104.4:18555</code>에 띄운 임시 HTTP 서버예요. <b>클러스터의 노드라도 Calico Pod 풀 밖이면 NAT 조건에 들어갈 수 있어요.</b> 이번에는 worker1의 cali 장치, eth0, worker2의 eth0, 연결 추적 정보를 함께 읽어 변환 위치와 응답 경로를 확인해요.</p>
<p>실험 환경은 Kubernetes v1.37.2, Calico v3.33.0, Linux 6.8이에요. 기존 정책이나 NAT 설정은 바꾸지 않았고 전용 namespace의 Pod 두 개와 제한 시간 있는 수신기만 만들었어요. 일반 Pod의 IP는 10.244.194.92, worker1은 192.168.104.3, worker2는 192.168.104.4였어요.</p>

<h2>1. 목적지가 노드여도 Pod 풀 밖일 수 있다</h2>
<p>Pod에서 밖으로 나간다는 말부터 범위를 정해야 해요. 이 클러스터의 IPPool은 <code>10.244.0.0/16</code> 하나이고 <code>natOutgoing: true</code>예요. 수신기의 192.168.104.4는 여기에 속하지 않아요. 반면 같은 풀의 다른 Pod로 보내는 통신은 목적지가 풀 안에 있어요.</p>
<div class="obsv-term"><div class="obsv-tt">📖 용어: SNAT</div>패킷의 출발지 주소를 바꾸는 변환이에요. 이 실험에서는 Pod IP가 worker1의 노드 IP로 바뀌었고 출발지 포트도 함께 바뀌었어요.</div>
<p>Calico의 <a href="https://docs.tigera.io/calico/latest/networking/configuring/workloads-outside-cluster">outgoing NAT 문서</a>는 목적지가 모든 Calico IP 풀 밖인지로 조건을 설명해요. 단순히 “다른 노드면 NAT”, “인터넷이면 NAT”로 판별하면 이 실험을 설명할 수 없어요. 별도의 NAT 제외 풀이나 호스트 주소 제외 설정을 사용하면 조건이 달라질 수 있으므로 실제 규칙도 읽어야 해요.</p>
<div class="obsv-code">kubectl get ippool default-ipv4-ippool -o yaml
# 이번 spec: cidr=10.244.0.0/16, natOutgoing=true

# 전용 Pod에서 목적지를 고정하고 프록시 사용을 끈 요청
kubectl -n calico-blog-55 exec pod-client -- curl \\
  --noproxy '*' --local-port 45555 --max-time 5 -sS \\
  http://192.168.104.4:18555/pod</div>
<p>첫 명령은 NAT 여부를 결정할 풀 설정을, 두 번째 명령은 수신기가 본 원격 주소를 보여줘요. Pod 이름·주소·포트는 전용 실습 값이에요. <code>--local-port</code>는 애플리케이션이 쓰는 출발 포트를 정하지만 이후 NAT에서 포트가 유지된다고 보장하지 않아요.</p>
<div class="obsv-callout"><div class="obsv-ct">💡 실무에서는</div>같은 노드에서 일반 Pod·hostNetwork Pod·노드 셸 요청을 비교하면 애플리케이션이 보는 주소와 네트워크 경로를 분리할 수 있어요. hostNetwork Pod는 노드의 네트워크 네임스페이스를 공유하므로 일반 Pod의 IP를 출발지로 쓰지 않아요.</div>

<h2>2. natOutgoing은 커널의 MASQUERADE 규칙으로 이어졌다</h2>
<p>설정이 true라는 사실만으로 실제 연결이 어느 규칙을 지났다고 말할 수는 없어요. worker1에서 <code>sudo iptables-save -t nat</code>로 확인하니 POSTROUTING에서 <code>cali-POSTROUTING</code>으로 들어가고 그 안에서 <code>cali-nat-outgoing</code>을 호출했어요. 마지막 조건과 동작은 다음 한 줄이었어요. 읽기 편하게 식별용 주석만 뺐어요.</p>
<div class="obsv-code">-A cali-nat-outgoing \\
  -m set --match-set cali40masq-ipam-pools src \\
  -m set ! --match-set cali40network-ip-pools dst \\
  -j MASQUERADE --random-fully</div>
<p>출발지가 NAT 대상 풀에 속하고 목적지가 네트워크 풀 집합에 속하지 않을 때 MASQUERADE를 적용해요. 설치 버전의 <a href="https://github.com/projectcalico/calico/blob/v3.33.0/felix/rules/nat.go">Felix 규칙 생성 코드</a>도 두 집합 조건을 조합하고 NAT outgoing 체인을 만들어요. 이 환경의 iptables는 nf_tables 백엔드를 사용했어요. 다른 백엔드·eBPF 모드까지 동일한 규칙 모양이라고 일반화하지 않아요.</p>
<div class="obsv-term"><div class="obsv-tt">📖 용어: MASQUERADE</div>송신 인터페이스의 주소를 이용하는 SNAT 동작이에요. 고정 주소를 지정하는 SNAT 규칙과 구분하며, 여기서는 eth0으로 나가면서 출발지가 192.168.104.3으로 바뀌었어요.</div>
<p>이 체인의 매칭 패킷 카운터는 세 요청 전 <b>22</b>에서 뒤 <b>23</b>으로 늘었어요. 이것만으로 어떤 연결이 원인이었는지 확정하지는 않아요. 공유 노드의 다른 요청도 카운터에 포함될 수 있기 때문이에요. 다음 절의 패킷과 연결 추적을 함께 대조했어요.</p>
<div class="obsv-callout"><div class="obsv-ct">⚠️ 주의: NAT 카운터는 전체 전송량이 아니에요</div><a href="https://www.netfilter.org/documentation/HOWTO/NAT-HOWTO-5.html">Netfilter NAT 문서</a>가 설명하듯, 연결 추적을 사용하는 NAT 규칙은 새 연결의 첫 패킷에서 변환을 결정해요. 그 뒤 패킷에는 저장한 대응이 적용되므로 HTTP 응답에 패킷이 여러 개 있어도 NAT 규칙 카운터가 그만큼 늘어야 하는 것은 아니에요.</div>

<h2>3. cali와 eth0에서 같은 연결의 출발지가 달라졌다</h2>
<p>일반 Pod로 가는 호스트 경로에서 <code>cali31e758d2ea8</code>을 찾았어요. 이 장치와 worker1의 eth0, worker2의 eth0에서 <code>tcp and host 192.168.104.4 and port 18555</code> 필터로 동시에 캡처했어요. 각각 16초 제한을 걸고 원본 pcap을 남겼어요.</p>
<p>cali의 첫 SYN은 <b>10.244.194.92:45555 → 192.168.104.4:18555</b>였어요. worker1의 eth0에서는 <b>192.168.104.3:7165 → 192.168.104.4:18555</b>였고 worker2도 같은 변환된 주소를 받았어요. 두 SYN의 TCP 초기 시퀀스 번호는 345155042로 같았고 TCP 타임스탬프도 같았어요. 포트가 바뀌었어도 같은 연결의 패킷임을 대조할 수 있었어요.</p>
<div class="obsv-term"><div class="obsv-tt">📖 용어: 5-tuple</div>출발지 IP·포트, 목적지 IP·포트, 전송 프로토콜을 묶은 연결 식별 정보예요. NAT 전후에는 일부 값이 달라지므로 캡처를 비교할 때 TCP 시퀀스와 시각도 같이 확인했어요.</div>
FIG1
<p>수신기의 HTTP 응답과 서버 로그에도 일반 Pod 요청의 원격 포트는 7165로 남았어요. <a href="https://man7.org/linux/man-pages/man8/iptables-extensions.8.html">iptables 확장 매뉴얼</a>에서 <code>--random-fully</code>는 출발지 포트 매핑을 무작위화하는 옵션이에요. 7165는 이 규칙이 적용된 이번 연결의 관측값이며 다음 실행에서도 7165를 쓴다는 뜻은 아니에요. hostNetwork Pod 요청과 노드 요청은 각각 <code>192.168.104.3:45556</code>, <code>192.168.104.3:45557</code>로 보였어요.</p>
<p><img src="https://raw.githubusercontent.com/DDINGJOO/Platform-study/main/posts/CS/DevOps/k8s-study/images/calico-55/receiver.png" alt="수신기 원문 출력: 일반 Pod 요청의 원격 포트 7165, hostNetwork 45556, 노드 45557" style="max-width:100%"></p>
<p>위 화면은 세 요청의 저장된 응답 원문을 모아 렌더링한 캡처예요. 터미널을 직접 촬영한 화면은 아니며 실행 시각·명령·서버 로그는 별도 실습 자료에 보관했어요.</p>
<p>52편의 다른 노드 Pod 통신과도 달라요. 목적지 192.168.104.4로의 호스트 경로는 eth0의 직접 경로였어요. IPIP Always라는 풀 설정이 모든 목적지의 패킷을 무조건 tunl0으로 보낸다는 뜻은 아니에요.</p>

<h2>4. 응답이 원래 Pod로 돌아오는 정보는 conntrack에 있었다</h2>
<p>수신기가 본 클라이언트는 노드 주소예요. 그렇다면 응답은 어떤 Pod로 보내야 할까요? worker1의 연결 추적 정보를 읽으니 일반 Pod 요청에 NAT 전 original과 NAT 후 reply가 함께 남아 있었어요.</p>
<div class="obsv-term"><div class="obsv-tt">📖 용어: conntrack</div>리눅스 커널이 연결의 두 방향과 상태를 추적하는 기능이에요. NAT와 함께 쓰이면 변환 전후의 대응을 보관하고 응답에 반대 변환을 적용할 수 있어요.</div>
<div class="obsv-code">original  10.244.194.92:45555 → 192.168.104.4:18555
reply     192.168.104.4:18555 → 192.168.104.3:7165
src_nat   true

hostNetwork: src_nat=false, 원래 포트 45556
node:        src_nat=false, 원래 포트 45557</div>
<p>위는 원문 JSON의 주소·포트를 한 줄씩 정리한 결과예요. <b>reply는 NAT 전 original의 주소를 단순히 뒤집은 값이 아니에요.</b> 수신기에서 돌아오는 패킷의 목적지는 192.168.104.3:7165예요. 커널이 연결을 찾아 목적지를 10.244.194.92:45555로 되돌린 뒤 Pod 방향으로 전달해요. 실제 cali 캡처에서도 SYN-ACK의 목적지는 원래 Pod 주소·포트였어요.</p>
FIG2
<p>이번 노드에는 conntrack CLI와 <code>/proc/net/nf_conntrack</code>이 없었어요. 패키지를 설치하는 대신 Python 표준 라이브러리로 <a href="https://docs.kernel.org/netlink/specs/conntrack.html">커널의 nfnetlink conntrack 조회 인터페이스</a>에 읽기 전용 dump를 요청했어요. 다른 연결 내용은 저장하지 않고 목적지 포트 18555인 TCP 연결만 출력했어요. 설치된 환경에서는 <code>sudo conntrack -L -p tcp --dport 18555</code>로 같은 종류의 정보를 볼 수 있어요.</p>
<p><img src="https://raw.githubusercontent.com/DDINGJOO/Platform-study/main/posts/CS/DevOps/k8s-study/images/calico-55/conntrack.png" alt="읽기 전용 nfnetlink 조회 원문 중 일반 Pod 연결: original/reply 주소와 src_nat true" style="max-width:100%"></p>
<p>이 화면도 저장된 조회 JSON에서 일반 Pod 연결 부분을 골라 렌더링했어요. 응답을 받은 뒤 조회한 결과라 TCP 연결이 이미 종료 중인 표본일 수 있어요. 이 표본만으로 연결 유지 시간이나 모든 TCP 상태 전이를 추론하지 않아요.</p>

<h2>5. 인터넷에서 보이는 주소와 Calico가 바꾼 주소를 구분한다</h2>
<p>이번에 수신기를 worker2의 호스트 네트워크에 둔 이유는 관측 경계를 좁히기 위해서예요. Calico 풀 밖의 주소에 요청하면서도 송신 노드와 수신기의 캡처를 모두 확보할 수 있었어요. 인터넷 전체의 경로·공인 NAT 동작을 재현한 실험은 아니에요.</p>
FIG3
<p>공인 IP 조회 서비스에서 주소 하나를 받으면 그 값은 최종 수신자가 본 출발지예요. 중간에 Lima·Mac·공유기·클라우드 NAT가 있으면 노드에서 이미 변환된 주소가 다시 바뀔 수 있어요. 따라서 그 출력 하나로 “Calico가 이 공인 IP로 바꿨다”고 결론 내리지 않아요.</p>
<div class="obsv-callout"><div class="obsv-ct">💡 실무에서는 이 순서로 대조해요</div>목적지 주소와 포트를 고정하고 Pod의 IP·경로, 실제 IPPool, NAT 조건과 카운터, 노드 송신 인터페이스의 패킷, 수신기의 원격 주소, conntrack의 original/reply를 차례로 확인해요. 주소 변경이 일어난 두 관측 지점 사이부터 조사하면 돼요.</div>
<p>NAT를 끄면 Pod 주소가 보존될 수 있지만 외부 수신기에서 그 Pod 대역으로 돌아오는 경로와 정책도 필요해요. 이 부분은 <a href="https://docs.tigera.io/calico/latest/reference/resources/ippool">IPPool 설정 문서</a>와 앞서 본 outgoing NAT 문서의 조건이에요. 이번에는 기존 풀을 바꾸지 않았으므로 NAT 비활성화 비교를 실험했다고 쓰지 않아요.</p>
<p>재현 스크립트와 매니페스트, 세 지점의 pcap, 조회 원문은 <a href="https://github.com/DDINGJOO/Platform-study/tree/main/labs/devops/k8s-study/calico-51-56/55">55편 실습 자료</a>에 함께 두었어요. 수집기는 저장소 경로의 lab 래퍼를 사용하므로 다른 환경에서는 경로와 노드 이름을 바꿔야 해요. 실행 후 전용 namespace가 사라지고 worker2의 18555 리스너가 닫힌 것도 확인했어요.</p>
<div class="obsv-summary"><div class="obsv-st2">✍️ 오늘의 요약</div><b>이번 구성에서는 Pod 풀 밖의 worker2 호스트로 보낸 일반 Pod 요청이 worker1에서 SNAT됐어요.</b><br><br>cali의 10.244.194.92:45555와 eth0의 192.168.104.3:7165를 같은 TCP 연결로 대조했고 conntrack에서 응답의 대응도 확인했어요. NAT를 설명할 때는 풀 설정, 실제 패킷, 연결 추적, 수신기의 관측 범위를 함께 읽어야 해요.</div>
'''
for key,fig in [('FIG1',fig1),('FIG2',fig2),('FIG3',fig3)]:content=content.replace(key,fig)
post='<!-- tags: SNAT, MASQUERADE, natOutgoing, conntrack, 파드 외부 통신 -->\n<!-- lead: Pod에서 출발 포트를 45555로 지정했는데 수신기는 노드 IP의 7165로 받았어요. Calico 풀 밖의 수신기를 두고 cali·eth0 패킷과 conntrack을 대조해 SNAT 위치와 응답 경로를 확인했어요. -->\n'+style+'\n<div class="obsv-wrap">\n'+series+content+'\n</div>\n'
(ROOT/row['file']).write_text(post)
print(ROOT/row['file'])
