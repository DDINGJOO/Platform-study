#!/usr/bin/env python3
"""Print a compact report from saved observations, not a live cluster query."""
import json
from pathlib import Path

D = Path(__file__).resolve().parent
x = json.loads((D / 'verified.json').read_text())
pair = next(z for z in x['pods'] if z['pod'] == 'pair')
host = next(z for z in x['pods'] if z['pod'] == 'host')
eth = next(z for z in pair['links'] if z['ifname'] == 'eth0')
clean = json.loads((D / '26-host-links-clean.txt').read_text().split('\n', 1)[1])
assert x['peer']['ifname'] not in {z['ifname'] for z in clean}
print('Saved observation: calico-blog-51 on k8s-worker1\n')
print('pair sandbox/app0/app1 share netns:', all(z['netns'] == pair['sandboxNetns'] for z in pair['containers']))
print('hostNetwork sandbox uses host netns:', host['sandboxNetns'] == x['hostNetns'])
print(f'\nPod eth0: ifindex={eth["ifindex"]}, peer index={eth["link_index"]}, MTU={eth["mtu"]}')
print(f'Host {x["peer"]["ifname"]}: ifindex={x["peer"]["ifindex"]}, peer index={x["peer"]["link_index"]}')
print('Bidirectional peer match:', eth['link_index'] == x['peer']['ifindex'] and x['peer']['link_index'] == eth['ifindex'])
print('Cleanup: namespace NotFound; experiment veth absent')
