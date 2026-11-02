#!/usr/bin/env python3
"""Verify extension transfer boundaries without opening any science payload."""
import csv
import json
import tempfile
from pathlib import Path
import acquire_main as acq

P = Path(__file__).resolve().parent
ROOT = P.parent


def main():
    checks = []

    def check(name, condition):
        assert condition, name
        checks.append({'case': name, 'passed': True})

    def rejects(name, callback):
        try:
            callback()
        except (ValueError, FileNotFoundError):
            checks.append({'case': name, 'passed': True})
        else:
            raise AssertionError(name)

    plan = acq.load_plan()
    selected = set(plan['selected_ids'])
    check('Exact selection and complete job coverage', len(selected) == plan['objects'])
    check('Extension and combined object caps', 0 < len(selected) <= 104 and len(selected) + 188 <= 500)
    with (ROOT/'extension_feasibility/OBJECT_FEASIBILITY.csv').open() as f:
        eligible = {r['object_id'] for r in csv.DictReader(f) if r['status'] == 'MEETS_TEMPORAL_QUALITY_NECESSARY_CONDITION'}
    check('All selected identities met frozen metadata prerequisite', selected <= eligible)
    initial = set()
    for name in ('DEVELOPMENT_SELECTION.csv', 'MAIN_METADATA_CANDIDATES_UNMATCHED.csv'):
        with (ROOT/'access_pilot'/name).open() as f:
            initial.update(r['r:diaObjectId'] for r in csv.DictReader(f))
    check('No overlap with any original 433 exact identities', len(initial) == 433 and not selected.intersection(initial))
    original = json.loads((ROOT/'main_acquisition/PLAN.json').read_text())
    check('Transfer limits unchanged', plan['limits'] == original['limits'])
    for stream in ('sources', 'fp'):
        prior = next(j for j in original['jobs'] if j['job_id'].startswith(stream+'_'))
        jobs = [j for j in plan['jobs'] if j['job_id'].startswith(stream+'_')]
        check(stream+' fields and endpoints unchanged', all(j['endpoint'] == prior['endpoint'] and j['payload']['columns'] == prior['payload']['columns'] and j['payload']['output-format'] == 'json' for j in jobs))
    oid = plan['selected_ids'][0]
    check('Observed 18-digit identity retained exactly', acq.exact_id(oid) == oid)
    for name, value in [('float',float(oid)),('native integer',int(oid)),('scientific notation','3.137e17'),('zero','0'),('negative','-1'),('signed64 overflow',str(2**63))]:
        rejects('Reject '+name+' object identity', lambda value=value: acq.exact_id(value))
    source = {'r:diaObjectId':int(oid),'r:diaSourceId':int(oid)+1,'r:visit':123456}
    rows = acq.validate_rows(json.dumps([source]).encode(),selected,'https://api.lsst.fink-portal.org/api/v1/sources')
    check('JSON integer identity parsed without floating-point loss', rows[0]['r:diaObjectId'] == oid and rows[0]['r:diaSourceId'] == str(int(oid)+1))
    rejects('Reject foreign object in returned rows',lambda: acq.validate_rows(json.dumps([source]).encode(),{'1'},'/sources'))
    source['r:diaObjectId'] = float(oid)
    rejects('Reject JSON floating-point object identity',lambda: acq.validate_rows(json.dumps([source]).encode(),selected,'/sources'))
    budget = acq.Budget(80,20)
    check('Two simultaneous full-response reservations bounded', budget.reserve() and budget.reserve() and budget.reserved == 40)
    budget.close(5,False); budget.close(0,True)
    check('Unknown transfer charged at full reserved limit', budget.charged == 25 and budget.reserved == 0)
    check('Insufficient remaining reservation rejected', budget.reserve() and budget.reserve() and not budget.reserve())
    saved = acq.P
    with tempfile.TemporaryDirectory() as temporary:
        acq.P = Path(temporary)
        try:
            rejects('Missing release prevents entry to acquisition',lambda: acq.validate_release(plan))
        finally:
            acq.P = saved
    preserved = json.loads((P/'CODE_ADAPTATIONS.json').read_text())['preserved_source_hashes']
    check('Original selection/results and scientific method unchanged', all(acq.sha(ROOT/name) == digest for name,digest in preserved.items()))
    record = {'status':'PASS_OFFLINE_EXTENSION_GUARDS','checks':checks,'network_calls':0,'extension_flux_reads':0,
              'selection_sha256':plan['selection_sha256'],'plan_sha256':acq.sha(P/'PLAN.json'),
              'script_sha256':acq.sha(P/'acquire_main.py'),'guard_script_sha256':acq.sha(Path(__file__))}
    (P/'OFFLINE_GUARDS.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))


if __name__ == '__main__':
    main()
