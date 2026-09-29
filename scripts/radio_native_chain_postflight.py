"""Independent stdlib-only bytes/journal/reference audit; no detector or RNG."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results_radio_native_chain_engineering_2026-09-29'
LIVE=BASE/'live01'
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(x):return hashlib.sha256(x).hexdigest()
def read(p):return json.loads(p.read_bytes())
def sealed(x,key):
    assert x[key]==sha(canon({k:v for k,v in x.items() if k!=key})),key
    return x

def main():
    plans=read(BASE/'plans.json');allocation=read(BASE/'allocation.json')
    files=sorted((LIVE/'journal/revisions').iterdir());docs=[]
    for p in files:
        data=p.read_bytes();d=json.loads(data);assert canon(d)==data and sha(data)==p.name
        assert d['manifest_sha256']==sha(canon(d['manifest']))
        docs.append(d)
    docs.sort(key=lambda d:len(d['events']))
    assert [len(d['events']) for d in docs]==list(range(len(docs)))
    for a,b in zip(docs,docs[1:]):assert a['manifest']==b['manifest'] and a['events']==b['events'][:-1]
    doc=docs[-1];assert (LIVE/'journal/HEAD').read_text().strip()==sha(canon(doc))
    assert doc['manifest']['cases']==allocation['cases']
    cases=[];prior='0'*64
    for i,r in enumerate(doc['events']):
        assert r['index']==i and r['previous']==prior
        sealed(r,'sha256');prior=r['sha256'];ev=r['event']
        if ev['kind']=='consume':
            assert not cases or cases[-1]['status']=='completed'
            assert ev['binding']==allocation['cases'][len(cases)]
            cases.append({'ordinal':len(cases),'identity':ev['binding']['case_identity'],
                          'nonce':ev['nonce'],'status':'consumed','artifacts':{}})
        else:
            c=cases[-1];assert ev['nonce']==c['nonce'] and c['status']=='consumed'
            if ev['kind']=='artifact':
                assert ev['name'] not in c['artifacts'];c['artifacts'][ev['name']]={'size':ev['size'],'sha256':ev['sha256']}
            elif ev['kind']=='finish':c.update(status=ev['outcome'],elapsed_milliseconds=ev['elapsed_milliseconds'])
            else:raise AssertionError('Unexpected local engineering event')
    observed_draws=0;receipts=[];summaries=[]
    for c in cases:
        folder=LIVE/f"case{c['ordinal']}";actual={p.name for p in folder.iterdir()}
        assert actual==set(c['artifacts']),('unregistered partial artifact',actual-set(c['artifacts']))
        for name,m in c['artifacts'].items():
            data=(folder/name).read_bytes();assert len(data)==m['size'] and sha(data)==m['sha256']
        if c['status']=='completed':assert actual==set(doc['manifest']['required_artifacts'])
        if 'renderer.json' in actual:
            r=sealed(read(folder/'renderer.json'),'receipt_sha256')
            assert r['case_identity']==c['identity'] and r['normal_calls']==96
            assert len(r['row_receipts'])==6 and all([x['row'] for x in s['rows']]==list(range(16)) for s in r['row_receipts'])
            assert all(x['generator_call_arguments']==[100.,1.,65536] for s in r['row_receipts'] for x in s['rows'])
            assert r['engineering_start']['nonce']==c['nonce'];observed_draws+=6291456
        if 'maximum.json' in actual:
            u=sealed(read(folder/'maximum.json'),'receipt_sha256');assert u['case_identity']==c['identity']
            assert u['all_hypotheses_evaluated'] is True and u['visited_hypotheses']==2592 and u['scored_cells']==209952
            assert (u['maximum']['kind']=='empty')==(u['eligible_cells']==0)
            if c['ordinal']<4:receipts.append(u)
        entry={'ordinal':c['ordinal'],'status':c['status'],'artifact_count':len(actual),
               'artifact_bytes':sum(m['size'] for m in c['artifacts'].values())}
        if 'engineering_gate.json' in actual and c['ordinal']>=4:
            p=sealed(read(folder/'physical.json'),'result_sha256');g=sealed(read(folder/'engineering_gate.json'),'result_sha256')
            ret=sealed(p['retention'],'result_sha256');assert ret['case_identity']==c['identity'] and ret['complete'] and p['complete']
            rows=ret['retained']['on'];dec={x['record_id']:x for x in p['decisions']}
            assert len(dec)==len(rows)==len(p['decisions'])
            for r in rows:
                sealed(r,'record_id');rank=r['rank'];assert rank['reference_denominator']==5 and rank['inclusive_p']>=.2 and rank['meets_rank_cut'] is False
                d=dec[r['record_id']];assert not d['diagnostic_final'] and not d['scientific_candidate'] and not d['meets_diagnostic_rank_cut']
                assert d['passes_evaluated_physical_vetoes']==(d['physical_disposition']=='pending_receiver_alias_evaluation')
            survivors={rid for rid,d in dec.items() if d['passes_evaluated_physical_vetoes']}
            assoc={a['record_id'] for a in g['association'] if a['engineering_survivor'] and a['associated']}
            assert survivors=={a['record_id'] for a in g['association'] if a['engineering_survivor']}
            assert g['counts']['physical_survivors']==len(survivors) and g['counts']['associated_physical_survivors']==len(assoc)
            expected=bool(assoc) if plans[c['ordinal']]['case']['spec']['kind']=='on_signal' else not survivors
            assert g['engineering_gate_pass']==expected and not g['calibrated_rank_gate_pass']
            assert g['physical_report_sha256']==p['result_sha256'];entry.update(engineering_gate_pass=expected,counts=g['counts'])
        summaries.append(entry)
    if (LIVE/'threshold.json').exists():
        t=sealed(read(LIVE/'threshold.json'),'threshold_receipt_sha256')
        assert len(receipts)==4 and t['reference_records']==receipts
        values=[r['maximum']['value'] for r in receipts if r['maximum']['kind']=='finite']
        assert t['operational_threshold']==max([10.,*values])
        assert t['reference_denominator']==5 and t['reference_bundle']['reference_count']==4 and not t['calibrated_1_percent_test']
    resultfile=LIVE/('result.json' if (LIVE/'result.json').exists() else 'error.json');result=read(resultfile)
    if resultfile.name=='result.json':assert len(cases)==8 and result['new_gaussian_values']==observed_draws
    else:assert result['all_eight_allocation_remains_spent'] and not result['retry_authorized']
    rawbytes=sum(p.stat().st_size for p in LIVE.rglob('*') if p.is_file())
    journalbytes=sum(p.stat().st_size for p in (LIVE/'journal').rglob('*') if p.is_file())
    report={'schema':'radio-native-chain-independent-postflight-v1','status':'RETAINED_BYTE_STATE_AUDIT_PASS',
            'experiment_status':result['status'],'cases':summaries,'journal_versions':len(docs),'journal_events':len(doc['events']),
            'original_journal_history_bytes':journalbytes,'uncompressed_live_bytes':rawbytes,
            'completed_render_gaussian_values_verified':observed_draws,'all_eight_reserved_identities_spent':True,
            'unentered_case_ordinals':[i for i in range(8) if i>=len(cases)],
            'new_random_values_in_audit':0,'new_scores_computed':0,'physical_algorithm_rerun':False,
            'audit_does_not_establish_gate_pass_or_resource_qualification':True,
            'ledger_byte_cap_met':journalbytes<=8*1024**2,'whole_evidence_byte_cap_met':rawbytes<=208*1024**2}
    output=BASE/'postflight.json';assert not output.exists();output.write_bytes(canon(report));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
