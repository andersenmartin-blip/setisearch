"""Prepare prospective remaining-domain dual ON burst scope from frozen text only."""
from __future__ import annotations
import argparse
import importlib.util
from pathlib import Path
import sys

BASE = 'seti_burst_full'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path('.'))
    p.add_argument('--extra-text-pin', action='append', default=[],
                   help='Additional final source/review path; code and metadata only')
    args = p.parse_args()
    root = args.root.resolve()
    spec = importlib.util.spec_from_file_location('full_on_burst_scope_driver', root / BASE / 'driver.py')
    d = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = d
    spec.loader.exec_module(d)
    names = [*d.PINS, BASE + '/driver.py', BASE + '/prepare_scope.py', *args.extra_text_pin]
    pilot_manifests = []
    completed_pilots = []
    for primary, (scan, target) in d.SCANS.items():
        parent = d.PILOT + '/results/' + primary
        receipt = parent + '/EXECUTION_RECEIPT.json'
        manifest = parent + '/MAPS.json'
        names.extend([receipt, manifest])
        rec = d.read_json(root / receipt)
        d.require(rec['status'] == 'COMPLETE_96_NEW_ON_BURST4_COMBINED_MAPS_EXPLORATORY_ONLY'
                  and rec['scan_id'] == scan and rec['counts']['maps'] == 96,
                  'Exact complete96pilotmaps per originalON required')
        pilot_manifests.append(d.byte_pin(root, d.confined(root, manifest)))
        completed_pilots.append({'primary_scan_id': primary, 'scan_id': scan,
            'execution_receipt': d.byte_pin(root, d.confined(root, receipt)),
            'maps': 96, 'process_CPU_seconds': rec['process_CPU_seconds'], 'wall_seconds': rec['wall_seconds']})
    pins = [d.byte_pin(root, d.confined(root, name)) for name in dict.fromkeys(names)]
    d.require(all(Path(pin['path']).suffix in ('.py', '.json', '.md', '.txt') for pin in pins), 'Text only preparation')
    sources = d.source_records(root)
    d.require(len(sources) == 9 and sources == d.read_json(root / d.PILOT / 'SCOPE.json')['source_compacts'],
              'Reuse same exact nine authenticated ON compacts')
    d.require(all(d.confined(root, r['path']).is_file() and d.confined(root, r['path']).stat().st_size == r['bytes']
                  for r in sources), 'Relocated raw source sizes differ')
    scope = {**d.method_contract(), 'text_code_pins': pins, 'source_compacts': sources,
             'pilot_map_manifests': pilot_manifests, 'previous_completed_pilots': completed_pilots,
             'output_directory_template': BASE + '/results/<primary_id>',
             'conservative_max_job_output_bytes': 96 * (340 * 1024 + 4000 + 5 * 11000)
                                                + 2 * 800 * 1024 + 4 * 1024**2,
             'resource_basis': 'Completed original pilot96core CPU217.7..278.2s perjob. Same detector159drift sevenwindow score arithmetic once/core. Unaffected cleanmax mirrors original winner updates; onlyq127/128cores extra cachedDCeligibility/remax updates.96core perjob,600CPU900wall2GiB conservative bound.',
             'source_values_opened_in_preparation': False, 'raw_bytes_hashed_in_preparation': False,
             'root_GO_status_required': 'GO_2010_NEW_FULL_ON_DUAL_BURST4_MAPS',
             'public_freeze_status_required': 'PASS_PUBLIC_FREEZE_FULL_ON_DUAL_BURST4_SCOPE_READBACK',
             'public_freeze_file_required': BASE + '/freeze.json',
             'planned_independent_QA': {'maps_census': 2010, 'scalar_core_audits': 10050,
                                       'DC_affected_cores_exhaustively_remaxed': 18,
                                       'DC_full_raw_normalization_reproduced': 18,
                                       'other_cores_not_independently_exhaustively_remaxed': True},
             'interpretation_limitations': [
                 'Same exposed historical visit and source target.ThreeONscan positions are not independent visits or blind validation.',
                 'Remaining-domain coverage and best DC-untouched original hypothesis family are new analyses.No new telescope bandwidth or observations.',
                 'Score maxima over correlated hypotheses are not calibrated SNR/FAP, flux, EIRP or astrophysical detections.',
                 'DC-free boxes do not establish freedom from RFI or other receiver structure.All16row original normalization remains unchanged.',
                 'Pilot96domains perON are reused later under their original bytepins, never recalculated.',
                 'Exactly9 expected cleanEMPTY carrier records remain explicit, including -inf/nan sentinels; no automatic replacement or drift snapping.',
                 'No shard-levelTOP3 followup.Global766domain ranking perON requires all21complete shards plus288pilotmaps and independentQA.']}
    d.require(scope['conservative_max_job_output_bytes'] < d.CAPS['job_output_budget_bytes'], 'Prospective job budget invalid')
    d.contract(root, scope)
    output = root / BASE / 'SCOPE.json'
    d.save(output, scope)
    d.save(root / BASE / 'PREPARATION_RECEIPT.json', {
        'schema': 'SETI_FULL_ON_DUAL_BURST4_PREPARATION_V1', 'status': 'PASS_TEXT_ONLY_2010_NEW_DUAL_MAP_SCOPE',
        'scope': d.byte_pin(root, output), 'source_compacts': 9, 'decoded_rows_declared': 144,
        'jobs': 21, 'remaining_domains_per_ON': 670, 'maps': 2010, 'reused_pilot_maps': 288,
        'new_carrier_maximum_records': 2010 * 4096, 'new_valid_hypothesis_records': 2010 * 4096 * 2226,
        'score_audit_queries': 10050, 'DC_full_raw_core_crops': 18, 'expected_clean_EMPTY_carriers': 9,
        'numerical_modules_imported': False, 'source_values_opened': False,
        'raw_bytes_hashed': False, 'new_telescope_HTTP_requests': 0})
    print(d.byte_pin(root, output))


if __name__ == '__main__':
    main()
