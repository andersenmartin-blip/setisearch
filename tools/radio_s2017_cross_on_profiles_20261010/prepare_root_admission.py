#!/usr/bin/env python3
"""Root-only, one-time metadata admission; opaque hashes, never science arrays."""
from profile_contract import *
from prepare_scope import metadata_geometry
import zipfile

ROOT = Path('/workspace/scratch/a8d1e29996d0')
OWNER = Path('/workspace/scratch/5bf3860dacd6')
PROJECT = ROOT / 'setisearch_fullpower'
STAGE = PROJECT / 'results' / FAMILY
PRIVATE = ROOT / 'seti_fullpower_work'
PREPARATION_CUSHION = 134217728


def main():
    start = time.process_time()
    timestamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    require(STAGE.is_dir() and not (STAGE/'ROOT_ADMISSION.json').exists()
        and not (STAGE/'PROFILE_STARTED_ONCE.json').exists()
        and not (STAGE/'measurement').exists()
        and not (PROJECT/'tools'/FAMILY/'SCOPE_PREPARATION_STARTED.json').exists(),
        'New fixed-profile family must remain ungenerated and unattempted')
    proof_list_pin = pin(STAGE/'proofs/PROSPECTIVE_REVIEW_INPUTS.json')
    proof_list = pinned_json(proof_list_pin)
    require(proof_list['status']=='PASS_FINAL_SOURCE_AND_SYNTHETIC_FIXTURES_BEFORE_REAL_PROFILES',
        'Actual final source and toy reviews required')
    proofs = proof_list['proof_pins']
    for item in proofs:
        verify_pin(item)
    previous_pin = pin(PROJECT/'results'/MATCH_FAMILY/'ROOT_ADMISSION.json')
    previous = pinned_json(previous_pin)
    require(previous['all_numeric_and_QA_processes_closed'] is True
        and previous['durable_RAW_verified'] is True
        and previous['durable_RESULTS_verified'] is True, 'Original source admission differs')
    proofs += [previous_pin]
    for item in previous['durability_proofs']:
        require(item['verified'] is True, 'Original durable proof is incomplete')
        verify_pin(item['pin'])
        proofs.append(item['pin'])
    inv = metadata_inventory(PROJECT, OWNER)
    geometry_sha = metadata_geometry(inv['members'],inv['source'],inv['old_geometries'])
    closure_scope = {'owner_kernel_guard_paths':inv['owner_kernel_guard_paths'],
        'owner_scientific_command_paths': inv['owner_scientific_command_paths']+[
            'tools/'+MATCH_FAMILY+'/match_saved.py',
            'tools/'+FAMILY+'/profile_saved.py']}
    handles = acquire_owner_guards(closure_scope)
    try:
        verify_no_live_owner_processes(closure_scope)
        for item in previous['original_execution_and_QA_pins']:
            verify_pin(item)
        saved_pin = pin(PROJECT/'results'/MATCH_FAMILY/'DELIVERY_SAVE_RECEIPT.json')
        saved = pinned_json(saved_pin)
        report_name = 'SETI_S2017_CROSS_ON_RESULTAT_2026-10-10.md'
        bundle_name = 'SETI_S2017_CROSS_ON_2026-10-10.zip'
        matching_execution = pinned_json(inv['matching_execution_pin'])
        require(saved['status']=='PASS_TWO_NEW_DELIVERABLES_SAVED_AND_LOCAL_IDENTITIES_APPLIED'
            and len(saved['items'])==2
            and [x['filename'] for x in saved['items']]==[report_name,bundle_name]
            and saved['public_freeze_commit']==matching_execution['public_freeze_commit']
            and all(x['status']=='succeeded' and x['local_metadata_applied'] is True for x in saved['items']),
            'Matching deliverable save is incomplete')
        report_pin = pin(PROJECT/'results'/MATCH_FAMILY/report_name,
            'ba2162a86bd7a7c65e075b28346371980aa8ad2f02f414cac93e4dea428f2401')
        integrity_pin = pin(PRIVATE/'SETI_S2017_CROSS_ON_2026-10-10.INTEGRITY.json')
        integrity = pinned_json(integrity_pin)
        require(integrity['status']=='PASS_COMPLETE_PACKAGE_CRC_ALL_MEMBER_SHA_AND_SOURCE_END_PINS'
            and integrity['source_end_readback_exact'] is True
            and integrity['science_reexecuted'] is False, 'Matching local package integrity differs')
        bundle_pin = pin(PRIVATE/'SETI_S2017_CROSS_ON_2026-10-10.zip',integrity['archive_sha256'])
        require(bundle_pin['bytes']==integrity['archive_bytes'], 'Saved matching bundle size differs')
        require(any('library' in name.lower() for name in os.listxattr(bundle_pin['path'])),
            'Matching saved local file identity is absent')
        require(any('library' in name.lower() for name in os.listxattr(report_pin['path'])),
            'Matching saved report identity is absent')
        with zipfile.ZipFile(bundle_pin['path']) as archive:
            report_members = [name for name in archive.namelist() if name.endswith('/'+report_name)]
            require(len(report_members)==1 and archive.read(report_members[0])==Path(report_pin['path']).read_bytes(),
                'Saved matching report is not byte-identical to the durable bundle member')
        proofs += [saved_pin,report_pin,integrity_pin,bundle_pin,proof_list_pin]
        checked, hits = [], []
        excluded = {PROJECT/'results'/name for name in (
            'radio_s2017_cross_on_20261010','radio_s2017_cross_on_recovery_20261010',MATCH_FAMILY,FAMILY)}
        pattern = re.compile(r'radio_s2017_cross_on_profiles|cross[ _-]?on.{0,80}(?:all.six|fixed.profile)|'
            r'(?:635|1905|11[,.]?430).{0,30}(?:triples|members|profiles)', re.I)
        for root in (OWNER/'analysis',PROJECT/'results'):
            for base, children, files in os.walk(root,followlinks=False):
                if Path(base) in excluded:
                    children[:] = []
                    continue
                children[:] = [name for name in children if not (Path(base)/name).is_symlink()]
                for name in files:
                    path = Path(base)/name
                    if path.suffix.lower() not in ('.json','.md','.txt') or not re.search(r'SCOPE|PLAN|REGISTRY|STATUS|NEXT',name,re.I):
                        continue
                    if path.is_symlink() or path.stat().st_size>262144:
                        continue
                    item = pin(path)
                    checked.append(item)
                    if pattern.search(path.read_text(errors='replace')):
                        hits.append(item)
        require(not hits,'Finite profile registry mention needs classification before admission')
        roots = [str(ROOT),str(OWNER)]
        observed = tree_size(roots)
        free = os.statvfs(STAGE)
        physical = free.f_bavail*free.f_frsize
        require(observed+OUTPUT_CAP+PREPARATION_CUSHION<=WORKSPACE_CAP
            and physical>=OUTPUT_CAP+PREPARATION_CUSHION,'Prospective12GiB profile admission fails')
        registry = {'status':'PASS_FINITE_METADATA_NO_OTHER_635_TRIPLE_ALL_SIX_PROFILE_PHASE',
            'created_utc':timestamp,'checked_metadata_file_pins':checked,'unclassified_profile_hits':hits,
            'excluded_closed_association_namespaces_and_unstarted_profile_namespace':sorted(str(x) for x in excluded),
            'seven_original171_owner_guards_readonly_exclusively_probed':len(handles)==7,
            'relevant_original171_matching_joined_profile_and_QA_commands_active':False,
            'distinct_native170_172_interior_work_may_remain_active':True,
            'old_profile_hypotheses':54,'old_unique_scan_geometries':312,
            'new_fixed_member_hypotheses':1905,'new_logical_scan_profiles':11430,
            'new_unique_scan_geometries':11369,'old_profile_geometry_overlap':0,
            'verified_ordered_geometry_sha256':geometry_sha,
            'verified_selected_members_sha256':inv['selection_sha256'],
            'source_values_or_scientific_arrays_opened':False,
            'finite_scan_limits':'JSON/MD/TXT names SCOPE|PLAN|REGISTRY|STATUS|NEXT;262144B per file;OWNER analysis and OUR results. Not a global registry.'}
        save_new(STAGE/'ROOT_FRESH_DUPLICATE_CHECK.json',registry)
        resources = {'status':'PASS_PROSPECTIVE_12GiB_PROFILE_STORAGE_ADMISSION','created_utc':timestamp,
            'shared_workspace_roots':roots,'observed_tree_bytes':observed,'workspace_cap_bytes':WORKSPACE_CAP,
            'output_reservation_bytes':OUTPUT_CAP,'extra_preparation_cushion_bytes':PREPARATION_CUSHION,
            'physical_free_bytes':physical,'headroom_after_output_reservation_bytes':WORKSPACE_CAP-observed-OUTPUT_CAP,
            'CPU_cap_s':CPU_CAP,'wall_cap_s':WALL_CAP,'memory_cap_bytes':MEMORY_CAP,
            'source_HTTP_requests':0,'cost_DKK':0,'scientific_arrays_opened':False}
        save_new(STAGE/'ROOT_RESOURCE_ADMISSION.json',resources)
        proofs += [pin(STAGE/'ROOT_FRESH_DUPLICATE_CHECK.json'),pin(STAGE/'ROOT_RESOURCE_ADMISSION.json')]
        for item in proofs+inv['pins']:
            verify_pin(item)
        verify_no_live_owner_processes(closure_scope)
        admission = {'schema':'SETI_S2017_CROSS_ON_PROFILES_ROOT_ADMISSION_V1',
            'status':'PASS_CLOSED_DURABLE_MATCHED_SOURCE_NO_DUPLICATE_PROFILE_PHASE','created_utc':timestamp,
            'source_root':str(OWNER),'shared_workspace_roots':roots,
            'all_original171_numeric_QA_processes_closed':True,
            'matching_numeric_and_output_QA_processes_closed':True,
            'durable_source_RAW_and_RESULTS_verified':True,'durable_matching_RESULTS_verified':True,
            'fresh_duplicate_registry_no_profile_phase':True,'profiles_not_previously_measured':True,
            'original171_closure_only_not_global_idle':True,'selected_triples':635,'selected_members':1905,
            'logical_scan_profiles':11430,'unique_geometries':11369,'old_saved_geometries':312,
            'verified_ordered_geometry_sha256':geometry_sha,
            'verified_selected_members_sha256':inv['selection_sha256'],
            'proof_pins':proofs,'metadata_inventory_pins':inv['pins'],
            'scientific_arrays_opened':False,'source_HTTP_requests':0,'cost_DKK':0}
        save_new(STAGE/'ROOT_ADMISSION.json',admission)
        print(json.dumps({'status':admission['status'],'admission_pin':pin(STAGE/'ROOT_ADMISSION.json'),
            'metadata_files_checked':len(checked),'shared_tree_bytes':observed,
            'headroom_bytes':WORKSPACE_CAP-observed-OUTPUT_CAP,'process_CPU_seconds':time.process_time()-start}))
    finally:
        for handle in handles:
            handle.close()


if __name__ == '__main__':
    main()
