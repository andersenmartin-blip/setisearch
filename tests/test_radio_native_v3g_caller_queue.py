"""Tiny offline scheduling tests; no deterministic source or control is run."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('v3_queue_fixture',
    ROOT/'scripts/radio_native_v3g_compact_eight_case_resource_fixture.py')
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)


class CapacityWriteTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)/'cases'/'case00'
        self.root.mkdir(parents=True)

    def node_check(self,path,additional):
        source="const fs=require('node:fs'),path=require('node:path');\n"+FIXTURE.case_metadata_worker_guard()+\
            'checkCaseMetadataWrite('+json.dumps(str(path))+','+str(additional)+');'
        return subprocess.run([shutil.which('node'),'-e',source],capture_output=True,
            text=True,timeout=5,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})

    def test_python_and_node_budgets_accept_last_block_then_refuse_before_create(self):
        retained=self.root/'ordinary.json'
        with retained.open('wb') as stream:stream.truncate(FIXTURE.CASE_OTHER_METADATA_BUDGET_BYTES-4096)
        wanted=self.root/'new.json'
        FIXTURE.check_case_metadata_write(wanted,4096)
        self.assertEqual(self.node_check(wanted,4096).returncode,0)
        with self.assertRaisesRegex(ValueError,'capacity exceeded before write'):
            FIXTURE.write(wanted,b'a'*4097)
        self.assertFalse(wanted.exists())
        result=self.node_check(wanted,4097)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('capacity exceeded before write',result.stderr)

    def test_other_files_are_charged_and_separately_bounded_context_is_excluded(self):
        with (self.root/'worker-admission.json').open('wb') as stream:stream.truncate(2*1024*1024)
        wanted=self.root/'prepared.json'
        FIXTURE.write(wanted,{'tiny':True})
        self.assertEqual(self.node_check(self.root/'next.json',4096).returncode,0)
        self.assertTrue(FIXTURE.case_capacity_excluded('command-37-admission.json'))
        self.assertFalse(FIXTURE.case_capacity_excluded('command-38-admission.json'))
        self.assertFalse(FIXTURE.case_capacity_excluded('foreign-observation.json'))

    def test_aliases_are_refused_by_both_budget_readers(self):
        (self.root/'aliased.json').symlink_to(self.root/'missing.json')
        with self.assertRaisesRegex(ValueError,'sole-link'):
            FIXTURE.check_case_metadata_write(self.root/'new.json',1)
        self.assertNotEqual(self.node_check(self.root/'new.json',1).returncode,0)

    def test_shared_context_group_refuses_write_before_exclusive_create(self):
        scope=Path(self.temporary.name)/FIXTURE.PREFIX
        scope.mkdir()
        with (scope/'complete-freeze.json').open('wb') as stream:
            stream.truncate(FIXTURE.SHARED_METADATA_GROUP_BYTES)
        wanted=scope/'plan.json'
        with self.assertRaisesRegex(ValueError,'shared metadata capacity'):
            FIXTURE.write(wanted,{'tiny':True})
        self.assertFalse(wanted.exists())

    def test_derived_stream_refuses_oversized_next_chunk_without_large_input(self):
        derived=FIXTURE.templates((ROOT/FIXTURE.CODE_FILES[0]).read_text())
        caller=derived['fresh-caller.js'].decode()
        prefix=caller[:caller.index('async function caller(scope,bundlePath,bundleDigest)')]
        # Exercise the exact derived serializer with an eight-byte test cap.
        # The production cap stays unchanged and no worker/control is invoked.
        prefix=prefix.replace('written+amount>'+str(FIXTURE.TRANSCRIPT_CAPACITY_BYTES),'written+amount>8')
        destination=Path(self.temporary.name)/'tiny-transcript.json'
        source=prefix+'\nstreamJson('+json.dumps(str(destination))+',"0123456789");'
        result=subprocess.run([shutil.which('node'),'-e',source],capture_output=True,
            text=True,timeout=5,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})
        self.assertNotEqual(result.returncode,0)
        self.assertIn('full-transcript capacity exceeded before write',result.stderr)
        self.assertLessEqual(destination.stat().st_size,8)


class CallerQueueTests(unittest.TestCase):
    def node(self, source):
        completed = subprocess.run([shutil.which('node'), '-e',
            FIXTURE.SERIAL_EXECUTOR_HELPER + source], check=True,
            capture_output=True, text=True, timeout=5,
            env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})
        self.assertEqual(completed.stderr, '')
        return json.loads(completed.stdout)

    def test_all_38_readers_then_tail_preserve_exact_call_order_and_values(self):
        result = self.node('''
let live = 0, maximum = 0; const launched = [], received = [];
const run = serializeLocalExecutor(async args => {
  live++; maximum = Math.max(maximum, live); launched.push(args);
  await new Promise(resolve => setImmediate(resolve));
  live--; return { ordinal: args.ordinal, output: args.output, offline_fixture: true };
});
const calls = Array.from({length:39}, (_,ordinal) => ({ordinal,output:'tiny-'+ordinal}));
Promise.allSettled(calls.map(args => run(args))).then(results => {
  for (const row of results) received.push(row.value);
  process.stdout.write(JSON.stringify({maximum,launched,received,statuses:results.map(row=>row.status)}));
});
''')
        expected_calls = [{'ordinal':i, 'output':'tiny-'+str(i)} for i in range(39)]
        self.assertEqual(result['maximum'], 1)
        self.assertEqual(result['launched'], expected_calls)
        self.assertEqual(result['received'], [{**item, 'offline_fixture':True} for item in expected_calls])
        self.assertEqual(result['statuses'], ['fulfilled']*39)

    def test_failure_permanently_stops_all_queued_and_later_work(self):
        result = self.node('''
const launched = [], fault = new Error('fixed fault');
const run = serializeLocalExecutor(async args => {
  launched.push(args);
  await new Promise(resolve => setImmediate(resolve));
  if (args === 3) throw fault;
  return args;
});
Promise.allSettled(Array.from({length:39}, (_,i) => run(i))).then(async results => {
  const later = await Promise.allSettled([run(99)]);
  process.stdout.write(JSON.stringify({launched,statuses:results.map(row=>row.status),
    values:results.slice(0,3).map(row=>row.value),
    same_fault:results.slice(3).every(row=>row.reason===fault)&&later[0].reason===fault,
    later_status:later[0].status}));
});
''')
        self.assertEqual(result['launched'], [0,1,2,3])
        self.assertEqual(result['values'], [0,1,2])
        self.assertEqual(result['statuses'], ['fulfilled']*3+['rejected']*36)
        self.assertTrue(result['same_fault'])
        self.assertEqual(result['later_status'], 'rejected')

    def test_synchronous_fault_starts_no_later_subprocess(self):
        result = self.node('''
const launched = [], fault = new Error('synchronous fixed fault');
const run = serializeLocalExecutor(args => { launched.push(args); throw fault; });
Promise.allSettled([run(0),run(1),run(2)]).then(results => {
  process.stdout.write(JSON.stringify({launched,
    statuses:results.map(row=>row.status),same_fault:results.every(row=>row.reason===fault)}));
});
''')
        self.assertEqual(result['launched'], [0])
        self.assertEqual(result['statuses'], ['rejected']*3)
        self.assertTrue(result['same_fault'])

    def test_actual_fresh_caller_wraps_only_the_local_subprocess_executor(self):
        source = (ROOT/FIXTURE.CODE_FILES[0]).read_text()
        derived = FIXTURE.templates(source)['fresh-caller.js'].decode()
        self.assertEqual(derived.count(FIXTURE.SERIAL_EXECUTOR_HELPER), 1)
        self.assertEqual(derived.count('const execLocal=serializeLocalExecutor('), 1)
        self.assertIn('const raw=await execLocal(args)', derived)
        self.assertIn('sourceReads++', derived)
        self.assertIn("ensure(tailCount++===0,'Exactly one real local caller-tail saver; no retry')", derived)
        self.assertIn("'--command-worker',scope,'command-'+String(readByCommand.get(args.cmd)?.ordinal??'tail')", derived)
        syntax = subprocess.run([shutil.which('node'), '--check'], input=derived,
            capture_output=True, text=True, timeout=5,
            env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})
        self.assertEqual(syntax.returncode, 0, syntax.stderr)


if __name__ == '__main__':
    unittest.main()
