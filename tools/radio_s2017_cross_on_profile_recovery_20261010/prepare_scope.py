#!/usr/bin/env python3
"""Root-invoked ONCE, stdlib metadata/opaque hashes only; no science imports."""
import argparse
from profile_contract import *


def metadata_geometry(members,source,oldgeo):
    headers={x['label']:x['current_header']['data_attributes'] for x in source['sources']}
    anchor=min(x['tstart'] for x in headers.values());cache=set();unique=[]
    for member in members:
        m=member['original_member'];k=m['original_key'];base=(m['original_reference_frequency_hz']-FCH1)/DF
        for scan in SCANS:
            # Same separate IEEE arithmetic and nearest-even absolute rounding as frozen np.rint.
            centers=tuple(round(base+k['drift_hz_s']*((headers[scan]['tstart']-anchor)*86400
                +(row+.5)*TSAMP-k['reference_seconds_from_anchor'])/DF) for row in range(16))
            require(min(centers)-64>=C0 and max(centers)+64<C0+COUNT,'Metadata geometry outside retained source')
            key=(scan,k['width_channels'],centers)
            require(key not in oldgeo,'Old saved geometry would be repeated')
            if key not in cache:cache.add(key);unique.append([scan,k['width_channels'],list(centers)])
    require(len(unique)==11369,'Prospective11369 unique geometries differ')
    return hashlib.sha256(json.dumps(unique,separators=(',',':')).encode()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project-root',required=True);p.add_argument('--source-root',required=True)
    p.add_argument('--admission',required=True);p.add_argument('--expected-admission-sha256',required=True)
    p.add_argument('--root-go-metadata-only-after-source-review',action='store_true');args=p.parse_args()
    start=time.process_time();require(args.root_go_metadata_only_after_source_review,'Root metadata GO required')
    project,owner=Path(args.project_root),Path(args.source_root)
    require(project.is_absolute() and owner.is_absolute() and project.resolve()==project and owner.resolve()==owner,'Canonical roots required')
    tool=project/'tools'/FAMILY;stage=project/'results'/FAMILY
    require(tool.is_dir() and stage.is_dir() and not (stage/'PROFILE_STARTED_ONCE.json').exists()
        and not (stage/'measurement').exists(),'New family must be unattempted')
    save_new(tool/'SCOPE_PREPARATION_STARTED.json',{'family_id':FAMILY,'status':'STARTED_ONCE_METADATA_ONLY','admission_sha256':args.expected_admission_sha256})
    ap=pin(args.admission,args.expected_admission_sha256);admission=pinned_json(ap)
    require(admission['schema']=='SETI_S2017_CROSS_ON_PROFILES_ROOT_ADMISSION_V1'
        and admission['status']=='PASS_CLOSED_DURABLE_MATCHED_SOURCE_NO_DUPLICATE_PROFILE_PHASE'
        and admission['source_root']==str(owner)
        and all(admission.get(k) is True for k in ('all_original171_numeric_QA_processes_closed',
            'matching_numeric_and_output_QA_processes_closed','durable_source_RAW_and_RESULTS_verified',
            'durable_matching_RESULTS_verified','fresh_duplicate_registry_no_profile_phase','profiles_not_previously_measured')),
        'Actual closed/durable/nonduplicate admission required')
    for x in admission['proof_pins']:verify_pin(x)
    inv=metadata_inventory(project,owner)
    gsha=metadata_geometry(inv['members'],inv['source'],inv['old_geometries'])
    require(admission['verified_selected_members_sha256']==inv['selection_sha256']
        and admission['verified_ordered_geometry_sha256']==gsha,
        'Root admission selection/geometry metadata digests differ')
    deps=[pin(tool/name) for name in ('profile_saved.py','profile_contract.py','prepare_scope.py','METHOD.md','FIELD_SCHEMA.json',
        'run_frozen_once.py','isolated_h5_runtime_fixture.py')]
    scope={'schema':SCHEMA,'family_id':FAMILY,'script_sha256':deps[0]['sha256'],
        'source_root':str(owner),'admission_pin':ap,'pinned_metadata_files':inv['pins']+[ap]+admission['proof_pins'],
        'pinned_dependency_files':deps,'source_pin':inv['source_pin'],'normalization_pin':inv['normalization_pin'],
        'acquisition_pin':inv['acquisition_pin'],'compact_records':inv['compact_records'],
        'old_profile_pins':inv['old_profile_pins'],'matching_TOP_pin':inv['matching_TOP_pin'],
        'outside_native_profile_interval_proof_pin':inv['outside_native_profile_interval_proof_pin'],
        'outside_native_profile_cases':54,'outside_native_scan_profiles':324,
        'matching_execution_pin':inv['matching_execution_pin'],'matching_review_pin':inv['matching_review_pin'],
        'selected_members_sha256':inv['selection_sha256'],'ordered_geometry_sha256':gsha,
        'selected_triples':635,'selected_members':1905,'logical_scan_profiles':11430,'logical_time_rows':182880,
        'unique_geometries':11369,'new_geometry_aliases':61,'old_geometry_aliases':0,'old_saved_profiles':54,
        'old_saved_geometries':312,'excluded_match_id':EXCLUDED,
        'source_channel0':C0,'source_chunk_channel_count':COUNT,'profile_offset_interval_inclusive':[-64,64],
        'flank_rule':'abs(offset)>3;122channels','reference_rule':'each original ON first integration midpoint; no common-reference recentering',
        'profile_identity_fields':['family_id','match_id','member_scan_id','target_scan_id'],
        'scans':list(SCANS),'CPU_cap_s':CPU_CAP,'CPU_hard_limit_s':182,'wall_cap_s':WALL_CAP,'memory_cap_bytes':MEMORY_CAP,
        'output_reservation_bytes':OUTPUT_CAP,'shared_workspace_cap_bytes':WORKSPACE_CAP,
        'shared_workspace_roots':admission['shared_workspace_roots'],'owner_kernel_guard_paths':inv['owner_kernel_guard_paths'],
        'owner_scientific_command_paths':inv['owner_scientific_command_paths']+[
            'tools/'+MATCH_FAMILY+'/match_saved.py','tools/'+FAMILY+'/profile_saved.py'],
        'output_directory':str(stage/'measurement'),'attempt_marker_path':str(stage/'PROFILE_STARTED_ONCE.json'),
        'serial_gate_path':str(stage/'SERIAL_ACTIVE.flock'),'retry_resume_or_rerun_authorized':False,
        'new_HTTP_requests':0,'new_source_BODY_bytes':0,'cost_DKK':0,'limitations':LIMITATIONS}
    roots=[Path(x) for x in admission['shared_workspace_roots']]
    for path in (owner,tool,stage):require(any(path==r or r in path.parents for r in roots),'Declared disk roots omit stage/source')
    verify_no_live_owner_processes(scope)
    require(tree_size(admission['shared_workspace_roots'])+OUTPUT_CAP<=WORKSPACE_CAP,'Metadata shared12GiB/reservation gate fails')
    free=os.statvfs(stage);require(free.f_bavail*free.f_frsize>=OUTPUT_CAP,'Insufficient actual output disk headroom')
    for x in scope['pinned_metadata_files']+deps:verify_pin(x)
    require(pin(args.admission)==ap,'Admission changed during preparation')
    save_new(tool/'scope.json',scope)
    save_new(tool/'SCOPE_PREPARATION_RECEIPT.json',{'status':'COMPLETE_ONCE_METADATA_ONLY','family_id':FAMILY,
        'scope_pin':pin(tool/'scope.json'),'source_root':str(owner),'admission_pin':ap,
        'selected_members_sha256':inv['selection_sha256'],'ordered_geometry_sha256':gsha,
        'unique_geometries':11369,'science_arrays_opened':False,'scope_bytes':(tool/'scope.json').stat().st_size,
        'process_CPU_seconds':time.process_time()-start})
    print(json.dumps({'status':'COMPLETE_ONCE_METADATA_ONLY','scope_sha256':digest(tool/'scope.json'),'process_CPU_seconds':time.process_time()-start}))


if __name__=='__main__':main()
