# HIP98505 ON burst search and fixed context: reproduction

This package preserves the three completed ON searches, their 288 carrier maps,
1,170 raw 4×503 score-audit capsules, nine saved DC-aware winners and their 54
fixed six-scan context profiles. Every unique context normalization core/scan
has a saved raw 16×12096 crop. The package also contains the scopes, original
source metadata, execution receipts, independent QA, reviews, code and report.

All three ON scans belong to one historical 2017-04-28 visit of HIP98505. The
context retains the six original scan labels, directions and ON/OFF acquisition
roles. Scores are empirical robust box-track scores, not calibrated SNR or
false-alarm probabilities. DC-aware ranking checks only the already winning
four-row boxes. It does not search a replacement hypothesis. Fixed context
holds the selected frequency, drift, width, winning local four-row window and
4096-channel normalization core unchanged; it neither refits nor applies an
ON/OFF veto.

## Files and environment

Extract the ZIP into a fresh directory and run commands from that directory.
The paths `seti_burst_on/` and `burst_previous/` must stay as packaged. Archive
members use workspace-relative paths. `ON_BURST4_PACKAGE_MANIFEST.json` lists
each included file's SHA256 and size, together with the exact excluded HDF5
source declarations. The ZIP contains no original HDF5 compacts, runtime
wheels or old result-array trees.

The recorded numerical runtime is in each execution/QA receipt. For the
original run it uses Python 3.12.3 with NumPy 2.3.5, SciPy 1.17.0, h5py 3.15.1,
hdf5plugin 7.1.0 and HDF5 1.14.6. The audit checks this exact runtime tuple.
Using a Python 3.12.3 interpreter, an isolated environment can be prepared with:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install numpy==2.3.5 scipy==1.17.0 h5py==3.15.1 hdf5plugin==7.1.0
```

The portable context replay imports and checks the same pinned numerical
runtime, including h5py and the bitshuffle decoder, while opening no original
HDF5. No command below downloads telescope observations or reruns a detector
grid.

## Verify the delivered file bytes

This standard-library command verifies the complete included manifest without
opening any numerical array:

```bash
python3.12 - <<'PY'
import hashlib, json
from pathlib import Path
root = Path('.').resolve()
manifest = json.loads((root / 'ON_BURST4_PACKAGE_MANIFEST.json').read_bytes())
for item in manifest['files']:
    path = root / item['path']
    assert path.is_file() and path.stat().st_size == item['bytes'], item['path']
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    assert h.hexdigest() == item['sha256'], item['path']
print('PASS', len(manifest['files']), 'included file byte pins')
PY
```

## Portable context replay from saved crops

Keep the delivered `qa_results/QA_RECEIPT.json` unchanged: the context GO pins
that original primary-QA receipt. Use a fresh output directory. The following
command supplies the exact scope, QA-code, context-receipt and GO hashes
derived from their delivered bytes:

```bash
.venv/bin/python - <<'PY'
import hashlib, subprocess, sys
from pathlib import Path
root = Path('.').resolve()
def sha(name):
    return hashlib.sha256((root / name).read_bytes()).hexdigest()
base = 'seti_burst_on/'
command = [sys.executable, base + 'context_qa.py', '--root', str(root),
           '--portable', '--output-dir', base + 'fresh_portable_replay',
           '--scope-sha256', sha(base + 'CONTEXT_SCOPE.json'),
           '--qa-sha256', sha(base + 'context_qa.py'),
           '--receipt-sha256', sha(base + 'context_results/EXECUTION_RECEIPT.json'),
           '--root-go-sha256', sha(base + 'CONTEXT_QA_GO.json')]
subprocess.run(command, check=True)
PY
```

Expected receipt status:
`PASS_PORTABLE54_FIXED_PROFILES9_OWN_SCORES_ALL_PINNED_CROP_FULL501_NORMALIZATIONS`.
The new receipt is
`seti_burst_on/fresh_portable_replay/QA_RECEIPT.json`.

This independently recomputes the 501-channel running medians and the full
4096-channel row median/MAD/winsorized locations for every unique saved crop.
It checks all raw profile bits against those crops, all 54 fixed four-row and
full16 scores, all row contributions and all nine own primary score matches.
It verifies original source metadata and provenance declarations without
reopening the original HDF5 or rechecking its full decoded row hashes. Thus it
replays the packaged numerical evidence, while full-source verification has
the separate prerequisites below. The numerical tolerances are absolute
`1e-7` and relative `1e-10`.

## Full-source primary QA

Use a separate fresh extraction for this section. Restore the retained
original compact HDF5 to the exact workspace-relative `seti_raw/` paths in
the package manifest's `excluded_original_HDF5` list. Their original files
come from:

- `SETI_S2017_NATIVE171_RAW_2026-10-10.zip`
- `SETI_S2017_NATIVE170_172_RAW_2026-10-10.zip` (or its assembled part01–part03)

The original primary QA requires the nine ON compacts: three native pieces
170/171/172 in each of `epoch1_on`, `epoch2_on`, `epoch3_on`. The full fixed
context QA requires all 18 ON/OFF compacts and all 288 decoded rows. Correct
file sizes and SHA256 are necessary; renamed or reconstructed alternatives
are not admitted. The archive itself cannot provide these excluded raw files.

The primary QA always writes `seti_burst_on/qa_results`. In this separate
extraction, preserve the delivered QA as `delivered_primary_qa_results` before
creating a fresh audit. Do this only after the manifest verification above:

```bash
.venv/bin/python - <<'PY'
import hashlib, subprocess, sys
from pathlib import Path
root = Path('.').resolve()
base = 'seti_burst_on/'
delivered = root / base / 'qa_results'
preserved = root / base / 'delivered_primary_qa_results'
assert delivered.is_dir() and not preserved.exists()
delivered.rename(preserved)
def sha(name):
    return hashlib.sha256((root / name).read_bytes()).hexdigest()
command = [sys.executable, base + 'qa.py', '--root', str(root),
           '--scope-sha256', sha(base + 'SCOPE.json'),
           '--qa-sha256', sha(base + 'qa.py'),
           '--root-go-sha256', sha(base + 'QA_ROOT_GO.json')]
for job in ('on20170428_epoch1_HIP98505', 'on20170428_epoch2_HIP98505',
            'on20170428_epoch3_HIP98505'):
    command += ['--primary-receipt', job + '=' + sha(base + 'results/' + job + '/EXECUTION_RECEIPT.json')]
subprocess.run(command, check=True)
PY
```

Expected primary-QA status:
`PASS288_ON_BURST4_MAPS1170_RAW4X503_QUERIES144_SOURCE_ROWS_NO_GRID_RERUN`.
This checks saved winners and rankings, all 1,170 audit scores, source file and
decoded-row pins, raw core medians, and full501 normalization on the selected
TOP3 cores. It does not independently rerun the exhaustive maximization or
its tie order.

## Full-source context QA

Use another fresh extraction with all 18 exact raw HDF5 compacts restored.
Keep the original primary QA receipt in place. The delivered context QA can
remain in place because a separate fresh output directory is supported:

```bash
.venv/bin/python - <<'PY'
import hashlib, subprocess, sys
from pathlib import Path
root = Path('.').resolve()
base = 'seti_burst_on/'
def sha(name):
    return hashlib.sha256((root / name).read_bytes()).hexdigest()
command = [sys.executable, base + 'context_qa.py', '--root', str(root),
           '--output-dir', base + 'fresh_full_source_context_replay',
           '--scope-sha256', sha(base + 'CONTEXT_SCOPE.json'),
           '--qa-sha256', sha(base + 'context_qa.py'),
           '--receipt-sha256', sha(base + 'context_results/EXECUTION_RECEIPT.json'),
           '--root-go-sha256', sha(base + 'CONTEXT_QA_GO.json')]
subprocess.run(command, check=True)
PY
```

Expected status:
`PASS54_FIXED_SIX_SCAN_PROFILES9_OWN_SCORES_ALL_FULL501_NORMALIZATIONS`.
This adds exact original HDF5 file/decoded-row and raw crop/profile verification
to the portable checks. All numerical audit processes retain their frozen
600 CPU-second, 900 wall-second and 2 GiB address-space limits. Replays create
new receipts; their run-time measurements and output hashes may differ from
the original receipts.

## Package assembly recipe

The following metadata/opaque-byte command can be used on a completed work
directory with all exact producer and full-source QA receipts. It refuses
incomplete outcomes and never loads an NPZ array or HDF5 dataset:

```bash
python3.12 seti_burst_on/package.py --root . --preflight
python3.12 seti_burst_on/package.py --root . --build --output SETI_ON_BURST4_2026-10-13.zip
```

Assembly includes all 288 primary maps and 1,170 audit capsules, the context
profiles/crops, code, current scopes/reviews/receipts and the minimal original
metadata dependencies. It checks all included file byte pins, verifies ZIP
CRC and writes a sibling manifest. It preserves existing files and requires
a fresh archive destination. No source HDF5, runtime wheels, lock/cache files
or existing archives are included.

Report regeneration (optional): `python3 seti_burst_on/make_report.py` needs NumPy, Matplotlib, ReportLab, DejaVu fonts and all included JSON receipts. The exact DC source-QA receipt is included in `seti_burst_on/report_dependencies/DC_SOURCE_QA_RECEIPT.json`; no original HDF5 file is read by report generation.
