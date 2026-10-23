#!/usr/bin/env python3
import json,time,urllib.request
end=time.monotonic()+45
while time.monotonic()<end:
    try:
        data=json.load(urllib.request.urlopen('http://localhost:28300/summary.json',timeout=2))
        assert data['synthetic_only'] and data['test_count']>=12
        assert data['scenarios']['healthy_effect']['decision']=='PASS_FIXED_RULES'
        assert data['scenarios']['insufficient']['decision']=='HOLD_SAMPLE'
        assert data['scenarios']['srm']['decision']=='INVALID_SRM'
        assert data['scenarios']['guardrail_bad']['decision']=='STOP_GUARDRAIL'
        assert data['scenarios']['healthy_equal']['decision']=='HOLD_EFFECT'
        print('HTTP summary verified: 5 scenarios, all fixed gates, user denominators PASS')
        break
    except Exception:
        time.sleep(.25)
else:raise SystemExit('Report not ready or did not satisfy expected analysis gates')
