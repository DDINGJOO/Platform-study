#!/usr/bin/env python3
"""Real Compose rollouts -> real request metrics -> official Kayenta analysis.
Resets only deployment-experiments-01. Does not drive a Spinnaker deploy pipeline.
"""
import concurrent.futures,datetime,json,os,pathlib,statistics,subprocess,threading,time,urllib.error,urllib.parse
from urllib.request import Request,urlopen
ROOT=pathlib.Path(__file__).resolve().parent;OUT=ROOT/'out'
APP='deployment-experiments';CONFIG=None
LATENCY='1000 * sum(rate(orders_duration_seconds_sum{role="%s"}[10s])) / sum(rate(orders_duration_seconds_count{role="%s"}[10s]))'
def request(port,path,payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=Request(f'http://localhost:{port}{path}',data,{'Content-Type':'application/json'})
    try:
        with urlopen(req,timeout=20) as r:
            raw=r.read()
            return json.loads(raw) if raw[:1] in (b'{',b'[') else raw.decode()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'{port} {path} HTTP {e.code}: {e.read().decode()[:1500]}')
def compose(*args,extra=None):
    env=os.environ.copy();env.update(extra or {})
    subprocess.run(['docker','compose',*args],cwd=ROOT,env=env,check=True)
def poll(fn,timeout=180):
    until=time.monotonic()+timeout;last=None
    while time.monotonic()<until:
        try:
            value=fn()
            if value:return value
        except Exception as e:last=e
        time.sleep(.5)
    raise AssertionError(f'poll timeout: {last}')
def iso(epoch):return datetime.datetime.fromtimestamp(epoch,datetime.timezone.utc).isoformat().replace('+00:00','Z')
def save(name,data):
    (OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def prom_range(role,start,end):
    q=LATENCY%(role,role)
    params=urllib.parse.urlencode({'query':q,'start':start,'end':end,'step':2})
    result=request(28104,'/api/v1/query_range?'+params)
    assert result['status']=='success' and len(result['data']['result'])==1
    return result['data']['result'][0]['values']
class Load:
    def __init__(self,roles):
        self.roles=roles;self.stop=threading.Event();self.rows={role:[] for role in roles};self.errors=[];self.threads=[]
    def start(self):
        barrier=threading.Barrier(len(self.roles));self.began=time.time()
        def work(role,port):
            barrier.wait();i=0;begin=time.monotonic()
            while not self.stop.is_set():
                try:
                    data=request(port,f'/work?key={i%128}');self.rows[role].append({'epoch':time.time(),**data})
                except Exception as e:self.errors.append(str(e))
                i+=1;delay=begin+i*.25-time.monotonic()
                if delay>0:self.stop.wait(delay)
        for role,port in self.roles.items():
            t=threading.Thread(target=work,args=(role,port),daemon=True);t.start();self.threads.append(t)
        return self
    def close(self):
        self.stop.set()
        for t in self.threads:t.join(timeout=30)
        assert not self.errors,self.errors

def analysis(label,control,experiment,start,end):
    def scope(role):return {'scope':role,'location':'local','start':iso(start),'end':iso(end),'step':2}
    body={'scopes':{'default':{'controlScope':scope(control),'experimentScope':scope(experiment)}},'thresholds':{'marginal':75,'pass':95}}
    save(label+'-analysis-request.json',body)
    result=request(28102,f'/canary/{CONFIG}?application={APP}&metricsAccountName=prometheus&configurationAccountName=memory&storageAccountName=memory',body)
    save(label+'-analysis-start.json',result)
    runid=result['canaryExecutionId']
    def done():
        r=request(28102,f'/canary/{runid}?storageAccountName=memory')
        if str(r.get('status','')).upper() in ('SUCCEEDED','TERMINAL','FAILED','CANCELED'):return r
    final=poll(done,180);save(label+'-kayenta.json',final)
    pairs=request(28102,f"/metricSetPairList/{final['metricSetPairListId']}?storageAccountName=memory")
    save(label+'-kayenta-metric-pairs.json',pairs)
    return runid,final

def main():
    global CONFIG
    if OUT.exists() and any(OUT.iterdir()):
        archive=ROOT/'history'/datetime.datetime.now().strftime('%Y%m%dT%H%M%S');archive.parent.mkdir(exist_ok=True);OUT.rename(archive)
    OUT.mkdir(exist_ok=True)
    compose('down','--volumes','--remove-orphans')
    compose('up','-d','--build','redis','kayenta','front50','gate','deck','old','prometheus','grafana')
    for port,path in [(28102,'/health'),(28103,'/health'),(28101,'/health'),(28110,'/health'),(28104,'/-/ready'),(28105,'/api/health')]:
        poll(lambda port=port,path=path:request(port,path),240)
    save('credentials.json',request(28102,'/credentials'));save('judges.json',request(28102,'/judges'))
    kayenta_id=subprocess.check_output(['docker','compose','ps','-q','kayenta'],cwd=ROOT,text=True).strip()
    runtime=json.loads(subprocess.check_output(['docker','inspect',kayenta_id],text=True))[0]
    save('kayenta-runtime.json',{'image':runtime['Config']['Image'],'container_ips':[v['IPAddress'] for v in runtime['NetworkSettings']['Networks'].values()]})
    request(28103,'/v2/applications',{'name':APP,'email':'lab@example.test','cloudProviders':[],'dataSources':{'enabled':['canaryConfigs'],'disabled':['serverGroups','loadBalancers','securityGroups','executions','pipelineConfigs']}})
    cfg=json.loads((ROOT/'config/canary-config.json').read_text())
    CONFIG=request(28102,'/canaryConfig?configurationAccountName=memory',cfg)['canaryConfigId']
    old=Load({'old':28110}).start();poll(lambda:request(28110,'/state')['cache_items']==128,60)
    cases=[]
    try:
        for label,version,delay in [('same-version','v1','0'),('regression','v2','40')]:
            compose('up','-d','--force-recreate','baseline','canary',extra={'CANDIDATE_VERSION':version,'REGRESSION_MS':delay})
            for port in (28111,28112):poll(lambda port=port:request(port,'/health'))
            metadata={role:request(port,'/state') for role,port in [('old',28110),('baseline',28111),('canary',28112)]}
            delta=abs(metadata['baseline']['started_epoch']-metadata['canary']['started_epoch']);assert delta<3,delta
            save(label+'-start-metadata.json',metadata)
            container_ids=subprocess.check_output(['docker','compose','ps','-q','old','baseline','canary'],cwd=ROOT,text=True).split()
            containers=json.loads(subprocess.check_output(['docker','inspect',*container_ids],text=True))
            snapshot=[{'name':r['Name'],'created':r['Created'],'started':r['State']['StartedAt'],'image_id':r['Image'],'image_ref':r['Config']['Image'],'environment':r['Config']['Env'],'memory_bytes':r['HostConfig']['Memory'],'nano_cpus':r['HostConfig']['NanoCpus']} for r in containers]
            save(label+'-containers.json',snapshot)
            pair=Load({'baseline':28111,'canary':28112}).start()
            try:
                # Fill all 128 actual cache entries with identical key sequences.
                poll(lambda:request(28111,'/state')['cache_items']==128 and request(28112,'/state')['cache_items']==128,60)
                # Exclude the 10-second PromQL lookback from the primary warm window.
                poll(lambda:time.time()-pair.began>=46,60)
                start=int(time.time())+2;end=start+120
                print(f'{label}: balanced 4 requests/s/replica, warmup 46s, observe 120s',flush=True)
                poll(lambda:time.time()>=end+3,135)
            finally:pair.close()
            save(label+'-http-observations.json',pair.rows)
            cold={role:prom_range(role,pair.began+10,pair.began+30) for role in ('old','baseline','canary')}
            data={role:prom_range(role,start,end) for role in ('old','baseline','canary')}
            for role,values in data.items():assert len(values)>=50,(role,len(values))
            save(label+'-prometheus-series.json',{'warm':data,'cold_diagnostic':cold,'start':iso(start),'end':iso(end)})
            counts={role:sum(start<=r['epoch']<=end for r in rows) for role,rows in pair.rows.items()}
            assert abs(counts['baseline']-counts['canary'])<=1 and min(counts.values())>=479,counts
            runid,result=analysis(label,'baseline','canary',start,end)
            judge=result.get('result',{}).get('judgeResult',{})
            assert str(result['status']).upper()=='SUCCEEDED',result
            assert judge['judgeName']=='NetflixACAJudge-v1.0'
            expected='Pass' if label=='same-version' else 'Fail'
            assert judge['score']['classification']==expected,judge
            assert judge['score']['score']==(100 if expected=='Pass' else 0),judge
            assert judge['results'][0]['controlMetadata']['stats']['count']>=50
            assert judge['results'][0]['experimentMetadata']['stats']['count']>=50
            # Actual response shape is retained for read-only verification and UI.
            case={'scenario':label,'version':version,'injected_regression_ms':float(delay),'created_delta_seconds':delta,'measurement_start':iso(start),'measurement_end':iso(end),'request_counts':counts,'mean_latency_ms':{role:statistics.mean(float(v[1]) for v in values) for role,values in data.items()},'cold_mean_latency_ms':{role:statistics.mean(float(v[1]) for v in values) for role,values in cold.items()},'series_points':{role:len(values) for role,values in data.items()},'config_id':CONFIG,'run_id':runid,'execution_status':result.get('status'),'judge':judge,'deck_url':f'http://localhost:28100/#/applications/{APP}/canary/report/{CONFIG}/{runid}'}
            cases.append(case);save('summary-progress.json',cases)
        save('old-http-observations.json',old.rows)
    finally:old.close()
    # Validate real judge outcomes once full response shape has been inspected.
    summary={'executed_at':iso(time.time()),'spinnaker_version':'2026.1.3','cases':cases,'deployment_owner':'run.py Docker Compose; Kayenta embedded Orca owns analysis execution','notes':['20% effect-size budget fixed before observation','Memory account loses configs/results on Kayenta restart','A is an earlier-started local replica, not long-lived production','Synthetic delay, real HTTP requests and measured Prometheus counters','Overlapping 10s rate windows are correlated, not independent product users']}
    save('summary.json',summary)
    with (OUT/'compose.log').open('w') as f:subprocess.run(['docker','compose','logs','--no-color'],cwd=ROOT,stdout=f,check=True)
    subprocess.run(['docker','compose','cp','prometheus:/prometheus/queries.log',str(OUT/'prometheus-queries.jsonl')],cwd=ROOT,check=True)
    subprocess.run(['python3',str(ROOT/'verify.py')],cwd=ROOT,check=True)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
