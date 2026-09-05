#!/usr/bin/env python3
"""Post-hoc frequency overlap with later OFF scans; never revises LS5 disposition."""
import json,hashlib
from pathlib import Path
from seti_repeater.light_sail import frequency_overlap_fraction
from seti_repeater.search_v0p6 import canonical_json_bytes

def main():
    source=Path('results_ls5_screen/screen.json');screen=json.loads(source.read_text());rows=[]
    for candidate in screen['candidates']:
        if not candidate['survives_adjacent_off_veto']:continue
        event=candidate['event'];off=[]
        for scan in screen['scans']:
            if scan['role']!='OFF':continue
            matches=[{'event':other,'frequency_overlap_fraction':frequency_overlap_fraction(event,other)} for other in scan['search']['events'] if other['score']>=6 and frequency_overlap_fraction(event,other)>=.5]
            off.append({'label':scan['label'],'was_frozen_adjacent_off':scan['label'] in next(s['adjacent_off_labels'] for s in screen['scans'] if s['label']==candidate['on_label']),'matching_retained_event_count':len(matches),'maximum_score':max((m['event']['score'] for m in matches),default=None),'matches':matches})
        rows.append({'on_label':candidate['on_label'],'event':event,'off_checks':off})
    result={'artifact_type':'seti_repeater.ls5_posthoc_later_off_audit','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source_result_identity':screen['result_sha256'],'posthoc':True,'primary_disposition_modified':False,'new_spectral_values_read':False,'interpretation':'Frequency overlap in nonadjacent controls flags interference concern; not simultaneous coincidence or proof of common physical origin. Primary three-survivor result is unchanged.','rows':rows}
    result['result_sha256']=hashlib.sha256(canonical_json_bytes(result)).hexdigest()
    Path('results_ls5_screen/later_off_audit.json').write_bytes(canonical_json_bytes(result))
if __name__=='__main__':main()
