#!/usr/bin/env python3
"""Read the saved classic-pcap files, match the two test TCP flows, and verify SYN continuity."""
from pathlib import Path
import ipaddress, json, struct
HERE=Path(__file__).resolve().parent

def packets(file):
    data=file.read_bytes()
    order='<' if data[:4]==bytes.fromhex('d4c3b2a1') else '>'
    assert data[:4] in [bytes.fromhex('d4c3b2a1'),bytes.fromhex('a1b2c3d4')]
    link=struct.unpack(order+'IHHIIII',data[:24])[-1]
    pos=24
    def ip(raw):
        if len(raw)<20 or raw[0]>>4!=4:return None
        h=(raw[0]&15)*4
        result={'src':str(ipaddress.ip_address(raw[12:16])),'dst':str(ipaddress.ip_address(raw[16:20])),
                'ttl':raw[8],'proto':raw[9],'length':int.from_bytes(raw[2:4],'big'),
                'id':int.from_bytes(raw[4:6],'big'),'ihl':h}
        if raw[9]==4:result['inner']=ip(raw[h:])
        if raw[9]==6:
            tcp=raw[h:]
            result.update(sport=int.from_bytes(tcp[:2],'big'),dport=int.from_bytes(tcp[2:4],'big'),
                          seq=int.from_bytes(tcp[4:8],'big'),ack=int.from_bytes(tcp[8:12],'big'),flags=tcp[13])
        return result
    while pos<len(data):
        sec,usec,caplen,wirelen=struct.unpack(order+'IIII',data[pos:pos+16])
        raw=data[pos+16:pos+16+caplen];pos+=16+caplen
        if link==1:
            if raw[12:14]!=b'\x08\x00':continue
            raw=raw[14:]
        else:assert link==101,link
        yield {'timestamp':f'{sec}.{usec:06d}','captured':caplen,'wire':wirelen,'ip':ip(raw)}

env=json.loads((HERE/'environment.json').read_text())
client=env['ips']['client']
summary={}
for file in sorted(HERE.glob('*.pcap')):
    saved=list(packets(file));counts={45252:0,45253:0};syn=[]
    for packet in saved:
        outer=packet['ip'];inner=outer.get('inner',outer)
        if not inner or client not in (inner['src'],inner['dst']):continue
        for port in counts:
            if port in (inner.get('sport'),inner.get('dport')):counts[port]+=1
        if inner.get('flags')==2 and inner.get('sport') in counts:syn.append(packet)
    summary[file.stem]={'total_packets':len(saved),'experiment_packet_counts':counts,'initial_syn':syn}

order=['client-eth0','client-cali','local-cali','worker1-tunl0','worker1-eth0','worker2-eth0','worker2-tunl0','remote-cali']
rows=['Capture point             local:45252  remote:45253  remote SYN TTL  outer IPIP']
remote_syn={}
for name in order:
    item=summary[name]
    cross=[p for p in item['initial_syn'] if p['ip'].get('inner',p['ip']).get('sport')==45253]
    ttl=cross[0]['ip'].get('inner',cross[0]['ip'])['ttl'] if cross else '-'
    if cross:
        assert len(cross)==1
        remote_syn[name]=cross[0]['ip'].get('inner',cross[0]['ip'])
    outer='yes' if cross and 'inner' in cross[0]['ip'] else 'no'
    rows.append(f'{name:26} {item["experiment_packet_counts"][45252]:>5} {item["experiment_packet_counts"][45253]:>13} {str(ttl):>15} {outer:>11}')

# Prove claims about these recorded flows; these assertions are not a guarantee for other runs.
assert len({p['seq'] for p in remote_syn.values()})==1
assert len({p['id'] for p in remote_syn.values()})==1
for name in order:
    assert summary[name]['experiment_packet_counts'][45252]==(12 if name in ['client-eth0','client-cali','local-cali'] else 0)
    assert summary[name]['experiment_packet_counts'][45253]==(0 if name=='local-cali' else 12)
for name in ['worker1-eth0','worker2-eth0']:
    outer=summary[name]['initial_syn'][0]['ip']
    assert outer['src']=='192.168.104.3' and outer['dst']=='192.168.104.4' and outer['proto']==4
    assert outer['length']==outer['inner']['length']+20
assert remote_syn['client-eth0']['ttl']==64
assert remote_syn['worker1-tunl0']['ttl']==63
assert remote_syn['remote-cali']['ttl']==62
(HERE/'analysis.json').write_text(json.dumps(summary,indent=2)+'\n')
(HERE/'capture-summary.txt').write_text('\n'.join(rows)+'\n')
print('\n'.join(rows))
