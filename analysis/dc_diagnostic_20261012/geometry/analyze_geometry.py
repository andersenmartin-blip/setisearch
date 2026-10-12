#!/usr/bin/env python3
"""Post-selection metadata-only geometry; no source spectra, scores or grids."""
import time
START_WALL = time.perf_counter()
START_CPU = time.process_time()
import ast
import hashlib
import json
import resource
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BASE = ROOT / 'seti_previous'
N = 2**20
CENTERS = [178782208, 179830784, 180879360]
INPUTS = {}

def pin_read(path, as_json=True):
    raw = path.read_bytes()
    INPUTS[str(path.relative_to(ROOT))] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    return json.loads(raw) if as_json else raw.decode()

manifest = pin_read(BASE/'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json')
summary = pin_read(BASE/'analysis/s2017_control_targets_20261011_v2/delivery/SUMMARY.json')
source_meta = pin_read(OUT/'SOURCE_METADATA.json')
waterfall = pin_read(OUT/'blimpy_waterfall.py', False)
reader = pin_read(OUT/'blimpy_base_reader.py', False)
pin_read(Path(__file__), False)
for code, record in zip([waterfall, reader], source_meta['sources']):
    raw = code.encode()
    blob = b'blob ' + str(len(raw)).encode() + b'\0' + raw
    assert hashlib.sha1(blob).hexdigest() == record['git_blob_sha']

# Verify the retrieved source states the indexing convention without executing it.
water_ast = ast.parse(waterfall)
reader_ast = ast.parse(reader)
def method_source(tree, source, method):
    matches = [x for x in ast.walk(tree) if isinstance(x, ast.FunctionDef) and x.name == method]
    assert len(matches) == 1
    node = matches[0]
    return ast.get_source_segment(source, node)
blank_dc = method_source(water_ast, waterfall, 'blank_dc')
coarse_count = method_source(reader_ast, reader, 'calc_n_coarse_chan')
assert 'mid_chan = int(n_chan_per_coarse / 2)' in blank_dc
assert 'ss = ii*n_chan_per_coarse' in blank_dc
assert 'data[..., ss+mid_chan]' in blank_dc
assert 'nchans % HIRES_THRESHOLD == 0' in coarse_count
assert 'nchans / float(HIRES_THRESHOLD)' in coarse_count
assert 'HIRES_THRESHOLD = 2**20' in reader

headers = []
for src in manifest['sources']:
    attr = src['current_header']['data_attributes']
    headers.append({'scan_id':src['label'], 'original_role':src['role'], 'source_name':attr['source_name'],
                    'fch1_MHz':attr['fch1'], 'foff_MHz':attr['foff'], 'nchans':attr['nchans'],
                    'tsamp_s':attr['tsamp'], 'telescope_id':attr['telescope_id']})
assert len(headers) == 6
assert len({(h['fch1_MHz'],h['foff_MHz'],h['nchans'],h['tsamp_s'],h['telescope_id']) for h in headers}) == 1
ref = headers[0]
f0 = Q.from_float(ref['fch1_MHz']) * 1000000
df = Q.from_float(ref['foff_MHz']) * 1000000
assert df < 0
bandwidth = Q(1500000000,512)
assert abs(df)*N == bandwidth
assert ref['nchans'] % N == 0
assert ref['nchans']//N == 343
paper_f0 = Q(source_meta['paper']['table5_standard_Sband_blc00_fch1_MHz']) * 1000000
offset = (paper_f0-f0)/bandwidth
assert offset.denominator == 1
assert offset == 119
assert summary['previous_known_reference']['channel'] == CENTERS[1]

records = []
for c in CENTERS:
    k, r = divmod(c,N)
    assert r == N//2
    local_center_f = f0 + df*c
    standard_global_coarse_index = int(offset)+k
    paper_center_f = paper_f0 - bandwidth*(Q(standard_global_coarse_index)+Q(1,2))
    assert paper_center_f == local_center_f
    records.append({'fixed_line_source_channel':c, 'native_index':k, 'within_native_index':r,
                    'expected_DC_within_coarse_index':N//2, 'DC_offset_channels':r-N//2,
                    'header_frequency_Hz':float(local_center_f), 'header_frequency_MHz':float(local_center_f/1000000),
                    'published_standard_Sband_global_coarse_index':standard_global_coarse_index,
                    'published_grid_frequency_Hz':float(paper_center_f),
                    'published_grid_difference_Hz':float(local_center_f-paper_center_f),
                    'geometry_exact_in_integer_channel_coordinates':True})

saved_tuples = []
for family in ['s2017_control_targets_20261011_v2','off_adjacent_20261011']:
    for p in sorted((BASE/'analysis'/family/'results').glob('*/TOP3.json')):
        doc = pin_read(p)
        for r in doc['records']:
            c = r['reference_source_channel']
            k, j = divmod(c,N)
            dc = k*N+N//2
            saved_tuples.append({'input_path':str(p.relative_to(ROOT)), 'scan_id':r['scan_id'], 'rank':r['rank'],
                                 'saved_reference_channel':c, 'nearest_native_DC_channel':dc,
                                 'saved_reference_offset_from_native_DC_channels':c-dc,
                                 'saved_width_channels':r['width_channels'], 'saved_drift_hz_s':r['drift_hz_s'],
                                 'new_score_evaluation':False})

result = {
  'schema':'SETI_INDEPENDENT_DC_METADATA_GEOMETRY_V1',
  'status':'COMPLETE_METADATA_DIAGNOSIS_EXPLORATORY',
  'input_pins':INPUTS,
  'original_headers':headers,
  'documented_fine_channels_per_coarse':N,
  'full_source_coarse_count':ref['nchans']//N,
  'native_coarse_width_Hz':float(bandwidth),
  'line_spacing_channels':CENTERS[1]-CENTERS[0],
  'line_spacing_Hz':float(abs(df)*(CENTERS[1]-CENTERS[0])),
  'published_standard_Sband_first_fine_frequency_MHz':float(paper_f0/1000000),
  'source_first_fine_frequency_MHz':float(f0/1000000),
  'source_start_offset_from_standard_grid_coarse_channels':int(offset),
  'file_frequency_origin_matches_published_standard_grid_at_integer_coarse_edge':True,
  'software_convention_verified_from_parsed_official_source':True,
  'software_source_files_match_retrieved_git_blob_SHA1':True,
  'software_sources':source_meta['sources'],
  'fixed_line_center_geometry':records,
  'saved_winning_tuple_geometry':saved_tuples,
  'statement':'All three fixed line-center coordinates coincide exactly with the expected coarse DC-bin lattice; header-origin alignment agrees with published standard GBT S-band frequencies and independent official blimpy indexing. This strongly supports an instrumental/DC interpretation, but physical origin is inferred rather than proved.',
  'inference_strength':{'integer_channel_center_alignment':'exact arithmetic verified',
                        'published_standard_frequency_grid_alignment':'exact arithmetic verified under published standard tuning',
                        'instrumental_DC_origin':'strongly favored interpretation requiring morphology/context corroboration',
                        'specific_hardware_or_processing_cause':'not established'},
  'limitations':[
     'The fixed center coordinates are existing post-selection descriptive references, not three new independent detections.',
     'Saved winning reference tuples can be displaced from DC, particularly native171 width3 references at channel179830783. A box can include or later cross a fixed center; tuple reference is not automatically line-center frequency.',
     'Current official blimpy code corroborates a convention, not the exact pipeline revision used for 2017 files.',
     'Published standard tuning is not a recovered original GUPPI raw header; no specific OBSFREQ/OBSBW or raw-voltage mean was measured.',
     'Header offset corrections and trimming are documented in Lebofsky2019. Integer-grid agreement is corroboration, not independent authentication of tuning or whole-file completeness.',
     'HDF5 chunk size alone is not treated as evidence of hardware origin.',
     'No frequency-grid false-alarm probability is assigned; three nearby selected lines are not independent trials.',
     'No new spectra, maxima arrays, detector grids, thresholds, masks, vetoes, or source acquisition were computed.',
     'Zero bin masking and detector reprocessing would require a separate scientifically specified analysis; no masking is done here.'
  ],
  'new_telescope_HTTP_requests':0, 'new_telescope_BODY_bytes':0,
  'new_observation_visit':False, 'calibrated_SNR_FAP':False, 'qualified_SETI_detection':False,
  'OFF_veto_applied':False, 'original_A_B_status':'FAIL_CLOSED_UNCHANGED',
  'measured_resources':{'process_CPU_seconds':time.process_time()-START_CPU,
                        'wall_seconds':time.perf_counter()-START_WALL,
                        'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                        'input_bytes_read':sum(x['bytes'] for x in INPUTS.values()),
                        'resource_scope':'This small metadata/AST process only; excludes prior searches and remote documentation retrieval.'}
}
(OUT/'GEOMETRY_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'], 'line_center_records':records, 'resources':result['measured_resources']},indent=2))
