"""Seal BX evidence after closed scientific runs and independent binding review."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
BX = ROOT / 'work_bx'
STAGE = Path('/dev/shm/seti_bx_ata_20261031/delivery')
DEST = ROOT.parent / 'bx_delivery'
REPORT = 'RADIO_PROGRESS_BX_DATA_SOURCES_2026-10-31.md'
NAME = 'SETI_FORTSAETTELSE_BX_2026-10-31_EVIDENCE.zip'

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def main():
    assert (BX / 'FINAL_BINDING_REVIEW_BX.json').is_file()
    assert (BX / 'ata/REVIEW_ATA_BX.json').is_file()
    binding = json.loads((BX / 'FINAL_BINDING_REVIEW_BX.json').read_text())
    assert binding['status'] == 'PASS_COMPACT_SUMMARY_AND_REPORT_BINDING'
    for name, digest in binding['bound_file_sha256'].items():
        assert sha(Path(name)) == digest
    STAGE.mkdir(exist_ok=False)
    contents = STAGE / 'contents'
    contents.mkdir()
    files = [ROOT / REPORT, ROOT / 'work_bt/isolated_worker.py']
    for path in sorted(BX.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(BX)
        if 'packages' in relative.parts or '__pycache__' in relative.parts:
            continue
        if relative.name in {'DELIVERY_BX.json', 'PACKAGE_RECEIPT_BX.json'}:
            continue
        files.append(path)
    for path in files:
        assert not path.is_symlink()
        before = sha(path)
        target = contents / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        with path.open('rb') as src, target.open('xb') as dst:
            shutil.copyfileobj(src, dst)
        assert before == sha(path) == sha(target)
    spec = importlib.util.spec_from_file_location('bx_archive', ROOT / 'work_bt/isolated_worker.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    sealed = STAGE / NAME
    receipt = helper.create_archive(contents, sealed)
    DEST.mkdir(exist_ok=True)
    exported = helper.export_archive(sealed, DEST / NAME, receipt)
    result = {'schema': 'SETI_BX_PACKAGE_V1', 'status': 'PASS',
              'local_path': str(DEST / NAME), 'closed_archive': exported,
              'new_scientific_run': False}
    with (BX / 'PACKAGE_RECEIPT_BX.json').open('x') as f:
        json.dump(result, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')
    print(json.dumps({'status': 'PASS', 'path': str(DEST / NAME),
                      'bytes': exported['bytes'], 'sha256': exported['sha256'],
                      'members': len(exported['members'])}))

if __name__ == '__main__':
    main()
