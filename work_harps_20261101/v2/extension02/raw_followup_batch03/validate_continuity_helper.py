"""Isolated synthetic continuity validation; never writes live science/status files."""
from pathlib import Path
import csv, hashlib, io, json, shutil, subprocess, sys, tempfile
OUT = Path(__file__).resolve().parent
REPO = OUT.parents[3]
BASE_REL = Path('work_harps_20261101')
BATCH_REL = OUT.relative_to(REPO)

def read(path): return json.loads(path.read_text())
def rows(path):
    with path.open(newline='') as handle: return list(csv.DictReader(handle))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write_json(path, value): path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, indent=2)+'\n')
def write_csv(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as handle:
        writer=csv.DictWriter(handle, fieldnames=list(dict.fromkeys(k for r in records for k in r)))
        writer.writeheader(); writer.writerows(records)

def main():
    plan = read(OUT/'PLAN.json'); old_summary=read(OUT/'inputs/CURRENT_SUMMARY.json')
    state = read(OUT/'inputs/CONTINUATION_STATE.json'); n=plan['selection_rule']['max_unique_exposures']
    queue=state['pending_raw_queue']['exposure_queue'][:n]; selected_ids=[k for e in queue for k in e['pending_ids']]
    main_rows=rows(REPO/BASE_REL/'v2/extension02/MAIN100.csv'); main_by={r['dp_id']:r for r in main_rows}
    hit_by={r['candidate_id']:r for r in rows(REPO/BASE_REL/'v2/extension02/production/V2_HITS.csv')}
    tests=[]
    with tempfile.TemporaryDirectory(prefix='seti_batch03_continuity_') as temp:
        root=Path(temp); out=root/BATCH_REL; out.mkdir(parents=True)
        required={Path(rel) for rel in state['source_hashes']}
        required.update(BASE_REL/'v2'/rel for rel in old_summary['source_hashes'])
        required.update([BASE_REL/'v2/extension02/MAIN100.csv',BASE_REL/'v2/extension02/production/V2_HITS.csv'])
        for rel in required:
            p=root/rel; p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/rel,p)
        shutil.copy2(OUT/'update_current.py',out/'update_current.py')
        shutil.copy2(OUT/'PLAN.json',out/'PLAN.json')
        shutil.copytree(OUT/'inputs',out/'inputs')
        # The fixture restores the predecessor regardless of subsequent live updates.
        v2=root/BASE_REL/'v2';current=v2/'extension02/raw_followup'
        for name in ['CURRENT_V2_ALL336_DISPOSITIONS.csv','CURRENT_SELECTED_EVENT_DISPOSITIONS.csv','CURRENT_SUMMARY.json']:
            shutil.copy2(out/'inputs'/name,current/name)
        shutil.copy2(out/'inputs/CURRENT_SUMMARY.json',v2/'CURRENT_STATUS.json')
        shutil.copy2(out/'inputs/CURRENT_V2_DISPOSITIONS.csv',v2/'CURRENT_V2_DISPOSITIONS.csv')
        selection=[]
        for key in selected_ids:
            h=hit_by[key]
            selection.append(dict(detector='V2',review_id=key,candidate_id=key,dp_id=h['dp_id'],target=h['canonical_target'],source_sha256=h['input_sha256']))
        write_csv(out/'SELECTED_EVENTS.csv',selection)
        write_csv(out/'SELECTED_EXPOSURES.csv',[main_by[r['dp_id']] for r in queue])
        (out/'figures').mkdir();(out/'figures/SYNTHETIC.png').write_bytes(b'SYNTHETIC_FIXTURE_NOT_A_SCIENTIFIC_IMAGE')
        mapping=dict(events=[dict(review_id=r['review_id'],mapping_supported=True,status='NATIVE_CONTEXT_EXTRACTED')for r in selection])
        write_json(out/'NATIVE_MAPPING.json',mapping)
        write_json(out/'independent_audit/SUMMARY.json',dict(status='PASS',source_hashes={'NATIVE_MAPPING.json':sha(out/'NATIVE_MAPPING.json')},scope='SYNTHETIC CONTINUITY FIXTURE ONLY'))
        write_csv(out/'ADOPTED_DISPOSITIONS.csv',[dict(candidate_id=r['review_id'],dp_id=r['dp_id'],code='U',evidence='Synthetic continuity fixture, not a scientific disposition.',all_covering_orders_mapping_verified=True,figure='figures/SYNTHETIC.png')for r in selection])
        write_json(out/'SUMMARY.json',dict(created_utc='2000-01-01T00:00:00+00:00',status='ROOT_ADOPTED_CONSERVATIVE_REVIEW',selected_events=len(selection),selected_exposures=len(queue),independent_numeric_audit='PASS',root_visual_review_complete=True,original_production_unchanged=True,adopted_counts={'U':len(selection)},scope='SYNTHETIC CONTINUITY FIXTURE ONLY'))
        freeze_paths=[out/'PLAN.json',out/'SELECTED_EVENTS.csv',out/'SELECTED_EXPOSURES.csv']+list((out/'inputs').glob('*'))
        write_json(out/'FOLLOWUP_FREEZE.json',dict(status='SYNTHETIC_TEST_FREEZE',source_hashes={str(p.relative_to(root/BASE_REL)):sha(p)for p in freeze_paths}))
        def run(*args, ok=True):
            result=subprocess.run([sys.executable,str(out/'update_current.py'),*args],capture_output=True,text=True)
            if ok and result.returncode:raise RuntimeError(result.stderr)
            if not ok:assert result.returncode!=0;return result
            return json.loads(result.stdout)
        protected=[current/'CURRENT_V2_ALL336_DISPOSITIONS.csv',current/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv',current/'CURRENT_SUMMARY.json',v2/'CURRENT_STATUS.json',v2/'CURRENT_V2_DISPOSITIONS.csv']
        before_hashes={str(p):sha(p)for p in protected}
        dry=run();assert dry['mode']=='DRY_RUN' and before_hashes=={str(p):sha(p)for p in protected};tests.append('default_dry_run_changes_no_current_tables')
        applied=run('--apply');assert applied['new_counts']=={'A':80,'O':13,'U':142,'M':7,'N':94};tests.append('115_synthetic_U_decisions_produce_expected_cohort_counts')
        assert applied['selected_rows']==248 and applied['pending_events']==94 and applied['pending_exposures']==37;tests.append('selected_master_and_pending_queue_counts')
        old_master=rows(out/'inputs/CURRENT_V2_DISPOSITIONS.csv');new_master=rows(v2/'CURRENT_V2_DISPOSITIONS.csv')
        assert [r for r in old_master if r['cohort']=='V2_first100']==[r for r in new_master if r['cohort']=='V2_first100'];tests.append('all_333_older_master_rows_exactly_preserved')
        old_selected=rows(out/'inputs/CURRENT_SELECTED_EVENT_DISPOSITIONS.csv');new_selected=rows(current/'CURRENT_SELECTED_EVENT_DISPOSITIONS.csv')
        assert all(all(new_selected[i][k]==v for k,v in r.items())for i,r in enumerate(old_selected));tests.append('all_133_prior_selected_fields_preserved')
        before=rows(out/'inputs/CURRENT_V2_ALL336_DISPOSITIONS.csv');after=rows(current/'CURRENT_V2_ALL336_DISPOSITIONS.csv')
        assert all(all(old[k]==new[k]for k in old)for old,new in zip(before,after)if old['candidate_id']not in selected_ids);tests.append('all_unselected_earlier_and_pending_fields_preserved')
        assert all(r['figure'].startswith('../raw_followup_batch03/')for r in new_selected[len(old_selected):]);tests.append('new_figures_resolve_under_correct_batch')
        updated_state=read(out/'CONTINUATION_STATE.json')
        for rel,h in updated_state['source_hashes'].items():assert sha(root/rel)==h,rel
        tests.append('all_new_and_inherited_source_hashes_valid_after_docs_render')
        outputs=[root/p for p in applied['output_files']];first_hashes={str(p):sha(p)for p in outputs}
        run('--apply');assert first_hashes=={str(p):sha(p)for p in outputs};tests.append('identical_reapplication_is_byte_identical')
        for p in protected:
            saved=p.read_bytes();p.write_bytes(saved+b'CONCURRENT_CHANGE\n');failed=run('--apply',ok=False)
            assert 'Current file differs' in failed.stderr;p.write_bytes(saved)
        tests.append('all_five_current_table_concurrency_conflicts_rejected')
        figure=out/'figures/SYNTHETIC.png';figure.unlink();failed=run(ok=False);assert 'Adopted figure is missing' in failed.stderr;tests.append('missing_adopted_figure_rejected')
        result=dict(status='PASS_SYNTHETIC_HELPER_VALIDATION_ONLY',tests=tests,tests_passed=len(tests),script_sha256=sha(OUT/'update_current.py'),validation_script_sha256=sha(Path(__file__)),synthetic_selected_events=len(selection),synthetic_selected_exposures=len(queue),synthetic_pending_events=applied['pending_events'],synthetic_pending_exposures=applied['pending_exposures'],synthetic_next_event=applied['next_event'],live_scientific_files_modified=False,limits='Only deterministic continuity behavior tested on copied predecessor metadata and deliberately synthetic decisions. This does not validate scientific classifications or replace actual final continuity audit.')
        write_json(OUT/'CONTINUITY_HELPER_VALIDATION.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
