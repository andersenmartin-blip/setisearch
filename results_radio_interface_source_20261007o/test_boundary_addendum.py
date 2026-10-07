"""Three new controls only; earlier 35 are not replayed or recounted."""
import importlib.util
import json
import os
from pathlib import Path
import resource
import socket
import time
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('radio_O_first_harness', HERE/'test_interface.py')
first = importlib.util.module_from_spec(spec); spec.loader.exec_module(first)


class BoundaryAddendumTests(first.InterfaceTests):
    def flagged_channel(self, flag):
        original = self.a
        class ManufacturedFlags:
            def getsockopt(_, *args): return original.getsockopt(*args)
            def recvmsg(_, *args):
                raw, ancillary, flags, address = original.recvmsg(*args)
                return raw, ancillary, flags | flag, address
        return ManufacturedFlags()

    def test_cleanup_closes_adapter_not_only_descriptors(self):
        self.startup(); self.target.close_fixture_descriptors()
        before = len(self.target.raw_records)
        with self.assertRaises(ValueError): self.target.receive_fixture(self.a)
        with self.assertRaises(ValueError): self.target.finish_fixture(1234, 0)
        self.assertEqual(len(self.target.raw_records), before)
        self.assertTrue(self.target.poisoned)

    def test_normal_record_flag_preserves_unrewritten_v2_packet(self):
        raw = self.packet(1, 0); self.b.sendmsg([raw])
        self.inputs.append({'manufactured_flag':socket.MSG_EOR,'raw_hex':raw.hex()})
        self.assertTrue(self.target.receive_fixture(self.flagged_channel(socket.MSG_EOR)))
        self.assertEqual(self.target.raw_records[-1]['raw_hex'], raw.hex())

    def test_unknown_flag_with_descriptor_closes_all_received_rights(self):
        fd = os.open(self.main, os.O_RDONLY)
        import array
        try:
            before = len(os.listdir('/proc/self/fd')); raw = self.packet(1, 0)
            self.b.sendmsg([raw],[(socket.SOL_SOCKET,socket.SCM_RIGHTS,array.array('i',[fd]))])
            self.inputs.append({'manufactured_flag':socket.MSG_OOB,'raw_hex':raw.hex()})
            with self.assertRaises(ValueError): self.target.receive_fixture(self.flagged_channel(socket.MSG_OOB))
            self.assertEqual(len(os.listdir('/proc/self/fd')), before)
            self.assertEqual(self.target.raw_records[-1]['received_descriptors'], 1)
        finally: os.close(fd)


if __name__ == '__main__':
    resource.setrlimit(resource.RLIMIT_CPU,(1,1))
    resource.setrlimit(resource.RLIMIT_AS,(384*1024**2,384*1024**2))
    resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
    resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2))
    names=['test_cleanup_closes_adapter_not_only_descriptors',
           'test_normal_record_flag_preserves_unrewritten_v2_packet',
           'test_unknown_flag_with_descriptor_closes_all_received_rights']
    at=time.monotonic();result=unittest.TextTestRunner(verbosity=2).run(
        unittest.TestSuite(BoundaryAddendumTests(name) for name in names))
    seconds=time.monotonic()-at
    record={'schema':'radio-O-three-new-boundary-controls-v1','cases':result.testsRun,
            'failures':len(result.failures),'errors':len(result.errors),'seconds':seconds,
            'process_peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'tests':first.EVIDENCE,'prior_35_reexecuted':False,
            'source_context_explicit_read_bytes':len(first.MANIFEST)+sum(map(len,first.RAWS.values())),
            'cumulative_native_or_scientific_budget_reset':False,
            'native_callback_observations':0,'native_runtime_codec_science_authority':False}
    raw=first.o.canonical(record)
    with (HERE/'COHORT-2-NEW-BOUNDARIES.json').open('xb') as out:out.write(raw)
    raise SystemExit(0 if result.wasSuccessful() else 1)
