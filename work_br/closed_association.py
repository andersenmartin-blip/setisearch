"""New BR execution: frozen BQ associations with closed-output verification.

Only the evidence writer and closure checks change. Frozen BP/BQ source files
and all earlier outputs remain untouched. No saved score inputs are opened at
import time, and this module contains no random generator or scan scorer.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
BQ_PATH = ROOT/'work_bq/stream_association.py'
BQ_SHA256 = '455ad449bbe7ddd540b559461620e652c15bffe76b0c597648f8fd780a5fa115'
CLOSURE_PATH = Path(__file__).with_name('stream_closure.py')
_spec = importlib.util.spec_from_file_location('br_stream_closure', CLOSURE_PATH)
closure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(closure)


def specification():
    return {'schema':'SETI_BR_CLOSED_ASSOCIATION_SPEC_V1',
            'execution_identity':'BR_A04_ASSOC_V1',
            'frozen_BQ_source_sha256':BQ_SHA256,
            'method':'Call unchanged frozen BQ run_stream_assessment with its writer replaced in this new module instance only',
            'new_writer':'AtomicJSONLPublisher; identical compact sorted-key JSON serialization per original association record',
            'closure_specification':closure.specification(),
            'thresholds_candidates_scores_changed':False,
            'BP_failure_preserved':True,'BQ_integrity_failure_preserved':True,
            'BQ_failure_cause':'UNESTABLISHED',
            'new_scan_scores':0,'RNG_calls':0,'astronomical_powers_opened':0}


def load_bq():
    with BQ_PATH.open('rb') as f:
        actual=hashlib.file_digest(f,'sha256').hexdigest()
    closure.require(actual==BQ_SHA256,'BQ_SOURCE_CHANGED','Frozen BQ stream source differs')
    spec=importlib.util.spec_from_file_location('br_frozen_bq_stream',BQ_PATH)
    bq=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bq)
    return bq


class ClosedWriter:
    """BQ writer protocol backed by exclusive pending-to-final publication."""
    def __init__(self,path):
        path=Path(path)
        self.publisher=closure.AtomicJSONLPublisher(path.parent,path.name)

    def append(self,record):
        self.publisher.append(record)

    def close(self):
        return self.publisher.close()

    def close_partial(self):
        self.publisher.close_partial()


def run_closed_assessment(scan_dirs,case_spec,output_dir,base_scan_dirs,input_pins):
    bq=load_bq()
    old_writer=bq.AssociationWriter
    bq.AssociationWriter=ClosedWriter
    try:
        result=bq.run_stream_assessment(scan_dirs,case_spec,output_dir,base_scan_dirs,input_pins)
    finally:
        bq.AssociationWriter=old_writer
    computation_status=result['status']
    child_check=closure.evaluate_closure(output_dir,result,stage='child_end')
    if child_check['status']!='PASS':
        result['status']='FAIL'
    result.update(
        schema='SETI_BR_CLOSED_ASSESSMENT_V1',execution_identity='BR_A04_ASSOC_V1',
        original_computation_status_preserved=computation_status,
        output_bindings_verified=child_check['status']=='PASS',
        child_stream_closure=child_check,
        frozen_BQ_source_sha256=BQ_SHA256,
        BQ_effective_failure_preserved=True,
        BQ_failure_cause='UNESTABLISHED',
        BQ_stream_mismatch_preserved='current receipt declared 82645873 bytes/43306 records; closed artifact was 71236624 bytes/36857 complete prefix records',
        new_identity_qualification='Same saved-score association endpoints under a new bounded execution identity; original BP RSS failure and BQ integrity failure remain FAIL.')
    return result
