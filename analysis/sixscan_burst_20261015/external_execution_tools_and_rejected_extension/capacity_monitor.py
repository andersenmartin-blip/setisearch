#!/usr/bin/env python3
"""Root-owned external file-size telemetry. Never launch or alter scientific jobs.

Samples regular-file logical sizes and small coordinator/scheduler metadata only.
A trace proves observations at sampled traversal times, not continuous hard caps.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import sys
import tempfile
import time

PHASES=('PRIMARY_CALIBRATION','PRIMARY_VALIDATION','QA','EXPOSED','QA_EXPOSED')
PLANNED={'PRIMARY_CALIBRATION':63,'PRIMARY_VALIDATION':142,'QA':205,'EXPOSED':9,'QA_EXPOSED':9}
TERMINAL={'ALL_FROZEN_PHASES_CLOSED','STOPPED_RETAINED_NO_RETRY'}
GAP_ALLOWANCE_S=2.0


def utc():return datetime.now(timezone.utc).isoformat()

def encoded(value):return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()


def sync_directory(path):
 descriptor=os.open(path,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(descriptor)
 finally:os.close(descriptor)


def atomic_json(path,value,exclusive=False):
 if exclusive:
  with path.open('xb') as stream:stream.write(encoded(value));stream.flush();os.fsync(stream.fileno())
 else:
  temporary=path.with_name(path.name+'.tmp')
  with temporary.open('wb') as stream:stream.write(encoded(value));stream.flush();os.fsync(stream.fileno())
  temporary.replace(path)
 sync_directory(path.parent)


def relative(path,workspace):
 try:return str(path.relative_to(workspace)) or '.'
 except ValueError:return str(path)


def count_regular_bytes(root,workspace):
 """Count logical st_size, skip symlinks; tolerate atomic rename/deletion races."""
 total=files=races=0;errors=[]
 if not root.exists():return {'bytes':0,'regular_files':0,'vanished_entries':0,'errors':[],'root_exists':False}
 def walkerror(error):
  if isinstance(error,FileNotFoundError):return
  errors.append({'path':relative(Path(error.filename or root),workspace),'error':type(error).__name__})
 for folder,dirs,names in os.walk(root,followlinks=False,onerror=walkerror):
  # os.walk will not recurse into symlink directories. Their own sizes are excluded.
  for name in names:
   path=Path(folder)/name
   try:info=path.lstat()
   except FileNotFoundError:races+=1;continue
   except OSError as error:
    errors.append({'path':relative(path,workspace),'error':type(error).__name__});continue
   if stat.S_ISREG(info.st_mode):total+=info.st_size;files+=1
 return {'bytes':total,'regular_files':files,'vanished_entries':races,'errors':errors,'root_exists':True}


def metadata(path):
 try:
  raw=path.read_bytes();value=json.loads(raw,parse_constant=lambda x:(_ for _ in ()).throw(ValueError(x)))
  if not isinstance(value,dict):raise ValueError('metadata root is not an object')
  return value,{'status':'READ','bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
 except FileNotFoundError:return None,{'status':'NOT_RUN_OR_ABSENT'}
 except (OSError,ValueError,TypeError) as error:return None,{'status':'UNREADABLE','error_type':type(error).__name__,'message':str(error)}


def phase_status(stage):
 views={};running=0;known=True
 for name in PHASES:
  value,receipt=metadata(stage/(name+'_RUN_STATE.json'))
  view={'planned_children':PLANNED[name],'metadata':receipt}
  if value is None:
   view['status']=receipt['status']
   if receipt['status']=='UNREADABLE':known=False
  else:
   jobs=value.get('jobs');live=value.get('running');unsubmitted=value.get('unsubmitted')
   if not all(isinstance(x,list) for x in (jobs,live,unsubmitted)):
    known=False;view['status']='UNKNOWN_MALFORMED_PHASE_METADATA'
   else:
    success=sum(isinstance(j,dict) and j.get('exit_code')==0 and j.get('wait4_reaped') is True for j in jobs)
    view.update(status=value.get('status','IN_PROGRESS_NO_TERMINAL_STATUS_FIELD'),
     successful_closed_children=success,closed_children=len(jobs),live_children=len(live),unsubmitted_children=len(unsubmitted))
    running+=len(live)
    view['complete_successful_phase']=(value.get('status')=='COMPLETE' and success==PLANNED[name] and len(jobs)==PLANNED[name] and not live and not unsubmitted)
  views[name]=view
 return views,running,known


def caps_from_scope(stage):
 raw=(stage/'SCOPE.json').read_bytes();scope=json.loads(raw);r=scope['resources']
 caps={'workspace_bytes':int(r['workspace_cap_bytes']),'results_bytes':int(r['new_output_payload_cap_bytes']),
       'coordinator_prelaunch_margin_bytes':536870912,'new_aggregate_CPU_s_cap':r['aggregate_new_CPU_s_cap'],
       'maximum_workers':r['max_concurrent_workers']}
 if caps['workspace_bytes']<=0 or caps['results_bytes']<=0:raise ValueError('Positive frozen storage caps required')
 caps['workspace_prelaunch_guard_bytes']=caps['workspace_bytes']-caps['coordinator_prelaunch_margin_bytes']
 caps['results_prelaunch_guard_bytes']=caps['results_bytes']-caps['coordinator_prelaunch_margin_bytes']
 return caps,hashlib.sha256(raw).hexdigest(),scope.get('study_id')


def capture(stage,workspace,scheduler_path,caps,sequence,started_monotonic,last_sample_start,interval):
 began=time.monotonic();begin_utc=utc()
 results=count_regular_bytes(stage/'results',workspace)
 work=count_regular_bytes(workspace,workspace)
 phases,running,known=phase_status(stage);scheduler,receipt=metadata(scheduler_path)
 scheduler_status=scheduler.get('status','UNKNOWN_STATUS') if scheduler else receipt['status']
 observed=[]
 for kind,measurement in [('results',results),('workspace',work)]:
  if measurement['bytes']>caps[kind+'_bytes']:observed.append(kind)
 gap=None if last_sample_start is None else began-last_sample_start
 sample={'schema':'SETI_CAPACITY_SAMPLE_V1','sequence':sequence,'sample_started_UTC':begin_utc,'sample_finished_UTC':utc(),
  'seconds_since_monitor_start':began-started_monotonic,'sample_duration_s':time.monotonic()-began,
  'sample_start_gap_s':gap,'declared_target_interval_s':interval,'declared_gap_limit_s':interval+GAP_ALLOWANCE_S,
  'observed_gap_above_limit':gap is not None and gap>interval+GAP_ALLOWANCE_S,
  'results':results,'workspace':work,'caps':caps,'phases':phases,
  'complete_successful_phase_count':sum(v.get('complete_successful_phase') is True for v in phases.values()),
  'scheduler_status':scheduler_status,'scheduler_metadata':receipt,
  'known_live_coordinator_running_entries':running,'all_phase_running_lists_readable_or_absent':known,
  'terminal_scheduler_and_no_live_coordinator':scheduler_status in TERMINAL and known and running==0,
  'observed_hardcap_exceeded':bool(observed),'observed_hardcap_exceeded_paths':observed,
  'observed_prelaunch_guard_reached':{'results':results['bytes']>=caps['results_prelaunch_guard_bytes'],'workspace':work['bytes']>=caps['workspace_prelaunch_guard_bytes']},
  'stat_only_payloads_not_opened':True,'own_monitor_files_included_in_workspace_walk':True,
  'counts_are_logical_regular_file_bytes_not_physical_blocks':True,
  'measurement_is_traversal_not_atomic_instantaneous_or_continuous':True}
 return sample,began


def peak_update(peak,sample):
 peak['samples']=sample['sequence'];peak['last_sample_started_UTC']=sample['sample_started_UTC'];peak['last_sample_finished_UTC']=sample['sample_finished_UTC']
 for kind in ('results','workspace'):
  old=peak['observed_peaks'][kind]
  if old is None or sample[kind]['bytes']>old['bytes']:
   peak['observed_peaks'][kind]={'bytes':sample[kind]['bytes'],'sequence':sample['sequence'],'sample_started_UTC':sample['sample_started_UTC']}
 gap=sample['sample_start_gap_s']
 if gap is not None:peak['maximum_observed_sample_start_gap_s']=max(peak['maximum_observed_sample_start_gap_s'] or 0,gap)
 peak['sample_gap_violations']+=int(sample['observed_gap_above_limit'])
 peak['samples_with_stat_errors']+=int(bool(sample['results']['errors'] or sample['workspace']['errors']))
 peak['samples_with_vanished_entries']+=int(bool(sample['results']['vanished_entries'] or sample['workspace']['vanished_entries']))
 peak['observed_hardcap_failure']=peak['observed_hardcap_failure'] or sample['observed_hardcap_exceeded']
 peak['resource_protocol_status']='OBSERVED_PROTOCOL_RESOURCE_FAILURE' if peak['observed_hardcap_failure'] else 'NO_BREACH_OBSERVED_AT_SAMPLED_TRAVERSALS'
 peak['latest_scheduler_status']=sample['scheduler_status'];peak['latest_phase_views']=sample['phases']
 peak['continuous_hardcap_compliance_proven']=False
 return peak


def run(stage,workspace,scheduler_path,out,interval=5.0,owner='/root'):
 if not (math.isfinite(interval) and interval==5.0):raise ValueError('Production sampling interval must be exactly5seconds')
 stage=stage.resolve();workspace=workspace.resolve();scheduler_path=scheduler_path.resolve();out=out.resolve()
 if stage==out or stage in out.parents:raise ValueError('Monitor writes must remain outside the frozen stage')
 if stage!=workspace and workspace not in stage.parents:raise ValueError('Stage must be within the measured workspace')
 if workspace not in out.parents:raise ValueError('Monitor output must be within workspace so its own files are counted')
 if owner!='/root':raise ValueError('Only the supervising root owns this monitor launch')
 caps,scope_sha,study=caps_from_scope(stage);out.mkdir(parents=True,exist_ok=True)
 statepath=out/'MONITOR_STATE.json';trace=out/'CAPACITY_SAMPLES.jsonl';peakpath=out/'PEAK_SUMMARY.json'
 state={'schema':'SETI_EXTERNAL_ONCE_ONLY_CAPACITY_MONITOR_V1','status':'STARTED_ONCE','owner':owner,'pid':os.getpid(),'started_UTC':utc(),
  'stage_relative_to_workspace':relative(stage,workspace),'scheduler_state_relative_to_workspace':relative(scheduler_path,workspace),
  'output_relative_to_workspace':relative(out,workspace),'workspace_root':str(workspace),'scope_sha256':scope_sha,'study_id':study,
  'interval_s':interval,'gap_limit_s':interval+GAP_ALLOWANCE_S,'caps':caps,'single_root_owned_launch':True,
  'no_dispatch_stop_cleanup_cap_changes_or_uploads':True,'trace_starts_at_launch_no_earlier_peak_claim':True}
 atomic_json(statepath,state,exclusive=True)
 # A partial previous launch also blocks replay: never reopen an existing trace for append.
 with trace.open('xb') as f:f.flush();os.fsync(f.fileno())
 sync_directory(out)
 peak={'schema':'SETI_CAPACITY_SAMPLED_PEAK_SUMMARY_V1','status':'MONITORING','monitor_started_UTC':state['started_UTC'],
  'stage_relative_to_workspace':state['stage_relative_to_workspace'],'output_relative_to_workspace':state['output_relative_to_workspace'],
  'scope_sha256':scope_sha,'caps':caps,'sampling_interval_s':interval,'declared_sample_start_gap_limit_s':interval+GAP_ALLOWANCE_S,
  'samples':0,'observed_peaks':{'results':None,'workspace':None},'maximum_observed_sample_start_gap_s':None,
  'sample_gap_violations':0,'samples_with_stat_errors':0,'samples_with_vanished_entries':0,'observed_hardcap_failure':False,
  'continuous_hardcap_compliance_proven':False,'trace_starts_at_launch_no_earlier_peak_claim':True,
  'trace_logical_bytes_included_in_workspace_census':True,
  'limitations':['Traversal samples are not atomic simultaneous counts and do not prove continuous caps.',
   'No earlier period peak is inferred; existing historical snapshots are not automatically merged.',
   'Reads only file metadata and small scope/coordinator/scheduler JSON; no array payloads decoded.',
   'File deletions/renames during traversal are counted as vanished entries; other stat errors remain explicit.',
   'Writes after a traversal are included only in a subsequent traversal; own growing trace/summary/state files are included.',
   'An observed hard-cap breach is a separate protocol resource failure; frozen SUMMARY is never edited.']}
 started=time.monotonic();last=None;sequence=0
 try:
  while True:
   sequence+=1;sample,last=capture(stage,workspace,scheduler_path,caps,sequence,started,last,interval)
   line=(json.dumps(sample,sort_keys=True,allow_nan=False)+'\n').encode()
   with trace.open('ab') as f:f.write(line);f.flush();os.fsync(f.fileno())
   peak_update(peak,sample);atomic_json(peakpath,peak)
   state.update(status='MONITORING',samples=sequence,latest_sample_started_UTC=sample['sample_started_UTC'],observed_hardcap_failure=peak['observed_hardcap_failure'])
   atomic_json(statepath,state)
   if sample['terminal_scheduler_and_no_live_coordinator']:
    status='CLOSED_OBSERVED_HARDCAP_FAILURE' if peak['observed_hardcap_failure'] else 'CLOSED_SAMPLED_EVIDENCE_ONLY'
    peak.update(status=status,closed_UTC=utc(),terminal_scheduler_status=sample['scheduler_status']);atomic_json(peakpath,peak)
    state.update(status=status,closed_UTC=peak['closed_UTC']);atomic_json(statepath,state)
    print(json.dumps({'status':status,'samples':sequence,'observed_peaks':peak['observed_peaks'],'continuous_hardcap_compliance_proven':False}),flush=True)
    return 1 if peak['observed_hardcap_failure'] else 0
   # Each sleep is bounded to5seconds. A long traversal is recorded rather than hidden.
   remaining=max(0.,interval-(time.monotonic()-last))
   if remaining:time.sleep(min(5.,remaining))
 except BaseException as error:
  peak.update(status='MONITOR_STOPPED_INCOMPLETE_EVIDENCE',stopped_UTC=utc(),failure={'type':type(error).__name__,'message':str(error)})
  state.update(status=peak['status'],stopped_UTC=peak['stopped_UTC'],failure=peak['failure'])
  atomic_json(peakpath,peak);atomic_json(statepath,state)
  raise


def selftest():
 """Tiny isolated metadata/filesystem fixtures, no real study or5second sleep."""
 checks=[]
 with tempfile.TemporaryDirectory(prefix='SETI_CAPACITY_FIXTURE_ONLY_') as tmp:
  root=Path(tmp);stage=root/'fake_stage';stage.mkdir();(stage/'results').mkdir()
  (stage/'results/a.bin').write_bytes(b'abc');(root/'other.bin').write_bytes(b'0123456789')
  (stage/'results/link').symlink_to(root/'other.bin')
  count=count_regular_bytes(stage/'results',root);assert count['bytes']==3 and count['regular_files']==1;checks.append('logical_regular_bytes_symlinks_excluded')
  count=count_regular_bytes(root/'absent',root);assert count['bytes']==0 and not count['root_exists'];checks.append('absent_results_is_explicit')
  scope={'study_id':'FIXTURE_ONLY','resources':{'workspace_cap_bytes':10**8,'new_output_payload_cap_bytes':2,'aggregate_new_CPU_s_cap':260000,'max_concurrent_workers':8}}
  atomic_json(stage/'SCOPE.json',scope)
  scheduler=root/'fake_scheduler.json';atomic_json(scheduler,{'status':'ALL_FROZEN_PHASES_CLOSED'})
  atomic_json(stage/'QA_RUN_STATE.json',{'status':'RUNNING','jobs':[{'exit_code':0,'wait4_reaped':True}],'running':[{'index':1}],'unsubmitted':[]})
  caps,h,study=caps_from_scope(stage);sample,t=capture(stage,root,scheduler,caps,1,time.monotonic(),None,5.)
  assert sample['observed_hardcap_exceeded'] and sample['observed_hardcap_exceeded_paths']==['results'] and not sample['terminal_scheduler_and_no_live_coordinator'];checks.append('observed_breach_flag_and_live_child_blocks_terminal')
  atomic_json(stage/'QA_RUN_STATE.json',{'status':'COMPLETE','jobs':[],'running':[],'unsubmitted':[]})
  sample,t=capture(stage,root,scheduler,caps,2,t,t-8.,5.);assert sample['terminal_scheduler_and_no_live_coordinator'] and sample['observed_gap_above_limit'];checks.append('terminal_requires_no_live_and_gap_violation_recorded')
  (stage/'QA_RUN_STATE.json').write_text('{')
  sample,t=capture(stage,root,scheduler,caps,3,t,None,5.);assert not sample['terminal_scheduler_and_no_live_coordinator'] and not sample['all_phase_running_lists_readable_or_absent'];checks.append('unreadable_phase_blocks_terminal_closure')
  path=root/'once.json';atomic_json(path,{'first':True},exclusive=True)
  try:atomic_json(path,{'second':True},exclusive=True);raise AssertionError('second launch accepted')
  except FileExistsError:pass
  assert json.loads(path.read_text())=={'first':True};checks.append('exclusive_launch_state_no_overwrite')
  peak={'samples':0,'observed_peaks':{'results':None,'workspace':None},'maximum_observed_sample_start_gap_s':None,'sample_gap_violations':0,'samples_with_stat_errors':0,'samples_with_vanished_entries':0,'observed_hardcap_failure':False}
  peak_update(peak,sample);assert peak['observed_hardcap_failure'] and not peak['continuous_hardcap_compliance_proven'];checks.append('breach_retained_no_continuous_compliance_claim')
 result={'status':'PASS_FIXTURES_ONLY','checks':checks,'production_monitor_launched':False,'science_trials':0,'real_study_values_read':False}
 print(json.dumps(result,sort_keys=True));return result


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--selftest',action='store_true')
 ap.add_argument('--stage',type=Path);ap.add_argument('--workspace',type=Path);ap.add_argument('--scheduler-state',type=Path);ap.add_argument('--out',type=Path)
 args=ap.parse_args()
 if args.selftest:selftest();return 0
 if any(x is None for x in (args.stage,args.workspace,args.scheduler_state,args.out)):ap.error('stage,workspace,scheduler-state,out required')
 return run(args.stage,args.workspace,args.scheduler_state,args.out)

if __name__=='__main__':raise SystemExit(main())
