"""Freeze new engineering identities, exact runtime and untouched fresh genesis."""
import json
from pathlib import Path
import time
from seti_repeater import whole_cadence_incremental_radio as r
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_runtime_radio import capture
from radio_incremental_journal_live import definitions, RECIPE, FREEZE

ROOT=Path(__file__).resolve().parents[1]


def main():
    started=time.monotonic();dest=ROOT/r.ROOT;dest.mkdir(exist_ok=True)
    witness={'schema':'radio-incremental-fixed-witness-v1',
        'purpose':'exact incremental journal and atomic artifact receipt qualification',
        'source_requests':0,'scientific_allocations':0,'telescope_values':0,'rng_constructions':0}
    recipe={'schema':'radio-incremental-engineering-recipe-v1','namespace':r.ROOT,
        'mode':'ENGINEERING_ONLY','prefixes':list(r.PREFIXES),
        'nonces':['00000000-0000-4000-8000-000000000092','00000000-0000-4000-8000-000000000093'],
        'witness':witness,'witness_sha256':r.sha(canonical(witness)),
        'limits':r.LIMITS,'ledger_cap_per_namespace':r.LEDGER_CAP,
        'artifact_cap_per_namespace':r.ARTIFACT_CAP,'four_live_branch_advances_maximum':True,
        'all_prior_scopes_closed_and_charges_preserved':True}
    (ROOT/RECIPE).write_bytes(canonical(recipe))
    inputs=[RECIPE,'RADIO_INCREMENTAL_JOURNAL_2026-09-29_SCOPE.md',
        'scripts/radio_incremental_journal_broker.js','tests/test_radio_incremental_journal.py',
        r.ROOT+'/preflight_tests.log','RADIO_JOURNAL_CAPACITY_2026-09-29_RESULT.md',
        'results_radio_journal_capacity_2026-09-29/result.json',
        'results_radio_gaussian_engineering_2026-09-29/allocation.json']
    frozen=capture(ROOT,inputs);raw=canonical(frozen);(ROOT/FREEZE).write_bytes(raw)
    manifests=[]
    for prefix in r.PREFIXES:
        path=ROOT/prefix;path.mkdir(exist_ok=False)
        genesis=definitions(r.sha(raw),recipe,prefix);history=r.initial(genesis)
        (path/'genesis.json').write_bytes(genesis);(path/'head.json').write_bytes(history.head)
        manifests.append({'prefix':prefix,'genesis_sha256':r.sha(genesis),
            'pointer_sha256':r.sha(history.head),'case_identity':history.document['manifest']['cases'][0]['case_identity']})
    result={'freeze_sha256':r.sha(raw),'code_files':len(frozen['code_sha256s']),
        'runtime_files':len(frozen['runtime_sha256s']),'input_files':len(frozen['input_sha256s']),
        'manifests':manifests,'elapsed_seconds':time.monotonic()-started,
        'scientific_execution_authorized':False}
    (dest/'preparation.json').write_bytes(canonical(result));print(json.dumps(result))


if __name__=='__main__':main()
