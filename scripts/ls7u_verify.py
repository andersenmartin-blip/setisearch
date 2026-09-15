#!/usr/bin/env python3
"""Reconstruct both fixed electronics measurements offline and check release scope."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_ls7u_prescan'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(script, *args):
    p = subprocess.run([sys.executable,str(ROOT/'scripts'/script),*args],
                       cwd=ROOT,capture_output=True,text=True,env=os.environ.copy())
    if p.returncode:
        raise RuntimeError(f'{script} failed: {p.stderr}\n{p.stdout}')
    return json.loads(p.stdout)


def main():
    manifests = [OUT/'acquisition.json',OUT/'blank_reference/acquisition.json']
    before = [sha(p) for p in manifests]
    fresh = [run('ls7u_acquire_prescan.py','--offline'),
             run('ls7u_acquire_blank.py','--offline')]
    assert all(r['new_transfer_bytes'] == 0 for r in fresh)
    assert before == [sha(p) for p in manifests]
    expected = [[(86803200,8640),(86811840,1382400)],
                [(69134400,8640),(69143040,2764800)]]
    original = json.loads((ROOT/'results_ls7r_metadata/SCI_RAW_SubArray_ranges.json').read_text())
    for p,ranges in zip(manifests,expected):
        manifest = json.loads(p.read_text())
        assert manifest['etag'] == original['etag']
        assert manifest['total_object_bytes'] == original['total_file_bytes']
        assert [(e['start'],e['count']) for e in manifest['ranges']] == ranges
        assert manifest['target_image_bytes'] == 0
        # Native science plane occupies [14,400, 69,134,400); never intersects.
        assert all(start >= 69134400 or start+count <= 14400 for start,count in ranges)
    files = []
    with tempfile.TemporaryDirectory(prefix='ls7u_verify_') as tmp:
        t = Path(tmp)
        primary = run('ls7u_assess_prescan.py','--output',str(t/'primary'))
        blank = run('ls7u_assess_blank.py','--output',str(t/'blank'))
        for folder,source,names in [
            (OUT,t/'primary',['summary.json','prescan_frame_statistics.csv.gz']),
            (OUT/'blank_reference',t/'blank',['summary.json','blank_frame_statistics.csv.gz'])]:
            for name in names:
                assert (folder/name).read_bytes() == (source/name).read_bytes(), name
                files.append({'path':str((folder/name).relative_to(ROOT)),
                              'sha256':sha(folder/name),'byte_identical':True})
    result = {'checkpoint':'LS7U','verified':True,'network_transfer_bytes':0,
        'range_manifest_bytes_unchanged':True,'retained_range_bytes':4164480,
        'electronic_reference_array_bytes':4147200,'header_bytes':17280,
        'target_image_bytes':0,'source_residual_trials':0,'pulse_recovery_trials':0,
        'new_candidates':0,'new_qualified_observing_seconds':0,
        'astropy_vs_struct_electronic_values':primary['audit']['astropy_vs_struct_values']+blank['audit']['astropy_vs_struct_values'],
        'primary_scalar_frame_statistics':primary['audit']['frame_scalar_statistics'],
        'supplement_scalar_clip_mask_comparisons':blank['audit']['scalar_vs_original_mask_comparisons'],
        'primary_fits_checksum_valid':True,'supplement_fits_checksum_valid':True,
        'reproduced_outputs':files,
        'decision':'NOT_READY_FOR_TARGET_IMAGE_STUDY'}
    text = json.dumps(result,indent=2,allow_nan=False)+'\n'
    (OUT/'verification.json').write_text(text)
    print(text,end='')


if __name__ == '__main__':
    main()
