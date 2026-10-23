"""Deterministic synthetic event fixtures, including retries and invalid temporal conversions."""
import datetime as dt
from analysis import instant

def build_fixture(spec, plan):
    name=spec['name']
    payload={'schema_version':1,'experiment_id':plan['experiment_id'],'synthetic':True,'scenario':name,'events':[]}
    events=payload['events']
    start=instant(plan['start'])
    def add(user,variant,kind,when,suffix,**extra):
        e={'event_id':f'{name}-{user}-{suffix}','experiment_id':plan['experiment_id'],
           'user_id':user,'variant':variant,'event_type':kind,'request_id':f'{name}-{user}-request',
           'occurred_at':when.isoformat().replace('+00:00','Z'),**extra}
        events.append(e)
        return e
    for variant in ['A','B']:
        cfg=spec[variant]
        assert 0 <= cfg['conversions'] <= cfg['users'] and 0 <= cfg['errors'] <= cfg['users']
        for i in range(cfg['users']):
            user=f'synthetic-{variant}-{i:04}'
            when=start+dt.timedelta(hours=1, seconds=30*i)
            add(user,variant,'entry',when-dt.timedelta(seconds=1),'entry')
            exposure=add(user,variant,'exposure',when,'exposure')
            # Both event-id retries and new event IDs for the same user's exposure occur.
            if i<10:
                events.append(dict(exposure))
                add(user,variant,'exposure',when+dt.timedelta(seconds=1),'refresh')
            req=add(user,variant,'request',when+dt.timedelta(seconds=2),'request',error=i<cfg['errors'],latency_ms=cfg['latency_base']+(i%50))
            if i<5: add(user,variant,'request',when+dt.timedelta(seconds=3),'request-retry',error=req['error'],latency_ms=req['latency_ms'])
            if i<cfg['conversions']:
                add(user,variant,'conversion',when+dt.timedelta(minutes=5),'conversion')
                if i<5:add(user,variant,'conversion',when+dt.timedelta(minutes=6),'conversion-repeat')
            # These should NEVER change the converted-user numerator.
            if i==cfg['users']-1:
                add(user,variant,'conversion',when-dt.timedelta(seconds=2),'conversion-before-exposure')
                add(user,variant,'conversion',when+dt.timedelta(hours=25),'conversion-after-window')
    return payload
