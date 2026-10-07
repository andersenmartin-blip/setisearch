"""Read retained metadata at one Git checkpoint; never execute a project recipe.

Q prepares the period review, not a scientific certificate. Only the paths in
INPUT_MANIFEST.json are read. Git object reads are administrative preservation.
"""
import hashlib
import json
from pathlib import Path
import subprocess

CHECKPOINT = '5bf89ac846329366429f93823a3777fef8ffb3a9'
META = 'results_radio_hd189733_metadata_preparation_20261002a/'
K = 'results_radio_runtime_recovery_20261006k/'
M = 'results_radio_mapping_kernel_source_20261006m/actual/'
PANEL = 'results_radio_hd189733_panel_2026-09-28/'
GEOMETRY = 'results_radio_hd189733_geometry_2026-09-27/'
SELECTED = [
    ('receiver-v2', 'RADIO_RECEIVER_RUNNER_V2_2026-10-04_RESULT.md', 30, 4, 'SYNTHETIC_PROCESS_QUALIFIED'),
    ('contents-a', 'RADIO_CONTENTS_CAS_EDGE_A_2026-10-04_RESULT.md', 180, 4, 'CLOSED_FAILED'),
    ('contents-b', 'RADIO_CONTENTS_CAS_EDGE_B_2026-10-04_RESULT.md', 180, 4, 'CLOSED_FAILED'),
    ('contents-c', 'RADIO_CONTENTS_CAS_EDGE_C_2026-10-04_RESULT.md', 180, 4, 'CLOSED_REFUSED_BEFORE_ADMISSION'),
    ('dynamic-git', 'RADIO_DYNAMIC_NETWORK_POLICY_2026-10-04_RESULT.md', 40, 4, 'SELECTED_TRANSPORT_OBSERVATION_VERIFIED'),
    ('hosted-cas', 'RADIO_HOSTED_CAS_CONTROL_2026-10-04_RESULT.md', 300, 20, 'CLOSED_FAILED'),
    ('capture-a', 'RADIO_RUNTIME_METADATA_CAPTURE_2026-10-04_RESULT.md', 60, 8, 'CLOSED_FAILED'),
    ('capture-b', 'RADIO_RUNTIME_METADATA_CAPTURE_2026-10-04B_RESULT.md', 60, 8, 'OBSERVED_METADATA_ONLY'),
    ('bootstrap-a', 'RADIO_RUNTIME_PACKAGE_BOOTSTRAP_2026-10-05A_RESULT.md', 300, 1536, 'CLOSED_FAILED'),
    ('bootstrap-b', 'RADIO_RUNTIME_PACKAGE_BOOTSTRAP_2026-10-05B_RESULT.md', 300, 1536, 'CLOSED_FAILED'),
    ('package-source', 'RADIO_HOSTED_PACKAGE_SOURCE_2026-10-05_RESULT.md', 480, 512, 'EXACT_THREE_ORIGINAL_ARCHIVES_VERIFIED'),
    ('materialization-c', 'RADIO_OFFLINE_RUNTIME_MATERIALIZATION_2026-10-05C_RESULT.md', 300, 1536, 'FAILED_CLOSED'),
    ('capture-d', 'RADIO_RUNTIME_METADATA_CAPTURE_2026-10-05D_RESULT.md', 180, 64, 'FAILED_CLOSED'),
    ('capture-e', 'RADIO_RUNTIME_METADATA_CAPTURE_2026-10-05E_RESULT.md', 180, 64, 'OBSERVED_METADATA_ONLY'),
    ('process-io-f', 'RADIO_PROC_IO_CONTROL_2026-10-06F_RESULT.md', 30, 16, 'OBSERVED_KERNEL_IO_ONLY_PENDING_INTEGRATION'),
    ('codec16-g', 'RADIO_CODEC16_2026-10-06G_RESULT.md', 120, 192, 'CONTROLLED_CODEC16_PARTIAL_HANDOFF_OBSERVED'),
]
EXTRA = [
    'PROJECT_STATUS.md', 'PROJECT_DIRECTION.md', 'RADIO_TWO_WEEK_PLAN_2026-09-26.md',
    'config/radio_hd1461_source_preparation_20260926.json',
    'config/radio_hd189733_source_preparation_20260927.json',
    'config/radio_whole_cadence_null_proposal_20260928.json',
    META+'admission_matrix.json', META+'prospective_wrapper.json', META+'sample-validation.json',
    META+'provenance_rebinding.json', META+'output_pins.json',
    K+'RESULT.json', K+'UNRECOVERED.json', M+'FAILURE.json',
    PANEL+'postflight.json', PANEL+'diagnosis01/result.json',
    GEOMETRY+'window_geometry.json', GEOMETRY+'window_identity_contract_v2.json',
    'results_radio_alternate_2026-09-27/source_qualification.json',
]


class Refusal(ValueError): pass


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out: raise Refusal('duplicate JSON key')
            out[key] = value
        return out
    def invalid(value): raise Refusal('nonfinite JSON value')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def pin(raw):
    return {'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest(),
            'blob_sha':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}


def git_bytes(root, path):
    if path.startswith('/') or '..' in Path(path).parts or '\0' in path:
        raise Refusal('relative retained metadata path required')
    result = subprocess.run(['git','cat-file','blob',CHECKPOINT+':'+path], cwd=root,
                            capture_output=True, timeout=15, check=True)
    if len(result.stdout)>1024**2: raise Refusal('metadata body cap')
    return result.stdout


def inventory(root):
    names = subprocess.run(['git','ls-tree','--name-only',CHECKPOINT], cwd=root,
                           capture_output=True, text=True, check=True, timeout=15).stdout.splitlines()
    reports = [n for n in names if n.startswith('RADIO_') and n.endswith('.md')]
    paths = sorted(set(reports+EXTRA))
    sources = {p:git_bytes(root,p) for p in paths}
    manifest = {'schema':'radio-Q-retained-review-inputs-v1','checkpoint':CHECKPOINT,
                'files':{p:pin(raw) for p,raw in sources.items()}, 'root_radio_report_count':len(reports),
                'payload_or_runtime_bodies_read':False, 'reported_outcome_authentication_only':True}
    return manifest, sources


def validate_sources(manifest, sources):
    if manifest['checkpoint'] != CHECKPOINT or set(manifest['files']) != set(sources):
        raise Refusal('exact checkpoint and complete input set required')
    for path, expected in manifest['files'].items():
        if type(sources[path]) is not bytes or pin(sources[path]) != expected:
            raise Refusal('retained input drift: '+path)


def reconcile(rows):
    if len(rows)!=16 or len({r['scope'] for r in rows})!=16:
        raise Refusal('sixteen distinct selected reservations required')
    expected = {scope:(report,seconds,mib,status) for scope,report,seconds,mib,status in SELECTED}
    for row in rows:
        values=(row['report'],row['reserved_wall_seconds'],row['reserved_artifact_mib'],row['reported_disposition'])
        if row['scope'] not in expected or values!=expected[row['scope']]:
            raise Refusal('original selected reservation changed')
        if any(type(row[k]) is not int for k in ('reserved_wall_seconds','reserved_artifact_mib')):
            raise Refusal('exact integer resource units required')
    return {'scope_count':16,'reserved_wall_seconds':sum(r['reserved_wall_seconds'] for r in rows),
            'reserved_artifact_mib':sum(r['reserved_artifact_mib'] for r in rows),
            'reserved_artifact_bytes':sum(r['reserved_artifact_mib'] for r in rows)*1024**2,
            'measurement':False,'complete_project_history':False,'refund_or_rearm':False}


def review(manifest, sources):
    validate_sources(manifest,sources)
    def load(p): return strict_json(sources[p])
    hd=load('config/radio_hd189733_source_preparation_20260927.json')
    held=load('config/radio_hd1461_source_preparation_20260926.json')
    matrix=load(META+'admission_matrix.json'); wrapper=load(META+'prospective_wrapper.json')
    proposal=load('config/radio_whole_cadence_null_proposal_20260928.json')
    k=load(K+'RESULT.json'); missing=load(K+'UNRECOVERED.json'); m=load(M+'FAILURE.json')
    panel=load(PANEL+'postflight.json'); geometry=load(GEOMETRY+'window_geometry.json')
    if hd['stage']!='preparation-only-no-spectral-access' or hd['windows']!=[] or hd['hdf5_runtime'] is not None:
        raise Refusal('original source preparation must remain blocked')
    if (hd['gates']['codec_integration']['status']!='not-qualified-for-this-source-contract'
            or hd['gates']['prospective_protocol']['status']!='not-frozen-for-new-source'):
        raise Refusal('original pending codec/protocol gates must remain')
    if held['stage']!='preparation-only-no-spectral-access' or held['gates']['pointing']['status']!='unresolved':
        raise Refusal('HD1461 unresolved pointing hold must remain')
    for document in (matrix,wrapper):
        if document['status']!='PROSPECTIVE_TELESCOPE_ACCESS_BLOCKED' or document['stop_date']!='2026-10-09':
            raise Refusal('original source admission boundary changed')
        if len(document['authority'])!=6 or any(v is not False for v in document['authority'].values()):
            raise Refusal('six exact false authority flags required')
    requirements=matrix['requirements']
    if len(requirements)!=11 or any(r['status']!='missing-not-admitted' for r in requirements):
        raise Refusal('all eleven actual source-admission obligations remain missing')
    if proposal['status']!='PROPOSED_NOT_ACTIVATED' or proposal['primary']!='neighbor9' or len(proposal['cases'])!=151:
        raise Refusal('unchanged inactive 127/24 proposal required')
    if proposal['new_values_generated'] is not False or proposal['telescope_access_authorized'] is not False:
        raise Refusal('proposal cannot supply generated values or telescope authority')
    for case in proposal['cases']:
        if case['executed'] is not False or case['budget_charged'] is not False:
            raise Refusal('proposed case may not become executed or charged')
    if len({c['identity'] for c in proposal['cases']})!=151:
        raise Refusal('151 unique proposed identities required')
    if k['runtime_qualified'] is not False or k['copied_files']+k['missing_or_mismatched']!=k['expected_files']:
        raise Refusal('K partial recovery boundary differs')
    if len(missing['members'])!=k['missing_or_mismatched'] or len({x['path'] for x in missing['members']})!=136:
        raise Refusal('136 exact distinct missing members required')
    if m['errno']!=13 or m['status']!='FAILED_CLOSED_NO_RETRY':
        raise Refusal('M access refusal must remain closed')
    if panel['status']!='RECONCILED_FAILED_CALIBRATION_AND_CLOSED_DIAGNOSIS' or panel['evaluation_runs_executed']!=0:
        raise Refusal('failed original calibration/evaluation disposition differs')
    rows=[dict(scope=s,report=p,reserved_wall_seconds=t,reserved_artifact_mib=b,reported_disposition=d)
          for s,p,t,b,d in SELECTED]
    for row in rows:
        if row['reported_disposition'] not in sources[row['report']].decode():
            raise Refusal('reported disposition not present in original report: '+row['scope'])
    resources=reconcile(rows)
    if (resources['reserved_wall_seconds'],resources['reserved_artifact_mib'])!=(2920,5512):
        raise Refusal('selected reservation subtotal mismatch')
    recovery_groups={name:{'files':group['files'],'original_expected_bytes':group['original_expected_bytes']}
                     for name,group in missing['groups'].items()}
    summary={'schema':'radio-Q-period-closure-preparation-v1','as_of':'2026-10-07',
      'checkpoint':CHECKPOINT,'final_period_consolidation':False,'period_stop':'2026-10-09',
      'scientific_pilot_completed':False,'new_telescope_search_result':False,
      'new_spectra_opened_in_this_audit':False,'new_trial_or_native_allocation':False,
      'selected_target':'HD189733/HIP98505','cadence':85030,'primary':'neighbor9',
      'source_scans':[{'label':s['label'],'url':s['url']} for s in hd['scans']],
      'source_preparation_unchanged_pin':manifest['files']['config/radio_hd189733_source_preparation_20260927.json'],
      'source_inventory_sha256':hd['source_inventory_sha256'],
      'admission_obligations':requirements,'authority':dict(matrix['authority']),
      'failed_calibration':{k:panel[k] for k in ('status','calibration_realizations_spent','diagnosis_attempts_spent_closed',
                       'finite_conditional_samples','empty_conditional_samples','evaluation_runs_executed','evaluation_values_opened')},
      'inactive_scientific_proposal':{'references':127,'evaluations':24,'identities':151,'values_generated':False},
      'source_windows':[{'name':w['name'],'archive_interval_half_open':w['archive_interval'],
                        'chunk':w['archive_chunk_index'],'native_low_hz':w['native_frequency_low_hz'],
                        'native_high_hz':w['native_frequency_high_hz']} for w in geometry['windows']],
      'runtime_recovery':{'copied_files':k['copied_files'],'copied_bytes':k['copied_original_bytes'],
                         'missing_files':len(missing['members']),'missing_original_bytes':missing['original_expected_bytes'],
                         'runtime_qualified':False,'missing_groups':recovery_groups},
      'observer_access':{'status':m['status'],'errno':m['errno'],'reason':m['reason'],'retry':False},
      'selected_reservations':resources,
      'test_counts_summed_into_scientific_evidence':False,'all_project_resource_total':None,
      'limits':['reported historical outcomes authenticated as retained bytes; no live-state recertification',
                'root report inventory is an index, not an independent reanalysis of every underlying archive',
                'original inode custody, private spend continuity and hidden provider resource cost not reconstructed'],
      'next_action':'Refresh the latest branch on 9 October and consolidate the period; no plan extension.'}
    return summary,{'schema':'radio-Q-selected-reservation-reconciliation-v1','checkpoint':CHECKPOINT,
                    'rows':rows,'selected_subtotal':resources,
                    'separate_guard_controls':{'count':5,'reserved_wall_seconds_each':30,'process_as_mib_each':512,
                       'reported_selected_observed_seconds':3.742786908,'artifact_mib':None},
                    'unallocated_H_proposal':{'wall_seconds':600,'cpu_seconds':540,'artifact_mib':448,
                                             'explicit_parent_read_gib':4,'opaque_child_read_gib':1,'allocated':False},
                    'excluded_history':['earlier Sep26-Oct3 acquisition/transport/native control reservations',
                      '54 old connector-call reservations','development/test/readback/preservation administration',
                      'implicit loader, hosted provider and unmeasured external operations'],
                    'whole_period_total_qualified':False}


if __name__=='__main__':
    import sys
    root=Path(__file__).resolve().parent.parent; out=Path(sys.argv[1])
    out.mkdir(exist_ok=False)
    manifest,sources=inventory(root); summary,resources=review(manifest,sources)
    for name,value in [('INPUT_MANIFEST.json',manifest),('SUMMARY.json',summary),('RESERVATIONS.json',resources)]:
        with (out/name).open('xb') as f:f.write(canonical(value))
    print(json.dumps({'inputs':len(sources),'input_bytes':sum(len(r) for r in sources.values()),
                      'report_count':manifest['root_radio_report_count'],'status':'REVIEWED_BLOCKED_PREPARATION'}))
