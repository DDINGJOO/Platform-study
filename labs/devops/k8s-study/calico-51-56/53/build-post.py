#!/usr/bin/env python3
from pathlib import Path
import json, re

ROOT=Path('/Users/dding/orca/workspaces/Platform-study/k8s-study')
HERE=Path(__file__).resolve().parent
style=re.search(r'<style>.*?</style>',Path('/Users/dding/orca/Platform-study/.claude/skills/tistory-sketch-post/assets/template.html').read_text(),re.S).group()
series=(HERE.parent/'series.html').read_text().replace('{number}','53')
manifest=json.loads((HERE.parent/'manifest.json').read_text())
entry=next(x for x in manifest if x['number']==53)
line=f"53편. {entry['title']}"
series=series.replace('  '+line+'<br>','  <b>'+line+'</b> &larr; 지금 이 글<br>')
body=r'''
<p>다른 노드의 파드에 ping을 보냈어요. 데이터 크기를 1452바이트로 주면 두 번 모두 응답했는데, 1453바이트로 바꾸자 <code>message too long, mtu=1480</code>이 나왔어요. 한 바이트 차이였어요. 그런데 이 실패는 상대 노드에서 패킷을 버린 결과가 아니었어요. 출발지 커널이 전송을 거절했어요.</p>
<p>이번에는 별도 경로를 만들었어요. 작은 ping과 TCP 연결은 통과했지만 64KiB 업로드는 4초 뒤에 시간 초과가 났어요. 중간 경로의 MTU는 그대로 두고 ICMP 오류 메시지만 허용하자 같은 업로드가 완료됐어요. 두 실패를 함께 보면 <b>로컬 MTU를 넘긴 경우와 중간 경로의 MTU를 알지 못하는 경우</b>를 구분할 수 있어요.</p>
<p>실측 환경은 Lima VM 4대, Kubernetes v1.37.2, Calico v3.33.0, Linux 6.8.0-147이에요. Calico는 IPv4 IPIP Always 구성이에요. 먼저 실제 파드의 정상 경계를 측정하고, 장애 재현은 기존 Calico 설정을 바꾸지 않은 격리 네트워크에서 진행했어요.</p>

<p><b>이 글에서 다룰 것</b><br>
&middot; 노드 NIC는 1500인데 파드 eth0는 왜 1480일까?<br>
&middot; ping의 1452와 화면에 보이는 1460·1480은 무엇이 다를까?<br>
&middot; TCP 연결에 성공했는데 업로드만 멈출 수 있을까?<br>
&middot; ICMP 피드백을 받으면 패킷과 커널 경로에 무엇이 달라질까?</p>

<h2>1. 노드 NIC의 1500에서 IPIP 헤더 20바이트를 뺀다</h2>
<p>51·52편에서 확인한 파드 eth0, 호스트의 cali 장치, tunl0와 실제 송신 NIC를 이번에는 크기 기준으로 봤어요. worker1의 노드 NIC eth0는 MTU 1500, tunl0와 임시 파드의 eth0는 1480이었어요.</p>
<div class="obsv-term"><div class="obsv-tt">📖 용어: MTU</div>인터페이스가 한 번에 내보낼 수 있는 IP 패킷의 최대 크기예요. 이 글의 Ethernet MTU 1500은 IP 헤더와 그 안의 데이터를 합친 크기이며 Ethernet 헤더까지 포함한 프레임 전체 크기가 아니에요.</div>
<p>IPIP는 원래 IP 패킷 바깥에 IPv4 헤더를 하나 더 붙여요. 옵션이 없는 바깥 IPv4 헤더는 20바이트이므로 내부 IP 패킷이 1480이면 바깥 IP 패킷은 1500이 돼요. 이 관계는 <a href="https://docs.tigera.io/calico/latest/networking/configuring/mtu">Calico 3.33의 MTU 표</a>와도 맞아요. 같은 문서에서 IPv4 VXLAN은 추가 크기가 50바이트예요. 캡슐화 종류가 바뀌면 계산도 바뀌어요.</p>
<div class="obsv-fig"><svg viewBox="0 0 700 236" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:700px;height:auto;" role="img" aria-label="ping 데이터 1452와 ICMP 헤더 8, 내부 IPv4 헤더 20, 외부 IPv4 헤더 20을 합친 1500바이트">
<path d="M30 65 C160 62 530 67 668 64 L669 144 C500 147 180 142 29 145 Z" fill="#fffdf7" stroke="#3d3a34" stroke-width="2.4" stroke-linejoin="round"/>
<path d="M31 65 C58 63 85 66 110 65 L111 144 L30 145 Z" fill="#fdf3dd" stroke="#e5a33c" stroke-width="2"/>
<path d="M111 65 C142 63 166 66 190 65 L192 144 L112 145 Z" fill="#f1f5fa" stroke="#4a7fb5" stroke-width="2"/>
<path d="M192 65 C219 63 240 66 266 65 L267 144 L193 145 Z" fill="#fbeee7" stroke="#b3502f" stroke-width="2"/>
<g font-family="'Nanum Pen Script',cursive" font-size="22" fill="#3d3a34" text-anchor="middle"><text x="350" y="32">IPv4 IPIP, IP 옵션 없는 ping의 크기 계산</text><text x="70" y="94">바깥 IP</text><text x="70" y="124">20</text><text x="151" y="94">안쪽 IP</text><text x="151" y="124">20</text><text x="229" y="94">ICMP</text><text x="229" y="124">8</text><text x="462" y="109">ping 데이터 1452</text><text x="390" y="178" fill="#3d6591">내부 IP 패킷 = 1480</text><text x="350" y="216" fill="#b3502f">바깥 IP 패킷 = 1500, Ethernet 헤더는 이 계산 밖이에요.</text></g>
</svg></div>
<p class="obsv-figcap">그림 1. ping의 데이터 크기와 인터페이스의 MTU는 같은 숫자를 뜻하지 않아요.</p>
<p>다만 NIC 출력이 1500이라는 사실만으로 경로 전체가 1500을 지원한다고 보장할 수는 없어요. 중간 네트워크에 더 작은 구간이 있을 수 있어요. 이번 두 파드 사이에서는 내부 1480바이트 ping의 왕복을 직접 확인했어요.</p>

<h2>2. 1453바이트 ping은 출발지에서 거절됐다</h2>
<p>worker1과 worker2에 임시 pause 파드를 하나씩 만들었어요. worker1에서 컨테이너 PID를 찾고 <code>nsenter -t "$PID" -n</code>으로 그 파드의 네트워크 네임스페이스에 들어가 노드의 iputils ping을 실행했어요. 이미지 안에 ping을 설치하지 않아도 파드와 같은 네트워크에서 측정할 수 있어요. PID는 컨테이너 재생성 후 다시 찾아야 해요.</p>
<div class="obsv-code"># worker1에서 실행. PID와 DEST는 이번에 만든 파드에서 조회한 값
sudo nsenter -t "$PID" -n ping -4 -n -c 2 -W 1 -M do -s 1452 "$DEST"
sudo nsenter -t "$PID" -n ping -4 -n -c 2 -W 1 -M do -s 1453 "$DEST"

# 1452: 2 packets transmitted, 2 received, 0% packet loss
# 1453: ping: local error: message too long, mtu=1480</div>
<p>첫 명령은 왕복에 성공했고, 두 번째의 <code>local error</code>는 출발지 커널이 패킷 크기를 허용하지 않았다는 뜻이에요. 상대 노드의 정책이나 BGP 상태부터 의심할 실패는 아니었어요.</p>
<div class="obsv-term"><div class="obsv-tt">📖 용어: DF와 ping -M do</div>DF는 IPv4 패킷을 중간에서 조각내지 말라는 플래그예요. iputils의 <code>-M do</code>는 DF를 설정하면서 커널의 경로 MTU 검사도 받아요. 따라서 이미 알려진 한도를 넘기면 전송 전에 거절될 수 있어요. 세부 옵션은 <a href="https://man7.org/linux/man-pages/man8/ping.8.html">ping 매뉴얼</a>에서 확인할 수 있어요.</div>
<p><code>-s</code>는 ICMP 데이터 크기예요. IPv4 옵션이 없을 때 1452 + ICMP 헤더 8 + IPv4 헤더 20 = 1480이에요. 성공 응답 줄의 <code>1460 bytes</code>는 ICMP 헤더와 데이터를 합한 크기예요. 화면의 세 숫자를 모두 MTU라고 읽으면 8바이트나 28바이트씩 계산이 어긋나요.</p>
<p><img src="https://raw.githubusercontent.com/DDINGJOO/Platform-study/main/posts/CS/DevOps/k8s-study/images/calico-53/mtu-boundary.png" alt="실제 Calico 파드에서 ping 데이터 1452는 두 번 응답하고 1453은 local message too long mtu 1480으로 실패한 저장 출력" style="max-width:100%"></p>
<p class="obsv-figcap">실행 기록 1. 저장된 두 명령 출력을 이미지로 만들었어요. 대상 Pod IP만 자리표시자로 바꿨어요.</p>
<div class="obsv-callout"><div class="obsv-ct">⚠️ 이 결과로 모든 MTU 장애를 설명할 수는 없어요</div>현재 tunl0에는 <code>nopmtudisc</code>가 표시됐어요. 내부 ping의 DF와 터널 바깥 패킷의 DF를 같은 것으로 취급하면 안 돼요. 이번 정상 경계 측정은 출발지 한도와 왕복 성공을 확인한 것이며, Calico 터널 아래에 MTU 장애를 넣어 바깥 단편화 동작까지 검증한 실험은 아니에요.</div>

<h2>3. 출발지는 1500인데 중간 경로만 1300이면 어떻게 될까</h2>
<p>로컬에서 거절되지 않는 실패를 보려면 출발 인터페이스보다 작은 중간 구간이 필요해요. worker1 안에 <code>cb53-src</code>, <code>cb53-rtr</code>, <code>cb53-dst</code>라는 Linux 네트워크 네임스페이스를 새로 만들고 veth 두 쌍으로 연결했어요. 클러스터 밖으로 연결되지 않는 전용 경로예요.</p>
<div class="obsv-term"><div class="obsv-tt">📖 용어: PMTUD</div>Path MTU Discovery는 경로를 지나갈 수 있는 패킷 크기를 알아내는 과정이에요. IPv4의 전통적인 방식에서는 DF 패킷을 전달하지 못한 라우터가 ICMP 오류와 다음 구간의 MTU를 알려 줘요. <a href="https://www.rfc-editor.org/rfc/rfc1191">RFC 1191</a>은 이 피드백에 따라 송신 크기를 줄이는 방법을 정의해요.</div>
<p>양 끝 인터페이스는 MTU 1500이고 라우터의 목적지 방향 인터페이스만 1300이에요. 라우터의 IP forwarding은 해당 netns 안에서만 켰어요. 같은 노드의 기존 Calico 인터페이스·경로·정책은 바꾸지 않았어요.</p>
<div class="obsv-fig"><svg viewBox="0 0 700 250" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:700px;height:auto;" role="img" aria-label="출발지와 목적지 MTU는 1500이고 격리 라우터의 송신 인터페이스만 1300인 실험 경로">
<defs><marker id="k53-path-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M1 1.5 Q5 3 8.5 5 Q5 7 1 8.5" fill="none" stroke="#3d3a34" stroke-width="1.5"/></marker></defs>
<path d="M27 66 C80 63 139 68 186 65 L188 151 C130 154 74 150 28 152 Z" fill="#fffdf7" stroke="#4a7fb5" stroke-width="2.4"/>
<path d="M270 64 C327 62 381 68 431 65 L433 152 C378 154 325 150 269 153 Z" fill="#fdf3dd" stroke="#e5a33c" stroke-width="2.4"/>
<path d="M515 65 C566 62 622 67 674 65 L672 152 C620 155 566 150 516 153 Z" fill="#fffdf7" stroke="#5a9e6f" stroke-width="2.4"/>
<path d="M192 108 Q227 105 262 108 M438 108 Q472 111 507 108" fill="none" stroke="#3d3a34" stroke-width="2" marker-end="url(#k53-path-arrow)"/>
<g font-family="'Nanum Pen Script',cursive" font-size="23" text-anchor="middle" fill="#3d3a34"><text x="350" y="30">Calico 장애를 넣지 않은 별도 Linux 경로</text><text x="107" y="96">출발지</text><text x="107" y="129">MTU 1500</text><text x="351" y="96">라우터</text><text x="351" y="129" fill="#b3502f">송신 MTU 1300</text><text x="595" y="96">목적지</text><text x="595" y="129">MTU 1500</text><text x="350" y="198">DF 패킷 1500은 중간에서 전달할 수 없어요.</text><text x="350" y="231" fill="#b3502f">ICMP 3/4 허용 여부만 바꿔 업로드를 비교해요.</text></g>
</svg></div>
<p class="obsv-figcap">그림 2. 양 끝 MTU가 같아도 경로 중간에는 더 작은 구간이 있을 수 있어요.</p>
<p>목적지에는 요청 본문을 모두 읽은 뒤 수신 바이트 수를 답하는 HTTP 서버를 띄웠어요. 출발지는 같은 65,536바이트 파일을 POST했어요. 재현 스크립트는 <a href="https://github.com/DDINGJOO/Platform-study/tree/main/labs/devops/k8s-study/calico-51-56/53">53편 실습 자료</a>에 있어요. 관리용 노드의 기본 네트워크가 아니라 새로 만든 netns 안에서만 실행하는 스크립트예요.</p>

<h2>4. ICMP 피드백을 막자 연결 뒤의 큰 패킷만 재전송됐다</h2>
<p>먼저 격리 라우터가 내보내는 ICMP Destination Unreachable의 code 4만 차단했어요. 다른 ICMP나 TCP 전체를 막은 것이 아니에요. 작은 ping은 응답했고, 출발지에서 캡처한 TCP에는 SYN, SYN-ACK, ACK가 모두 있었어요. 짧은 HTTP 요청 헤더 154바이트에 대한 ACK도 돌아왔어요.</p>
<p>그 뒤 IP 패킷 길이 1500인 본문 전송이 시작됐어요. 같은 TCP 순서 번호 구간 <code>4286112550:4286113998</code>이 처음 전송 이후 약 0.21초, 0.62초, 1.43초, 3.10초에 다시 나왔어요. 마지막에는 curl이 설정한 4초 제한으로 종료됐어요. 출발지 캡처에는 MTU를 알려 주는 ICMP가 없었고 라우터의 DROP 규칙 카운터는 16패킷이었어요. 이 카운터에는 앞서 보낸 큰 ping도 포함돼요.</p>
<div class="obsv-term"><div class="obsv-tt">📖 용어: MSS</div>TCP 연결을 시작할 때 상대에게 알리는 수신 가능한 TCP 데이터 크기예요. 경로 전체의 최소 MTU를 미리 증명하는 값은 아니에요. 이번 양쪽 SYN의 MSS는 1460이었지만 중간 경로의 MTU는 1300이었어요.</div>
<div class="obsv-code"># 격리 라우터의 netns 안에서만 실행
sudo ip netns exec cb53-rtr iptables -A OUTPUT -p icmp --icmp-type 3/4 -j DROP

# 출발지에서 같은 64KiB 파일 POST: 4초 뒤 종료 코드 28
http=000 uploaded=65536 total=4.002032

# ICMP 차단 규칙의 실제 카운터: 큰 ping과 TCP 실험을 함께 센 값
16  9216 DROP  ...  icmptype 3 code 4</div>
<p>종료 코드 28은 curl의 시간 제한에 걸렸다는 뜻이에요. 4초는 이 실험에서 정한 관찰 한도이며 TCP가 반드시 4초에 포기한다는 뜻은 아니에요. <a href="https://www.rfc-editor.org/rfc/rfc2923.html">RFC 2923의 PMTUD black hole 설명</a>도 작은 패킷이나 연결 설정이 통과한 뒤 큰 전송에서 문제가 드러나는 상황을 다뤄요.</p>
<div class="obsv-callout"><div class="obsv-ct">⚠️ uploaded=65536은 서버 수신 완료가 아니에요</div>curl의 전송 수치만으로 원격 애플리케이션이 본문을 모두 받았다고 판단하면 안 돼요. 이 실행에는 HTTP 응답이 없었어요. 완료 여부는 서버가 본문 전체를 읽고 반환하는 <code>received=65536</code>과 HTTP 200으로 별도 확인했어요.</div>

<h2>5. ICMP만 허용하자 PMTU 1300을 배우고 업로드가 완료됐다</h2>
<p>인터페이스 MTU와 경로는 그대로 두고 방금 만든 DROP 규칙만 지웠어요. 새 연결의 SYN에 나온 MSS는 여전히 1460이었어요. 첫 큰 패킷 뒤에는 출발지 캡처에 <code>need to frag (mtu 1300)</code>이 나타났고, 이어서 IP 길이 1300의 TCP 패킷이 나왔어요.</p>
<p>이 패킷의 TCP 데이터는 1248바이트였어요. 이번 연결은 TCP timestamp 옵션을 사용해서 IPv4 헤더 20 + TCP 헤더와 옵션 32 + 데이터 1248 = 1300이 됐어요. SYN의 MSS가 1460이었다는 사실과 실제 데이터 패킷이 1248바이트로 줄었다는 사실은 모순이 아니에요.</p>
<div class="obsv-fig"><svg viewBox="0 0 700 262" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:700px;height:auto;" role="img" aria-label="ICMP 차단 시 1500바이트 재전송과 허용 시 MTU1300 학습 후 크기 축소 비교">
<path d="M29 46 C190 43 499 49 670 45 L670 119 C500 122 188 117 30 121 Z" fill="#fbeee7" stroke="#b3502f" stroke-width="2.2"/>
<path d="M29 145 C190 143 502 148 670 144 L669 222 C501 225 189 220 30 223 Z" fill="#fffdf7" stroke="#5a9e6f" stroke-width="2.2"/>
<g font-family="'Nanum Pen Script',cursive" font-size="23" fill="#3d3a34"><text x="51" y="75" fill="#b3502f">ICMP 차단</text><text x="51" y="105">SYN 성공 → 큰 데이터 1500 재전송 → 4초 관찰 종료</text><text x="51" y="174" fill="#2e6b41">ICMP 허용</text><text x="51" y="206">need to frag 1300 → TCP 크기 조정 → 서버가 65536 수신</text></g>
<text x="350" y="251" text-anchor="middle" font-family="'Nanum Pen Script',cursive" font-size="20" fill="#8a8272">고친 것은 경로의 크기가 아니라 크기를 알려 주는 피드백이었어요.</text>
</svg></div>
<p class="obsv-figcap">그림 3. 같은 1300바이트 경로에서도 ICMP 피드백 유무에 따라 결과가 달랐어요.</p>
<p>서버는 <code>received=65536</code>을 반환했고 curl은 HTTP 200, 종료 코드 0으로 끝났어요. 출발지의 <code>ip route get 198.51.100.2</code>에는 <code>cache expires 599sec mtu 1300</code>이 보였어요. 그 뒤 ping 데이터 1272는 성공하고 1273은 로컬 MTU 1300 검사에서 거절됐어요. 이제는 출발지 커널도 더 작은 경로 한도를 알고 있었어요.</p>
<p><img src="https://raw.githubusercontent.com/DDINGJOO/Platform-study/main/posts/CS/DevOps/k8s-study/images/calico-53/pmtud-feedback.png" alt="격리 경로에서 ICMP3/4 차단 시 curl4초timeout, 규칙삭제 후 received65536 HTTP200으로 성공한 저장 출력" style="max-width:100%"></p>
<p class="obsv-figcap">실행 기록 2. 같은 원문에서 차단·허용 결과를 발췌하고 카운터 줄의 공백만 정리했어요.</p>

<h2>6. 큰 요청 장애는 로컬 거절, 경로 피드백, 패킷 캡처를 나눠 본다</h2>
<p>파드와 노드의 MTU를 먼저 나란히 확인하고 목적지·방향·크기를 고정해요. <code>message too long</code>이 로컬에서 나왔는지, 중간 라우터의 ICMP가 돌아왔는지, 응답 없이 같은 순서 번호가 재전송되는지를 구분해야 해요. 단순히 curl이 멈춘다는 이유만으로 MTU를 원인으로 확정할 수는 없어요.</p>
<p>큰 HTTP 응답이 한 번 성공한 것도 IP 패킷이 그 크기로 한 번에 전달됐다는 증거는 아니에요. 애플리케이션 본문은 여러 TCP 세그먼트로 나뉘고, 캡처 시점에 따라 여러 세그먼트가 합쳐 보일 수도 있어요. 이번 업로드 실험은 양 끝과 라우터의 실험용 veth에서 TSO·GSO·GRO를 꺼 캡처 해석을 단순하게 했어요.</p>
<div class="obsv-term"><div class="obsv-tt">📖 용어: offload</div>패킷 분할·병합 같은 처리를 커널의 다른 단계나 장치로 넘기는 기능이에요. 실제 선로에 나가는 크기와 호스트에서 tcpdump가 본 크기가 다를 수 있어요. 큰 캡처 패킷 하나만 보고 MTU 위반이라고 판단하지 않아요.</div>
<p>통제한 설정도 확인해야 해요. 이번 격리 출발지의 <code>net.ipv4.tcp_mtu_probing</code>은 0으로 고정했어요. <a href="https://docs.kernel.org/6.8/networking/ip-sysctl.html#tcp-variables">Linux 6.8 문서</a>에서 이 값은 TCP의 Packetization-Layer PMTU 탐색을 끄는 설정이에요. 다른 설정과 구현에서는 ICMP가 없어도 별도 탐색으로 회복할 수 있으므로 이번 4초 실패를 모든 TCP 연결의 필연적인 결과로 일반화하지 않아요.</p>
<div class="obsv-callout"><div class="obsv-ct">💡 실무에서는 이미 학습한 PMTU도 확인해요</div>같은 목적지로 반복하면 커널이 앞서 배운 PMTU를 재사용할 수 있어요. 정책 변경 전후 비교에서는 새 연결인지, 경로에 <code>mtu</code>가 캐시됐는지 함께 남겨요. 이번에는 피드백 차단 상태부터 시작한 새 netns에서 측정한 뒤 같은 경로의 피드백만 허용했어요.</div>
<p>원문·pcap·파드 매니페스트·재현 스크립트는 <a href="https://github.com/DDINGJOO/Platform-study/tree/main/labs/devops/k8s-study/calico-51-56/53">53편 실습 디렉터리</a>에 보관했어요. 실험 뒤 임시 Kubernetes namespace와 세 Linux netns를 제거한 것도 확인했어요. 실제 Calico의 정상 한도를 측정한 결과와 별도 Linux 경로의 장애 재현을 분리해서 읽으면 돼요.</p>
<div class="obsv-summary"><div class="obsv-st2">✍️ 오늘의 요약</div>
<b>실제 Calico 파드의 1480바이트 한도는 ping 데이터 1452바이트와 IPv4·ICMP 헤더를 합친 값이었어요.</b><br><br>
별도 경로에서는 TCP 연결 성공 뒤에도 큰 전송이 멈췄고 ICMP 피드백을 허용하자 PMTU를 학습해 완료됐어요. 로컬 거절과 경로 중간의 실패를 구분하는 데 필요한 것은 패킷 크기, 오류의 위치, 피드백과 재전송 기록이에요.
</div>
'''
html='<!-- tags: MTU, PMTUD, IPIP, ICMP, TCP MSS -->\n<!-- lead: Calico 파드에서 ping 데이터 1452바이트는 통과하고 1453바이트는 로컬 오류로 거절됐어요. 별도 격리 경로에서는 작은 요청과 TCP 연결이 성공해도 큰 업로드가 멈추는 상황을 만들고, ICMP 피드백과 패킷 크기를 비교했어요. -->\n'+style+'\n<div class="obsv-wrap">\n'+series+body+'\n</div>\n'
out=ROOT/entry['file'];out.write_text(html)
print(out)
