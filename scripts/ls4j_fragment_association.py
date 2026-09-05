#!/usr/bin/env python3
"""Post-LS4I fragment-local recovery accounting; unchanged detector and vetoes."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import lzma
import math
from pathlib import Path
import shutil
import tempfile

from seti_repeater import light_sail as ls
from ls4i_measured_digital_injections import (encoded, write_json, bilateral_overlap,
    associated, trial_specs, truth_geometry, collect_bands, read_htr, evaluate_htr)
from ls4f_v2_native_reanalysis import download_exact, numeric_agreement

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results_ls4j_fragment_association'
KEYS = ('frequency_index', 'window_index', 'pulse_width_s', 'medium_amplitude')


def load(path):
    p = ROOT/path
    raw = p.read_bytes()
    if p.suffix == '.xz': raw = lzma.decompress(raw)
    if p.suffix == '.gz': raw = gzip.decompress(raw)
    return json.loads(raw)


def fragment_associated(event, truth, base_width, threshold=.5):
    """A resolved portion of the truth, not recovery of its complete bandwidth."""
    if not math.isfinite(base_width) or base_width <= 0 or not 0 < threshold <= 1:
        raise ValueError('invalid association parameters')
    for item in (event, truth):
        for axis, unit in (('time', 's'), ('frequency', 'mhz')):
            lo, hi = item[f'{axis}_start_{unit}'], item[f'{axis}_stop_{unit}']
            if not all(math.isfinite(x) for x in (lo, hi)) or hi <= lo:
                raise ValueError('invalid event/truth geometry')
    overlap = max(0., min(event['frequency_stop_mhz'], truth['frequency_stop_mhz']) -
                  max(event['frequency_start_mhz'], truth['frequency_start_mhz']))
    event_width = event['frequency_stop_mhz'] - event['frequency_start_mhz']
    truth_width = truth['frequency_stop_mhz'] - truth['frequency_start_mhz']
    return (bilateral_overlap(event['time_start_s'], event['time_stop_s'],
                              truth['time_start_s'], truth['time_stop_s']) >= threshold and
            overlap >= threshold * event_width and
            overlap >= threshold * min(base_width, truth_width))


def candidates(search, off_search, detector):
    if search['retention_truncated'] or off_search['retention_truncated']:
        raise ValueError('truncated event retention')
    return ls.apply_abacad_veto([
        {'label':'A1', 'role':'ON', 'adjacent_off_labels':['B1'], 'search':search},
        {'label':'B1', 'role':'OFF', 'adjacent_off_labels':[], 'search':off_search}],
        on_threshold=detector['on_score_threshold'], off_threshold=detector['off_veto_score_threshold'],
        minimum_frequency_overlap=detector['off_veto_frequency_overlap'])


def select(items, truth, config):
    matches = [c for c in items if fragment_associated(c['event'], truth,
                config['base_bin_width_mhz'], config['association_threshold'])]
    if len(matches) > config['resource']['max_associated_events_per_trial']:
        raise ValueError('association cap exceeded; no truncation permitted')
    return matches


def decoys(truth, config):
    # The other original envelope, and adjacent disjoint bands, are controls.
    other = next(w for w in config['envelopes_s'] if w[0] != truth['time_start_s'])
    for time_shift, frequency_shift in config['decoy_offsets']:
        start, stop = other if time_shift else (truth['time_start_s'],truth['time_stop_s'])
        yield {'time_start_s':start,'time_stop_s':stop,
               'frequency_start_mhz':truth['frequency_start_mhz']+frequency_shift,
               'frequency_stop_mhz':truth['frequency_stop_mhz']+frequency_shift}


def verify():
    for manifest in ('LS4I_FREEZE.sha256','LS4J_FREEZE.sha256'):
        for line in (ROOT/manifest).read_text().splitlines():
            expected,path = line.split('  ',1)
            if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
                raise ValueError('freeze mismatch: '+path)
    config = load('config/ls4j_fragment_association.json')
    for path, expected in config['input_sha256'].items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != expected:
            raise ValueError('input identity mismatch: '+path)
    return config


def stage1(config):
    OUT.mkdir(exist_ok=False)
    a = load('results_ls4i_measured_digital_injections/A1_medium.json.xz')
    b = load('results_ls4i_measured_digital_injections/B1_medium.json.xz')
    old = load('config/ls4b_lhs1140_x_light_sail.json')
    detector = old['medium_resolution_screen']
    if len(a['trials']) != 36 or not a['historical_replay_agrees'] or not b['historical_replay_agrees']:
        raise ValueError('incomplete or invalid source study')
    trials, baselines = [], []
    for baseline in (False,True):
        source = ([{**s,'truth':truth_geometry(s,config),'search':a['baseline_search']}
                   for s in trial_specs(config,include_zero=True)] if baseline else a['trials'])
        destination = baselines if baseline else trials
        for trial in source:
            items = candidates(trial['search'], b['baseline_search'], detector)
            matches = select(items,trial['truth'],config)
            old_matches = [c for c in items if associated(c['event'],trial['truth'],.5)]
            if not baseline and old_matches != trial['matched_events']:
                raise ValueError('LS4I legacy association replay differs')
            controls = []
            for truth in decoys(trial['truth'],config):
                chosen = select(items,truth,config)
                controls.append({'truth':truth,'matched_event_indices':[items.index(c) for c in chosen],
                                 'survivor_count':sum(c['survives_adjacent_off_veto'] for c in chosen)})
            destination.append({**{k:trial[k] for k in KEYS},'truth':trial['truth'],
                                'legacy_match_count':len(old_matches),'matched_events':matches,'decoy_controls':controls})
    bands = collect_bands(trials,baselines,config,load('config/ls4c_lhs1140_x_htr_followup.json')['expected_filterbank_header'])
    result = {'status':'fragment-association-stage1-complete','trials':trials,'baselines':baselines,
              'htr_band_indices':bands,'new_spectral_bytes_read':0,
              'freeze_sha256':hashlib.sha256((ROOT/'LS4J_FREEZE.sha256').read_bytes()).hexdigest()}
    result['result_sha256'] = hashlib.sha256(encoded(result)).hexdigest()
    (OUT/'stage1.json.gz').write_bytes(gzip.compress(encoded(result),mtime=0))
    summary = {'matched_cells':sum(bool(t['matched_events']) for t in trials),
               'surviving_cells':sum(any(c['survives_adjacent_off_veto'] for c in t['matched_events']) for t in trials),
               'matched_events':sum(len(t['matched_events']) for t in trials),
               'surviving_events':sum(c['survives_adjacent_off_veto'] for t in trials for c in t['matched_events']),
               'decoy_matched_regions':sum(bool(c['matched_event_indices']) for t in trials for c in t['decoy_controls']),
               'decoy_surviving_regions':sum(c['survivor_count']>0 for t in trials for c in t['decoy_controls']),
               'baseline_matched_cells':sum(bool(t['matched_events']) for t in baselines),
               'baseline_surviving_cells':sum(any(c['survives_adjacent_off_veto'] for c in t['matched_events']) for t in baselines),
               'htr_unique_bands':len(bands),'stage1_result_sha256':result['result_sha256']}
    if summary['surviving_events'] == 0:
        summary.update({'followup_status':'not-run-no-stage1-survivors','paired_passes':0,'paired_configurations':144,
                        'candidate_conditioned_htr_evaluations':0,'new_spectral_bytes_read':0})
    else:
        summary['followup_status'] = 'selected-event-htr-required'
    write_json(OUT/'summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)


def followup(config):
    stage = load('results_ls4j_fragment_association/stage1.json.gz')
    identity = stage.pop('result_sha256')
    if hashlib.sha256(encoded(stage)).hexdigest() != identity:
        raise ValueError('stage1 checkpoint identity mismatch')
    if stage['freeze_sha256'] != hashlib.sha256((ROOT/'LS4J_FREEZE.sha256').read_bytes()).hexdigest():
        raise ValueError('stage1 freeze identity mismatch')
    summary = load('results_ls4j_fragment_association/summary.json')
    if summary['followup_status'] != 'selected-event-htr-required':
        raise ValueError('HTR not required or already finished')
    if (OUT/'htr.json.gz').exists() or (OUT/'source_receipts.json').exists() or (OUT/'abort.json').exists():
        raise ValueError('existing execution evidence; refuse overwrite or unbudgeted repeat')
    oldh = load('config/ls4c_lhs1140_x_htr_followup.json')
    settings = load('config/ls4e_residual_qualification.json')['settings']
    bands = [tuple(b) for b in stage['htr_band_indices']]
    rawdir = Path(tempfile.mkdtemp(prefix='setisearch-ls4j-',dir='/tmp'))
    receipts, htr, charged = [], {}, 0
    try:
        for source in config['sources']:
            path = rawdir/'source.fil'; errors=[]
            for attempt in range(config['resource']['attempts_per_source']):
                charged += source['source_size_bytes']
                if charged > config['resource']['max_total_download_bytes']:
                    raise ValueError('download budget exceeded')
                try:
                    receipt=download_exact(source,path,config); break
                except Exception as exc:
                    errors.append(str(exc))
                    if attempt+1 == config['resource']['attempts_per_source']: raise
            try:
                htr[source['label']] = read_htr(path,source,oldh,bands,config)
            finally:
                path.unlink(missing_ok=True)
            receipts.append({**receipt,'label':source['label'],'product':source['product'],
                             'raw_file_deleted':True,'prior_attempt_errors':errors})
            write_json(OUT/'source_receipts.json',{'sources':receipts,'charged_download_bytes':charged})
            print('Processed and deleted '+source['label'],flush=True)
        result=evaluate_htr(htr['A1'],htr['B1'],stage['trials'],stage['baselines'],config,oldh['expected_filterbank_header'],settings)
        previous=load('results_ls4i_measured_digital_injections/injections.json.gz')
        if not numeric_agreement(result['fixed_window_diagnostics'],previous['fixed_window_diagnostics'],**config['replay_tolerance']):
            raise ValueError('fixed-window LS4I diagnostic replay differs')
        if len(result['paired_configurations'])!=144 or len(result['uninjected_baselines'])!=12:
            raise ValueError('incomplete paired grid')
        result.update({'status':'selected-event-htr-complete','stage1_result_sha256':identity,'fixed_window_replay_agrees':True})
        result['result_sha256']=hashlib.sha256(encoded(result)).hexdigest()
        (OUT/'htr.json.gz').write_bytes(gzip.compress(encoded(result),mtime=0))
        summary.update({'followup_status':result['status'],'paired_passes':sum(r['joint_digital_pass'] for r in result['paired_configurations']),
                        'paired_configurations':144,'candidate_conditioned_htr_evaluations':sum(len(r['events']) for r in result['paired_configurations']),
                        'new_spectral_bytes_read':sum(r['bytes'] for r in receipts),'htr_result_sha256':result['result_sha256']})
        write_json(OUT/'summary.json',summary);print(json.dumps(summary,indent=2),flush=True)
    except Exception as exc:
        write_json(OUT/'abort.json',{'status':'aborted-no-complete-htr-conclusion','error':str(exc),'charged_download_bytes':charged,'sources':receipts})
        raise
    finally:
        shutil.rmtree(rawdir)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('stage1','htr'))
    args=parser.parse_args();config=verify()
    (stage1 if args.phase=='stage1' else followup)(config)
