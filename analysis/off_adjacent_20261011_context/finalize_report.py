"""Assemble the reviewed final report and publishable receipt summaries.

Reads saved JSON only; no search, fit, filtering or source-array access.
"""
import csv
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
base = root / 'analysis/off_adjacent_20261011_context'
out = base / 'delivery'

def read(path):
    return json.loads(path.read_text())

def pin(path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

primary_qa_path = root / 'analysis/off_adjacent_20261011_qa/results/QA_RECEIPT.json'
context_qa_path = base / 'CONTEXT_QA_RECEIPT.json'
qa, context_qa = read(primary_qa_path), read(context_qa_path)
assert qa['status'].startswith('PASS') and context_qa['status'].startswith('PASS')
sources = [primary_qa_path, context_qa_path, out / 'SUMMARY.json', out / 'NEARBY_STATIONARY_GEOMETRY.json',
           base / 'PROJECT_STATUS_ADDITION_2026-10-11.md', out / 'SETI_OFF_ADJACENT_2026-10-11.md']
receipts, maxima = [], []
for name in ('HIP97319', 'HIP97461', 'HIP97663'):
    folder = root / ('analysis/off_adjacent_20261011/results/primary20170428_' + name)
    rp, ap = folder / 'EXECUTION_RECEIPT.json', folder / 'SCORE_AUDITS.json'
    r = read(rp)
    assert r['status'] == 'COMPLETE_512_NEW_ORIGINAL_OFF_MAPS_EXPLORATORY_ONLY'
    receipts.append({'full_receipt': pin(rp), **{k: r[k] for k in
                     ('status', 'counts', 'process_CPU_seconds', 'wall_seconds', 'peak_RSS_bytes')}})
    sources.extend((rp, ap))
    records = [x['selected_tuple'] for x in read(ap)['records'] if x['query_kind'] == 'core_max']
    assert len(records) == 512
    maxima.extend(records)
assert len(maxima) == 1536
fields = ['primary_target', 'scan_id', 'native_chunk_index', 'core_q', 'map_id',
          'carrier_index_in_core', 'reference_source_channel', 'frequency_hz_at_own_first_midpoint',
          'reference_time_mjd', 'drift_grid_index', 'drift_hz_s', 'width_channels', 'score']
with (out / 'CORE_MAX1536.csv').open('x') as stream:
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows({k: row[k] for k in fields} for row in maxima)

summary = {'status': 'PASS_THREE_PRIMARY_JOBS_AND_BOTH_INDEPENDENT_NUMERICAL_QAS',
           'primary_jobs': receipts,
           'primary_QA': {'full_receipt': pin(primary_qa_path), **{k: qa[k] for k in
             ('status', 'counts', 'numeric_tolerance', 'max_row_sum_arithmetic_absolute_difference',
              'max_score_arithmetic_absolute_difference', 'process_CPU_seconds', 'wall_seconds', 'peak_RSS_bytes')}},
           'context_QA': {'full_receipt': pin(context_qa_path), **{k: context_qa[k] for k in
             ('status', 'counts', 'numeric_tolerance', 'max_row_box_absolute_difference',
              'max_score_absolute_difference', 'CPU_seconds', 'wall_seconds', 'peak_RSS_bytes')}},
           'full_core_MAD_location_independently_refiltered': False,
           'full_grid_recomputed_in_QA': False, 'qualified_SETI_detection': False,
           'calibrated_SNR_FAP': False, 'new_observation': False, 'cost_DKK': 0,
           'limitations': 'Raw503 arithmetic QA is conditional on hash-bound saved full-core MAD/location. Other directions are descriptive context, not independent repeats of the selected OFF target.'}
with (out / 'QA_SUMMARY.json').open('x') as stream:
    json.dump(summary, stream, indent=2); stream.write('\n')

addition = (base / 'PROJECT_STATUS_ADDITION_2026-10-11.md').read_text()
narrative = addition[addition.index('\n\n') + 2:addition.index('\n[Rapport og figurer]')]
original = (out / 'SETI_OFF_ADJACENT_2026-10-11.md').read_text()
details = original[original.index('| Stjerne |'):]
details = details.replace('en separat kontrol kan rekonstruere deres valgte scorer uden at gentage søgningen',
                          'den separate kontrol har rekonstrueret deres valgte scorer uden at gentage søgningen')
text = '# SETI: afsluttet udvidet signalanalyse, 11. oktober 2026\n\n' + narrative + '\n\n'
text += ('Begge uafhængige numeriske kontroller har bestået. Primærkontrollen omfatter alle 1536 kort, '
         '24.576 rå kernemedianer, 6153 rå503-scorequeries og 288 decoded kilde-rækkehashes. '
         'Største kontrollerede scoreafvigelse er 3,64 × 10⁻¹². Kontekstkontrollen omfatter alle 54 profiler, '
         '864 rækkesummer, ni primærscore-match samt bidrags- og overlapdiagnostik; '
         'kontekstscore-aritmetikken stemmer præcist. Den lokale kontrol er betinget af de gemte, hashbundne '
         'fuldkerne-MAD- og lokationsparametre; disse er ikke uafhængigt fuldt refiltreret.\n\n')
text += ('De to stationære frekvenser ligger præcist 2,9296875 MHz på hver sin side af den tidligere '
         'undersøgte 2300,390625 MHz-komponent. Det er observeret frekvensgeometri, som motiverer '
         'undersøgelse af et fælles instrumentelt mønster; årsagen er ikke klassificeret. '
         'Otte-række-overlappet for tredjepladserne er en beskrivelse efter udvælgelsen ud fra de gemte '
         'kanalcentre. Bidragsandelene gælder hele rækkebokse og fastslår ikke, at al effekten kommer '
         'fra én enkelt kildecelle.\n\n')
text += details
text += ('\n\n[Alle 1536 kernemaksima](CORE_MAX1536.csv) · [Ni primære udvalg](TOP9.csv) · '
         '[54 kontekstscorer](CONTEXT54.csv) · [Kompakt QA-evidens](QA_SUMMARY.json) · '
         '[Beskrivende overlapgeometri](NEARBY_STATIONARY_GEOMETRY.json)\n\n'
         'Resultatpakken indeholder alle gemte kort, rå scoreudsnit, komplette receipts, koden og '
         'SHA256-manifestet. De 18 oprindelige rå H5-dele ligger i de tidligere rådatapakker; '
         'REPRODUCTION_AND_DATA_AVAILABILITY.md angiver deres identitet og kørerækkefølgen. '
         'Der er foretaget nul nye teleskopforespørgsler. Pris: 0 DKK.\n')
with (out / 'SETI_ADJACENT_FINAL_2026-10-11.md').open('x') as stream:
    stream.write(text)
outputs = [out / name for name in ('CORE_MAX1536.csv', 'QA_SUMMARY.json', 'SETI_ADJACENT_FINAL_2026-10-11.md')]
receipt = {'status': 'COMPLETE_SAVED_JSON_FINAL_REPORT_AND_CORE_TABLE_NO_SEARCH',
           'code': pin(Path(__file__).resolve()), 'input_pins': [pin(p) for p in sources],
           'output_pins': [pin(p) for p in outputs], 'core_max_rows': len(maxima),
           'frozen_original_report_unchanged': True}
with (out / 'FINAL_DELIVERY_RECEIPT.json').open('x') as stream:
    json.dump(receipt, stream, indent=2); stream.write('\n')
print(json.dumps({'status': receipt['status'], 'core_max_rows': len(maxima)}))
