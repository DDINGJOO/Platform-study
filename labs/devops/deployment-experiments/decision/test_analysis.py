import copy,json,math,pathlib,unittest
from analysis import analyze,wilson,srm,difference_interval,percentile95
from generate import build_fixture
ROOT=pathlib.Path(__file__).resolve().parent
PLAN=json.loads((ROOT/'plan.json').read_text())
FIXTURES=json.loads((ROOT/'fixtures.json').read_text())
class AnalysisTests(unittest.TestCase):
    def small(self):return build_fixture(FIXTURES[2],PLAN)
    def test_five_declared_decisions(self):
        for spec in FIXTURES:
            with self.subTest(scenario=spec['name']):
                result=analyze(build_fixture(spec,PLAN),PLAN)
                self.assertEqual(result['decision'],spec['expected_decision'])
                for v in ['A','B']:
                    self.assertEqual(result['groups'][v]['exposed_users'],spec[v]['users'])
                    self.assertEqual(result['groups'][v]['converted_users'],spec[v]['conversions'])
    def test_user_dedup_not_event_denominator(self):
        result=analyze(self.small(),PLAN)
        self.assertEqual(result['dedup']['duplicate_event_ids'],20)
        self.assertEqual(result['dedup']['repeat_exposure_events'],20)
        self.assertEqual(result['dedup']['repeat_conversion_events'],10)
        self.assertEqual(result['dedup']['excluded_conversion_events'],4)
        self.assertEqual(result['dedup']['repeat_request_events'],10)
        self.assertEqual(result['groups']['A']['requests'],100)
        self.assertEqual(result['groups']['B']['conversion_rate'],.2)
    def test_srm_and_chi_square_reference(self):
        self.assertEqual(srm(100,100)['p_value'],1)
        r=srm(2800,1200)
        self.assertEqual(r['expected'],{'A':2000.0,'B':2000.0})
        self.assertEqual(r['chi2'],640)
        self.assertLess(r['p_value'],.001)
        # NIST df=1 critical value table: 3.841 -> upper tail ~0.05.
        self.assertAlmostEqual(math.erfc(math.sqrt(3.841/2)),.05,places=4)
        self.assertFalse(srm(1,1)['valid_approximation'])
    def test_wilson_reference_and_extremes(self):
        lo,hi=wilson(10,100)
        self.assertAlmostEqual(lo,.0552291370606751,places=12)
        self.assertAlmostEqual(hi,.174365661504913,places=12)
        self.assertAlmostEqual(wilson(0,10)[0],0)
        self.assertAlmostEqual(wilson(10,10)[1],1)
        self.assertGreater(wilson(0,10)[1],0)
        with self.assertRaises(ValueError):wilson(0,0)
    def test_difference_sign_and_uncertainty(self):
        lo,hi=difference_interval(200,2000,280,2000)
        self.assertGreater(lo,0)
        rev=difference_interval(280,2000,200,2000)
        self.assertAlmostEqual(lo,-rev[1]);self.assertAlmostEqual(hi,-rev[0])
        self.assertLess(difference_interval(200,2000,200,2000)[0],0)
        self.assertGreater(difference_interval(200,2000,200,2000)[1],0)
    def test_under_sample_never_passes_on_large_effect(self):
        r=analyze(self.small(),PLAN)
        self.assertTrue(r['gates']['effect'])
        self.assertFalse(r['gates']['sample'])
        self.assertEqual(r['decision'],'HOLD_SAMPLE')
    def test_window_not_closed_even_with_many_users(self):
        payload=build_fixture(FIXTURES[1],PLAN)
        r=analyze(payload,PLAN,as_of='2026-10-06T00:00:00Z')
        self.assertTrue(r['gates']['sample'])
        self.assertEqual(r['decision'],'HOLD_WINDOW')
    def test_cross_variant_user_is_invalid(self):
        p=self.small();event=copy.deepcopy(p['events'][0]);event['event_id']='changed-user';event['variant']='B';p['events'].append(event)
        self.assertEqual(analyze(p,PLAN)['decision'],'INVALID_ASSIGNMENT')
    def test_no_guardrail_observations_cannot_pass(self):
        p=build_fixture(FIXTURES[1],PLAN)
        p['events']=[e for e in p['events'] if e['event_type']!='request']
        self.assertEqual(analyze(p,PLAN)['decision'],'HOLD_GUARDRAILS')
    def test_tiny_srm_sample_is_held_not_called_mismatch(self):
        spec={'name':'tiny','A':{'users':1,'conversions':0,'errors':0,'latency_base':100},'B':{'users':1,'conversions':0,'errors':0,'latency_base':100}}
        r=analyze(build_fixture(spec,PLAN),PLAN)
        self.assertIsNone(r['srm']['p_value'])
        self.assertEqual(r['decision'],'HOLD_SAMPLE')
    def test_entry_only_user_is_not_denominator(self):
        p=self.small();e=copy.deepcopy(p['events'][0]);e['event_id']='entry-only';e['user_id']='synthetic-entry-only';p['events'].append(e)
        self.assertEqual(analyze(p,PLAN)['groups']['A']['exposed_users'],100)
    def test_conflicting_event_id_rejected(self):
        p=self.small();e=copy.deepcopy(p['events'][0]);e['variant']='B';p['events'].append(e)
        with self.assertRaisesRegex(ValueError,'event_id'):analyze(p,PLAN)
    def test_conflicting_request_id_rejected(self):
        p=self.small();e=copy.deepcopy(next(e for e in p['events'] if e['event_type']=='request'));e['event_id']='changed-request';e['error']=not e['error'];p['events'].append(e)
        with self.assertRaisesRegex(ValueError,'request_id'):analyze(p,PLAN)
    def test_enrollment_and_conversion_boundary(self):
        p=self.small()
        for e in p['events']:
            if e['user_id']=='synthetic-B-0000' and e['event_type']=='conversion': e['occurred_at']='2026-10-02T01:00:01Z'
        r=analyze(p,PLAN)
        self.assertEqual(r['groups']['B']['converted_users'],19)
        self.assertEqual(percentile95(list(range(100))),94)
if __name__=='__main__':unittest.main()
