"""Metadata-only executable freeze; no M43AF descriptors or null scores."""
import gzip
import importlib.metadata
import json
import platform
from pathlib import Path

from m43e_economical_bank import read_sealed
from m43ae_joint_response import sha
from m43af_verify_design import verify
from seti_repeater.detector_m43u import digest

ROOT = Path(__file__).resolve().parents[1]


def overlay_ids(value):
    if isinstance(value, dict):
        if 'patch_payloads' in value and 'background_provenance' in value:
            yield digest({k:value[k] for k in ('patch_payloads', 'background_provenance')})
        for child in value.values():
            yield from overlay_ids(child)
    elif isinstance(value, list):
        for child in value:
            yield from overlay_ids(child)


def main():
    verify()
    ae = json.loads((ROOT/'config/m43ae_joint_response.json').read_text())
    draft = json.loads((ROOT/'config/m43af_prospective_design_draft.json').read_text())
    result = read_sealed(ROOT/'results_m43ae_joint_response/result.json')
    history = {r['name']:r for r in result['inventory']}
    paths = set(ae['pinned_sha256']) | {
        'config/m43ae_joint_response.json', 'results_m43ae_joint_response/result.json',
        'config/m43af_prospective_design_draft.json',
        'MILESTONE_43AF_EXECUTABLE_PROTOCOL.md', 'scripts/m43af_freeze_config.py',
        'scripts/m43af_response_study.py', 'scripts/m43af_study_audit.py',
        'scripts/m43af_scalar_audit.py', 'scripts/m43af_verify_design.py',
        'src/seti_repeater/response_m43af.py', 'src/seti_repeater/acquisition_m43af.py',
        'src/seti_repeater/boundary_m43af.py', 'src/seti_repeater/native_null_m43af.py',
        'tests/test_m43af_response.py', 'tests/test_m43af_acquisition.py',
        'tests/test_m43af_boundary.py', 'tests/test_m43af_native_null.py',
        'tests/test_m43af_study_audit.py', 'results_m43af_response/focused_tests.log'}
    paths.update(r['file'] for r in history.values())
    prior = set(ae['previous_native_payload_identities'])
    prior.update(r['native_payload_identity'] for r in history.values())
    extra_paths = list(ROOT.glob('results_m43*/case_audits.jsonl.gz'))
    for directory in ('results_m43aa_native_response', 'results_m43ab_attribution',
                      'results_m43ad_geometry', 'results_m43ae_joint_response'):
        extra_paths.extend((ROOT/directory/'inputs').glob('*.json.gz'))
    for path in sorted(set(extra_paths)):
        paths.add(str(path.relative_to(ROOT)))
        if path.name.endswith('.jsonl.gz'):
            with gzip.open(path, 'rt') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        seal = record.pop('result_sha256')
                        assert digest(record) == seal, str(path)
                        prior.update(overlay_ids(record))
        else:
            prior.update(overlay_ids(read_sealed(path)))
    cfg = dict(milestone='M43AF', source_commit='068541aa2aff5baf1564b8889051002cd7e3a3e0',
        python_version=platform.python_version(),
        dependencies={n:importlib.metadata.version(n) for n in ('numpy', 'astropy', 'h5py', 'hdf5plugin')},
        parent_template_indices=ae['parent_template_indices'], grid_sha256=ae['grid_sha256'],
        training_cases=draft['cases']['training'], validation_cases=draft['cases']['validation'],
        training_native_shifts=draft['training_shifts'], heldout_native_shifts=draft['heldout_shifts'],
        previous_shift_rows=draft['excluded_prior_shifts'], previous_shift_row_count=1792,
        null_operator='D_e(row,k)=B_e(row,k+s_e), paired ON/OFF, after fixed normalization, no wrap',
        old_circular_score_nulls_reused_as_new_measurements=False,
        historical_sources=history, previous_native_payload_identities=sorted(prior),
        comparison_references=['neighbor9', 'centered_receiver_off_match_aggregate',
            'geometry_receiver_off_aggregate', 'geometry_receiver_aligned_off_aggregate'],
        maximum_records=ae['maximum_records'], new_observing_sequences=0,
        pinned_sha256={p:sha(ROOT/p) for p in sorted(paths)})
    (ROOT/'config/m43af_response_study.json').write_text(json.dumps(cfg, separators=(',', ':'))+'\n')
    print(json.dumps(dict(pinned_files=len(paths), prior_native_identities=len(prior),
        prior_shift_rows=1792, training_inputs=112, validation_inputs=112, historical_with_baseline=262,
        training_native_nulls=128, heldout_native_nulls=128, new_scientific_measurements=0)))


if __name__ == '__main__':
    main()
