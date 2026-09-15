#!/usr/bin/env python3
"""Reconcile saved electronics with the fixed calibration-log block, offline."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

from astropy.io import fits

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT/'results_ls7v_reduction_log'
LOG_SHA = '28170dd5716e5cfaf0f6cfa67c2de9d6324be880a82379e08e4043f7b84bbd9a'


def sha(body):
    return hashlib.sha256(body).hexdigest()


def save(path,obj):
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def one(pattern,text):
    values = re.findall(pattern,text,re.MULTILINE)
    if len(values) != 1:
        raise ValueError(f'Expected one log field for {pattern!r}; got {len(values)}')
    return values[0]


def header(relative_path):
    return fits.Header.fromtextfile(ROOT/relative_path)


def reconcile(out):
    out.mkdir(parents=True,exist_ok=True)
    provenance = json.loads((INPUT/'provenance.json').read_text())
    assert sha((ROOT/'LS7V_SCOPE.md').read_bytes()) == provenance['scope_sha256']
    for entry in provenance['reused_input_identities']:
        body = (ROOT/entry['path']).read_bytes()
        assert len(body) == entry['bytes'] and sha(body) == entry['sha256']
    compressed = (INPUT/'pipeline.log.gz').read_bytes()
    assert sha(compressed) == provenance['compressed_sha256']
    original = gzip.decompress(compressed)
    assert len(original) == 60868 and sha(original) == LOG_SHA
    old = json.loads((ROOT/'results_ls7r_metadata/calibration_log_extract.json').read_text())
    assert old['log_bytes'] == len(original) and old['log_sha256'] == LOG_SHA
    assert old['headers'] == provenance['original_http_headers']
    lines = original.decode('utf-8').splitlines()
    selected = [{'line':i,'text':lines[i-1]} for i in range(75,97)]
    text = '\n'.join(x['text'] for x in selected)
    assert set(re.findall(r'main_calibration\.py (\S+)',text)) == {'14.0.1'}
    assert not re.search(r'photometry|light.?curve|source flux|main_correction',text,re.I)
    source = {'observation_id':int(one(r'Observation ID is (\d+)',text)),
        'calibration_module_version':'14.0.1',
        'read_mode':one(r'Read Mode is (\w+)',text),
        'read_frequency_hz':int(one(r'Read Frequency is (\d+)',text)),
        'read_channel':one(r'Read HW channel is (\w+)',text),
        'read_script':int(one(r'Read Script is (\d+)',text)),
        'stacking':one(r'Staking way in the data is (\w+)',text),
        'bias_policy':one(r'Bias correction, (using defaults)\.',text),
        'reported_ccd_temperature_degC':float(one(r'measured Tccd ([+-]?\d+\.\d+)°C',text)),
        'rounded_ccd_temperature_degC':int(one(r'rounded to ([+-]?\d+)°C',text)),
        'default_bias_decimal':one(r'Default bias\s+(\d+\.\d+) adu/frame',text),
        'default_ron_decimal':one(r'Default\s+ron\s+(\d+\.\d+) adu/frame',text),
        'default_unit_literal':'adu/frame',
        'spatial_bias_frame':one(r'Bias correction frame (skipped)',text),
        'reported_gain_approx_e_per_adu':float(one(r'Gain correction completed, gain ~(\d+\.\d+) e-/adu',text)),
        'dark_mode':one(r'Dark correction mode: (\w+)',text),
        'dark_file':Path(one(r'Using dark frame: ([^\n]+)',text)).name,
        'dark_map_applied':bool(re.search(r'Dark correction: pix to pix completed',text)),
        'linearization_logged':bool(re.search(r'\[I\] Linearization$',text,re.M)),
        'flat_field_step_logged':bool(re.search(r'\[I\] Flat Field Correction$',text,re.M))}
    raw = header('results_ls7r_metadata/SCI_RAW_SubArray_hdu01_header.txt')
    cal = header('results_ls7r_metadata/SCI_CAL_SubArray_hdu01_header.txt')
    cor = header('results_ls7r_metadata/SCI_COR_SubArray_hdu01_header.txt')
    pairs = [('OBSID','observation_id'),('RO_FREQU','read_frequency_hz'),
             ('RO_HW','read_channel'),('RO_SCRPT','read_script'),('STACKING','stacking')]
    comparisons = []
    for name, field in pairs:
        for stage,h in [('RAW',raw),('CAL',cal),('COR',cor)]:
            assert h[name] == source[field], (stage,name)
            comparisons.append({'stage':stage,'card':name,'value':h[name],'matches_log':True})
    assert cal['RF_FIL7'] == cor['RF_FIL7'] == source['dark_file']
    assert cal['DARK'] == cor['DARK'] == 'completed'
    assert cal['FFIELD'] == cor['FFIELD'] == 'completed'
    assert cal['RF_FIL4'] == cor['RF_FIL4'] == 'CH_TU2019-12-18T00-00-00_REF_APP_BiasFrame_V0109.fits'
    assert raw['NEXP'] == 14
    # Named references and coarse step labels do not prove every substep ran.
    source['bias_reference_named_in_header'] = cal['RF_FIL4']
    source['cal_bias_ron_step_header'] = cal['BIAS_RON']
    source['cal_image_bunit_literal'] = cal['BUNIT']
    source['cor_image_bunit_literal'] = cor['BUNIT']

    history = json.loads((ROOT/'results_ls7s_calibration/summary.json').read_text())
    primary = json.loads((ROOT/'results_ls7u_prescan/summary.json').read_text())
    blank = json.loads((ROOT/'results_ls7u_prescan/blank_reference/summary.json').read_text())
    defaults = []
    for column,key,measurement,interval_key in [
        ('BIAS','default_bias_decimal','bias_per_readout_adu','bias_per_readout_adu_interval'),
        ('RON','default_ron_decimal','effective_read_noise_per_readout_adu','noise_per_readout_adu_interval')]:
        recorded = history['cal_cor_equal_metadata'][column]
        assert recorded['minimum'] == recorded['maximum']
        decimal = float(source[key])
        binary32 = struct.unpack('>f',struct.pack('>f',decimal))[0]
        assert binary32 == recorded['minimum']
        assert binary32 == primary['cal_cor_values_without_native_unit_cards'][column]
        interval = primary['bootstrap'][interval_key]
        defaults.append({'column':column,'logged_decimal':source[key],
            'logged_unit':'adu/frame','saved_cal_cor_value':binary32,
            'binary32_hex':struct.pack('>f',decimal).hex(),
            'binary32_promotion_exact_match':True,
            'primary_prescan_measurement':primary['primary'][measurement],
            'cal_minus_primary_adu_per_readout':binary32-primary['primary'][measurement],
            'primary_descriptive_interval':interval,
            'cal_inside_primary_descriptive_interval':interval[0]<=binary32<=interval[1]})
    result = {'checkpoint':'LS7V','file_key':provenance['file_key'],
        'study_type':'Forensic reconciliation of existing calibration provenance',
        'input_decision':'NOT_READY_FOR_TARGET_IMAGE_STUDY',
        'source_log_sha256':LOG_SHA,'source_log_bytes':len(original),
        'analyzed_log_lines':[75,96],'scope_sha256':provenance['scope_sha256'],
        'source_facts':source,'header_identity_comparisons':comparisons,
        'electronics_default_reconciliation':defaults,
        'ls7u_primary_reused_unchanged':primary['primary'],
        'ls7u_blank_reused_unchanged':blank['pipe_gain_one_adu'],
        'resolutions':[
            'The CAL/COR electronics numbers reproduce the logged defaults exactly after binary32 promotion.',
            'The log explicitly labels those defaults adu/frame. They are not a result to match by retuning the LS7U margin estimators.',
            'The named bias-frame input was skipped in this recorded calibration path; its contents are not required to replay an unapplied correction.',
            'The dark map was explicitly applied, so its content and early-visit applicability remain relevant.'],
        'limits':[
            'Binary32 equality does not prove an internal DRP numeric type or reproduce the entire program.',
            'The frame in the reported unit is consistent with LS7U per-readout scaling; the full stack/nonlinear operator still needs version-relevant documentation.',
            'The approximate gain ~2.0 does not identify an exact formula, inputs or rounding implementation.',
            'The native CAL/COR image headers say ADU. A logged gain conversion alone does not establish final image-unit semantics.',
            'A skipped spatial bias correction does not prove physical pixel-dependent bias is negligible for a different estimator.',
            'No native gcoadd definition, missing reference contents or source response is recovered from this log.'],
        'audit':{'source_identity_verified':True,'historical_input_identities_verified':len(provenance['reused_input_identities']),
            'header_identity_matches':len(comparisons),'exact_default_value_matches':len(defaults),
            'selected_log_lines':len(selected),'historical_row_census_repeated':False},
        'new_transfer_bytes':0,'new_electronic_reference_array_bytes':0,
        'target_image_bytes':0,'native_source_residual_trials':0,'pulse_recovery_trials':0,
        'new_candidates':0,'new_qualified_observing_seconds':0,
        'software':{'python':sys.version.split()[0]}}
    save(out/'selected_calibration_lines.json',{'source_log_sha256':LOG_SHA,'lines':selected})
    save(out/'summary.json',result)
    print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=INPUT)
    args = parser.parse_args()
    reconcile(args.output)
