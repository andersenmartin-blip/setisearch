#!/usr/bin/env python3
"""Fresh offline reproduction of the calibration-log reconciliation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_ls7v_reduction_log'


def main():
    with tempfile.TemporaryDirectory(prefix='ls7v_reproduce_') as temp:
        run = subprocess.run([sys.executable,str(ROOT/'scripts/ls7v_reconcile_log.py'),
                              '--output',temp],cwd=ROOT,capture_output=True,text=True)
        if run.returncode:
            raise RuntimeError(run.stderr+run.stdout)
        summary = json.loads(run.stdout)
        files = []
        for name in ['summary.json','selected_calibration_lines.json']:
            original = (OUT/name).read_bytes()
            assert original == (Path(temp)/name).read_bytes(), name
            files.append({'path':'results_ls7v_reduction_log/'+name,
                'bytes':len(original),'sha256':hashlib.sha256(original).hexdigest(),
                'byte_identical':True})
    result = {'checkpoint':'LS7V','verified':True,
        'source_log_identity_verified':summary['source_log_sha256'],
        'reused_input_identities':summary['audit']['historical_input_identities_verified'],
        'header_identity_matches':summary['audit']['header_identity_matches'],
        'exact_default_value_matches':summary['audit']['exact_default_value_matches'],
        'reproduced_outputs':files,'network_transfer_bytes':0,
        'target_image_bytes':0,'new_native_trials':0,
        'input_decision':summary['input_decision']}
    text = json.dumps(result,indent=2,allow_nan=False)+'\n'
    (OUT/'reproduction.json').write_text(text)
    print(text,end='')


if __name__ == '__main__':
    main()
