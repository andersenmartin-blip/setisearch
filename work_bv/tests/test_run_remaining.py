"""Serial policy tests with synthetic metadata and no astronomical powers."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SOURCE=Path(__file__).resolve().parents[1]/'run_remaining.py'
spec=importlib.util.spec_from_file_location('bv_serial_test',SOURCE)
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)


class SerialTests(unittest.TestCase):
    def scenario(self, fail_at=None):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        root=Path(temporary.name);execution=root/'execution';isolation=root/'isolation';reviews=root/'audit_execution'
        plan=root/'plan.json';plan.write_text('{}\n')
        reviewer=root/'artificial_reviewer.py';reviewer.write_text('# synthetic metadata only\n')
        sources={str(SOURCE):driver.stage.sha(SOURCE),str(reviewer):driver.stage.sha(reviewer)}
        wanted={'batch_q_lists':[[33],[34],[35]]};calls=[];audits=[]
        def production(batch,overall_deadline=None):
            calls.append(batch);return 1 if batch==fail_at else 0
        def audit(batch,pins,deadline):
            audits.append(batch)
            return ({'status':'PASS'}, {'status':'PASS_BOUNDED_INDEPENDENT_REVIEW',
                    'ON_seed_rows_all_semantically_reviewed':0,'status_counts':{}}, {'sha256':'a'*64})
        with contextlib.ExitStack() as stack:
            for target,name,value in [(driver,'HERE',root),(driver,'REVIEW_SOURCE',reviewer),
                    (driver,'REVIEW_CAPTURE',reviews),(driver,'SERIAL_START',execution/'SERIAL_RUN_START.json'),
                    (driver,'SERIAL_RESULT',execution/'SERIAL_RUN_RESULT.json'),(driver.stage,'EXECUTION',execution),
                    (driver.stage,'ISOLATION',isolation),(driver.stage,'PLAN',plan),(driver.stage,'BATCH_COUNT',3)]:
                stack.enter_context(patch.object(target,name,value))
            stack.enter_context(patch.object(driver.stage,'binding_pins',return_value=(wanted,sources,{})))
            stack.enter_context(patch.object(driver.stage,'run_parent',side_effect=production))
            stack.enter_context(patch.object(driver,'run_audit',side_effect=audit))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            code=driver.run_all();saved=json.loads((execution/'SERIAL_RUN_RESULT.json').read_text())
            with self.assertRaisesRegex(ValueError,'already used'):
                driver.run_all()
        return code,saved,calls,audits

    def test_fixed_order_completes_once_and_rejects_reuse(self):
        code,saved,calls,audits=self.scenario()
        self.assertEqual(code,0);self.assertEqual(saved['status'],'PASS')
        self.assertEqual(calls,[1,2,3]);self.assertEqual(audits,[1,2,3])
        self.assertTrue(saved['all_planned_batches_completed'])

    def test_failed_batch_stops_without_audit_retry_or_later_execution(self):
        code,saved,calls,audits=self.scenario(fail_at=2)
        self.assertEqual(code,1);self.assertEqual(saved['status'],'FAIL')
        self.assertEqual(calls,[1,2]);self.assertEqual(audits,[1])
        self.assertEqual(saved['attempted_batches'],[1,2])
        self.assertEqual(len(saved['completed_batches']),1)
        self.assertTrue(saved['errors'])

    def test_expired_overall_deadline_rejects_before_output(self):
        with self.assertRaisesRegex(ValueError,'No remaining overall wall budget'):
            driver.stage.run_parent(1,overall_deadline=0)


if __name__=='__main__':unittest.main()
