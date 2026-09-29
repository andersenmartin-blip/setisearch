#!/usr/bin/env python3
"""Audit a closed failure and represent its history; no writer or lease."""
import json
from pathlib import Path
import resource
import signal
import time
from unittest.mock import patch

from seti_repeater import physical_evidence_radio as e
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater import whole_cadence_history_radio as h
from seti_repeater.empty_null_radio import canonical
from seti_repeater.pipeline_receiver_radio import NativeRun

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_radio_physical_case_2026-09-29'
SOURCE=OUT/'integration01'


def inventory():
    return {p.relative_to(SOURCE).as_posix():{'bytes':p.stat().st_size,'sha256':e.sha(p.read_bytes())}
            for p in SOURCE.rglob('*') if p.is_file()}


def main():
    started=time.monotonic();out=OUT/'readonly01';out.mkdir(exist_ok=False)
    before=inventory();fixed=json.loads((SOURCE/'fixed_before_consumption.json').read_bytes())
    failure=json.loads((SOURCE/'failure.json').read_bytes());reference=failure['closure']['physical_evidence_reference']
    names=['RADIO_PHYSICAL_CASE_2026-09-29_READONLY_AUDIT.md','scripts/radio_physical_case_postflight.py',
           'src/seti_repeater/whole_cadence_history_radio.py','src/seti_repeater/physical_evidence_radio.py',
           'src/seti_repeater/whole_cadence_journal_radio.py']
    pins={'source_files':before,'expected_physical_reference':reference,
          'code_and_scope_sha256s':{n:e.sha((ROOT/n).read_bytes()) for n in names}}
    j.durable_write(out/'fixed_before_audit.json',canonical(pins))
    def deadline(signum,frame):raise TimeoutError('Read-only audit deadline')
    signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,60)
    with patch.object(j,'consume',side_effect=AssertionError('Consumption forbidden')), \
         patch.object(j.DirectoryStore,'publish',side_effect=AssertionError('Publication forbidden')), \
         patch.object(e.Writer,'checkpoint',side_effect=AssertionError('Physical writing forbidden')), \
         patch.object(e.Writer,'create_for_lease',side_effect=AssertionError('Physical writer forbidden')), \
         patch('numpy.random.Generator',side_effect=AssertionError('RNG forbidden')), \
         patch('numpy.random.SeedSequence',side_effect=AssertionError('RNG forbidden')), \
         patch.object(NativeRun,'__init__',side_effect=AssertionError('Native run forbidden')):
        cp=j.DirectoryStore(SOURCE/'journal').read();state=j.replay(cp.document)
        check=j.verify_archive(cp,SOURCE/'case',case_index=0)
        assert check['status']=='failed' and state['attempt_failed'] is True
        files=e._inventory(SOURCE/'case')
        physical={e.nested_name(n):data for n,data in files.items() if n.startswith('physical-')}
        view=e.inspect_files(physical,expected_config_sha256=reference['reservation_sha256'],
            expected_last_checkpoint_sha256=reference['last_checkpoint_sha256'],allow_orphans=True)
        restored=[]
        for index in range(len(view.checkpoint_bytes)):
            raw=view.snapshot(index);wanted=fixed['schedule'][index]
            assert len(raw)==wanted['bytes'] and e.sha(raw)==wanted['sha256']
            restored.append(wanted)
        rows=sorted((SOURCE/'journal/revisions').iterdir(),key=lambda p:len(json.loads(p.read_bytes())['events']))
        originals=[r.read_bytes() for r in rows];hashes=[r.name for r in rows]
        assert rows[-1].name==cp.revision
        packed=h.encode(originals,expected_revision_sha256s=hashes,decoded_cap=32*1024**2)
        reader=h.verify(packed,expected_sha256=e.sha(packed),expected_revision_sha256s=hashes,decoded_cap=32*1024**2)
        for i,raw in enumerate(originals):assert reader.revision(i)==raw
        assert inventory()==before
        j.durable_write(out/'closed_journal_history.json',packed)
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        assert peak<=512*1024**2
        result={'status':'READONLY_AUDIT_PASS_ORIGINAL_INTEGRATION_STILL_FAILED',
            'archive_check':check,'verified_physical_checkpoints':len(restored),'intended_physical_views':len(fixed['schedule']),
            'uncommitted_physical_members':list(view.orphan_paths),
            'uncommitted_physical_member_bytes':sum(len(physical[n]) for n in view.orphan_paths),
            'physical_terminal_footer_present':view.footer_bytes is not None,'physical_summary':view.summary(),
            'history':reader.summary(),'all_original_revision_bytes_exact':True,
            'outer_failure_footer_bytes':len(files['case_outcome.json']),
            'closed_source_file_count':len(before),'closed_source_bytes':sum(x['bytes'] for x in before.values()),
            'closed_files_unchanged':True,'original_scope_outcome':'CLOSED_BYTE_INTEGRATION_FAILURE',
            'new_case_consumption':False,'new_random_values':0,'new_native_scores':0,'new_physical_decisions':0,
            'elapsed_seconds':time.monotonic()-started,'peak_rss_bytes':peak}
        j.durable_write(out/'result.json',canonical(result))
        assert sum(x.stat().st_size for x in out.rglob('*') if x.is_file())<=8*1024**2
        print(json.dumps(result,indent=2),flush=True)
    signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':main()
