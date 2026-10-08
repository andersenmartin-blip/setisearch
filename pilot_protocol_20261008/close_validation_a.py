"""Close existing fresh A evidence; never generate controls or run a search."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'results/radio_pilot_validation_a_20261008'
DEST = ROOT / 'pilot_protocol_20261008'

def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def main():
    completion = json.loads((BASE / 'completion.json').read_text())
    if len(completion['results']) != 142:
        raise ValueError('The once-only coordinator must close all 142 attempted identities')
    cases = json.loads((ROOT / 'pilot_controls_20261008/validation_a_cases.json').read_text())
    outcomes = [json.loads((BASE / f'case_{i:03d}/outcome.json').read_text()) for i in range(142)]
    if [x['case_id'] for x in outcomes] != [c['case_id'] for c in cases]:
        raise ValueError('Original order and all 142 distinct identities required')
    summarizer_path = ROOT / 'pilot_controls_20261008/summarize.py'
    if hashlib.sha256(summarizer_path.read_bytes()).hexdigest() != '6f9153d8c598eb6bb897d0a00dc632906a00ed203c876902fca955b1b7e4b361':
        raise ValueError('Frozen summarizer changed')
    spec = importlib.util.spec_from_file_location('closed_A_summarizer', summarizer_path)
    summarizer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(summarizer)
    summary = summarizer.summarize(cases, outcomes, 'VAL_A')
    receipts = [json.loads((BASE / f'case_{i:03d}/resource_receipt.json').read_text()) for i in range(142)]
    receipt_cpu_sum = sum(float(x['cpu_s']) for x in receipts)
    charged = max(receipt_cpu_sum, float(completion['children_CPU_s'])) + float(completion['controller_CPU_s'])
    ledger = {
        'status': 'CLOSED_ALL_142_ATTEMPTS_ONCE_ONLY', 'case_count': 142,
        'all_returncodes_zero': completion['all_returncodes_zero'],
        'all_job_resource_caps_passed': all(x['caps_passed'] for x in receipts),
        'sum_whole_case_CPU_s': receipt_cpu_sum,
        'parent_children_CPU_s': completion['children_CPU_s'],
        'controller_CPU_s': completion['controller_CPU_s'],
        'charged_CPU_s': charged,
        'accounting': 'max(sum whole child receipts, parent reaped children CPU) + whole controller CPU; includes failed/successful startup and output finalization',
        'reserved_CPU_s': 35500, 'refunded_unused_CPU_s': 35500 - charged,
        'CPU_remaining_before_A_s': 36635.758461981,
        'CPU_remaining_after_A_s': 36635.758461981 - charged,
        'largest_case_wall_s': max(float(x['wall_s']) for x in receipts),
        'largest_case_peak_rss_bytes': max(int(x['peak_rss_bytes']) for x in receipts),
        'coordinator_wall_s': completion['wall_s'],
        'exclusive_case_CPU_cap_s': 250, 'case_wall_cap_s': 1800,
        'case_RSS_cap_bytes': 4 * 1024**3,
        'historical_CI_CPU_charge_s': 4800, 'historical_CI_measured_CPU_available': False,
        'other_unmeasured_preparation_CPU_is_not_claimed_zero': True,
        'VAL_B_generated': False, 'telescope_values_opened': False,
    }
    write(DEST / 'validation_a_complete_outcomes.json', outcomes)
    write(DEST / 'validation_a_complete_summary.json', summary)
    write(DEST / 'validation_a_complete_resource_receipt.json', ledger)
    print(json.dumps({'scientific_gate': summary['scientific_gate'], 'checks': summary['checks'], 'families': summary['families'], 'charged_CPU_s': charged, 'remaining_CPU_s': ledger['CPU_remaining_after_A_s']}))

if __name__ == '__main__':
    main()
