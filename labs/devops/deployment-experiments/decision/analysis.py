"""A small transparent fixed-window analyzer. No telemetry trace count is a denominator."""
import datetime as dt
import math
from statistics import NormalDist

def instant(value):
    return dt.datetime.fromisoformat(value.replace('Z', '+00:00'))

def wilson(successes, total, alpha=0.05):
    if not 0 <= successes <= total or total <= 0:
        raise ValueError('Wilson requires 0 <= successes <= total and total > 0')
    z = NormalDist().inv_cdf(1-alpha/2)
    p = successes / total
    denominator = 1 + z*z/total
    center = (p + z*z/(2*total)) / denominator
    radius = z*math.sqrt(p*(1-p)/total + z*z/(4*total*total)) / denominator
    return max(0.0, center-radius), min(1.0, center+radius)

def difference_interval(x_a, n_a, x_b, n_b, alpha=0.05):
    # Newcombe's uncorrected hybrid score interval for independent proportions.
    # Formula checked against statsmodels 0.15.0 confint_proportions_2indep(newcomb).
    la, ua = wilson(x_a, n_a, alpha)
    lb, ub = wilson(x_b, n_b, alpha)
    pa, pb = x_a/n_a, x_b/n_b
    delta = pb-pa
    lower = delta-math.hypot(pb-lb, ua-pa)
    upper = delta+math.hypot(ub-pb, pa-la)
    return lower, upper

def srm(a, b, expected_a=0.5):
    expected = {'A': (a+b)*expected_a, 'B': (a+b)*(1-expected_a)}
    if min(expected.values()) < 5:
        return {'observed':{'A':a,'B':b}, 'expected':expected, 'chi2':None, 'p_value':None, 'valid_approximation':False}
    stat = (a-expected['A'])**2/expected['A'] + (b-expected['B'])**2/expected['B']
    # For one degree of freedom, chi-square survival equals 2*(1-Phi(sqrt(x))).
    return {'observed':{'A':a,'B':b}, 'expected':expected, 'chi2':stat,
            'p_value':math.erfc(math.sqrt(stat/2)), 'valid_approximation':True}

def percentile95(values):
    if not values: return None
    return sorted(values)[math.ceil(.95*len(values))-1]  # nearest-rank, not interpolated

def analyze(payload, plan, as_of=None):
    as_of = instant(as_of or plan['analysis_at'])
    start, end = instant(plan['start']), instant(plan['enrollment_end'])
    analysis_at = instant(plan['analysis_at'])
    assert end + dt.timedelta(hours=plan['conversion_hours']) <= analysis_at
    if payload.get('experiment_id') != plan['experiment_id']:
        raise ValueError('experiment_id does not match predeclared plan')
    if payload.get('schema_version') != 1:
        raise ValueError('unsupported schema_version')
    events_by_id = {}
    duplicates = 0
    excluded_foreign = 0
    for event in payload['events']:
        if event['experiment_id'] != plan['experiment_id']:
            excluded_foreign += 1
            continue
        if event['variant'] not in ('A','B'):
            raise ValueError('unknown variant')
        if event['event_id'] in events_by_id:
            if event != events_by_id[event['event_id']]:
                raise ValueError('conflicting payload reused an event_id')
            duplicates += 1
        else: events_by_id[event['event_id']] = event
    events = list(events_by_id.values())
    variants = {}
    crossed = set()
    for event in events:
        when = instant(event['occurred_at'])
        if start <= when <= min(analysis_at, as_of):
            user = event['user_id']
            if user in variants and variants[user] != event['variant']: crossed.add(user)
            variants[user] = event['variant']
    exposure = {}
    repeated_exposures = 0
    for event in sorted(events, key=lambda e: instant(e['occurred_at'])):
        if event['event_type'] != 'exposure': continue
        when = instant(event['occurred_at'])
        if not start <= when < end or when > as_of: continue
        user = event['user_id']
        if user in exposure: repeated_exposures += 1
        else: exposure[user] = event
    converted = set()
    conversion_events = 0
    excluded_conversion_events = 0
    requests = {}
    repeated_requests = 0
    for event in events:
        when = instant(event['occurred_at'])
        user = event['user_id']
        first = exposure.get(user)
        eligible = first is not None and first['variant'] == event['variant']
        if eligible:
            exposed_at = instant(first['occurred_at'])
            eligible = exposed_at <= when <= min(exposed_at+dt.timedelta(hours=plan['conversion_hours']), analysis_at, as_of)
        if event['event_type'] == 'conversion':
            if eligible:
                converted.add(user)
                conversion_events += 1
            else: excluded_conversion_events += 1
        if event['event_type'] == 'request' and eligible:
            key = event['request_id']
            if key in requests:
                old=requests[key]
                if any(old.get(k) != event.get(k) for k in ('user_id','variant','error','latency_ms')):
                    raise ValueError('conflicting payload reused request_id')
                repeated_requests += 1
            else:
                if not isinstance(event.get('error'), bool): raise ValueError('request requires boolean error')
                latency=event.get('latency_ms')
                if not isinstance(latency,(int,float)) or isinstance(latency,bool) or not math.isfinite(latency) or latency < 0:
                    raise ValueError('request requires finite nonnegative latency_ms')
                requests[key] = event
    counts = {}
    for variant in ['A','B']:
        users = {u for u,e in exposure.items() if e['variant'] == variant}
        n, x = len(users), len(users & converted)
        req = [r for r in requests.values() if r['variant'] == variant]
        errors=sum(r['error'] for r in req)
        rate=x/n if n else None
        counts[variant]={'exposed_users':n,'converted_users':x,'conversion_rate':rate,
            'wilson95':wilson(x,n,plan['interval_alpha']) if n else None,
            'requests':len(req), 'errors':errors,'error_rate':errors/len(req) if req else None,
            'p95_ms':percentile95([r['latency_ms'] for r in req])}
    ratio=srm(counts['A']['exposed_users'], counts['B']['exposed_users'],plan['expected_allocation']['A'])
    ratio['pass'] = ratio['valid_approximation'] and ratio['p_value'] >= plan['srm_alpha']
    complete = as_of >= analysis_at
    sample = all(c['exposed_users'] >= plan['minimum_users_per_variant'] for c in counts.values())
    guardrails_known = all(c['requests'] for c in counts.values())
    guards = {'observed':guardrails_known, 'error_rate':False, 'absolute_p95':False, 'relative_p95':False}
    if guardrails_known:
        guards.update(error_rate=all(c['error_rate'] <= plan['maximum_error_rate'] for c in counts.values()),
            absolute_p95=all(c['p95_ms'] <= plan['maximum_p95_ms'] for c in counts.values()),
            relative_p95=counts['B']['p95_ms'] <= counts['A']['p95_ms']*plan['maximum_p95_ratio'])
    guardrails_pass=all(guards.values())
    delta=interval=None
    effect=False
    if all(c['exposed_users'] for c in counts.values()):
        a,b=counts['A'],counts['B']
        delta=b['conversion_rate']-a['conversion_rate']
        interval=difference_interval(a['converted_users'],a['exposed_users'],b['converted_users'],b['exposed_users'],plan['interval_alpha'])
        effect=interval[0] > 0 and delta >= plan['minimum_observed_difference']
    gates={'data_quality':not crossed,'window_complete':complete,'srm':ratio['pass'],'sample':sample,'guardrails_observed':guardrails_known,'guardrails':guardrails_pass,'effect':effect}
    if crossed: decision='INVALID_ASSIGNMENT'
    elif not complete: decision='HOLD_WINDOW'
    elif not ratio['valid_approximation']: decision='HOLD_SAMPLE'
    elif not ratio['pass']: decision='INVALID_SRM'
    elif not sample: decision='HOLD_SAMPLE'
    elif not guardrails_known: decision='HOLD_GUARDRAILS'
    elif not guardrails_pass: decision='STOP_GUARDRAIL'
    elif not effect: decision='HOLD_EFFECT'
    else: decision='PASS_FIXED_RULES'
    return {'groups':counts,'srm':ratio,'difference':delta,'difference95_newcombe':interval,'gates':gates,'guardrails':guards,'decision':decision,
        'dedup':{'input_events':len(payload['events']),'unique_event_ids':len(events),'duplicate_event_ids':duplicates,'repeat_exposure_events':repeated_exposures,'valid_conversion_events':conversion_events,'repeat_conversion_events':conversion_events-len(converted),'excluded_conversion_events':excluded_conversion_events,'repeat_request_events':repeated_requests,'cross_variant_users':len(crossed),'excluded_foreign_events':excluded_foreign}}
