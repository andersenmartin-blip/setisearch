#!/usr/bin/env python3
"""Fixed calibration-only LS7M panel; never opens native science pixels."""
import csv
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from seti_repeater.tess_prf_response import PRFCatalog, integrate, live_intervals

OUT=ROOT/'results_ls7m_response'


def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path,value): path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def main():
    assert not OUT.exists(), 'refuse to overwrite a completed benchmark'
    cfg=json.loads((ROOT/'config/ls7m_response.json').read_text())
    for path,sha in cfg['input_sha256'].items(): assert digest(ROOT/path)==sha,path
    catalog=PRFCatalog(ROOT)
    OUT.mkdir()
    # Every phase at every node: source shift maps integer pixel centers to
    # axis residues; index 58 is the zero of the inherited relative axes.
    yy,xx=np.mgrid[-6:7,-6:7]; phase_pixels=np.stack([xx,yy],axis=-1)
    phase_rows=[]
    for (ccd,row,col),entry in sorted(catalog.entries.items()):
        model=entry['model']
        for r in range(9):
            for c in range(9):
                got=model.sample(phase_pixels,[(4-c)/9,(4-r)/9])
                assert got.covered.all()
                err=float(np.max(np.abs(got.flux-model.values[r::9,c::9])))
                uerr=float(np.max(np.abs(got.uncertainty_envelope-model.uncertainties[r::9,c::9])))
                assert max(err,uerr)<=cfg['absolute_tolerance']
                phase_rows.append({'ccd':ccd,'grid_row':row,'grid_col':col,'row_residue':r,
                                   'column_residue':c,'maximum_flux_difference':err,
                                   'maximum_uncertainty_difference':uerr,'phase_sum':float(got.flux.sum())})
    with (OUT/'phase_checks.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(phase_rows[0]));writer.writeheader();writer.writerows(phase_rows)
    inv=json.loads((ROOT/'results_ls7k_inputs/inventory.json').read_text())
    rows=[]; saved={}; fields=[]
    for sector in cfg['sectors']:
        record=next(x for x in inv['light_curves'] if x['sector']==sector)
        geo=record['geometry'];source=np.array(geo['nominal_target_cutout_xy'])
        yy,xx=np.indices(geo['array_shape_yx']);pixels=np.stack([xx,yy],axis=-1)
        for offset in cfg['column_offsets']:
            model,nodes=catalog.local(record['ccd'],geo['nominal_target_detector_xy'],calibration_column_offset=offset)
            fields.append({'sector':sector,'column_offset':offset,'nodes':nodes})
            for phase in cfg['integration_start_phases_seconds']:
                live=live_intervals(readout_phase_seconds=phase)
                for path in cfg['trajectories']:
                    xy=source+np.asarray(path['displacement_xy'])
                    for pulse in cfg['pulses']:
                        k=len(rows); case=f'case_{k:03d}'
                        response,pieces=integrate(model,pixels,cfg['trajectory_times_seconds'],xy,live,pulse_intervals=pulse['intervals'])
                        gates=live if pulse['intervals'] is None else np.asarray(pulse['intervals'])
                        on_seconds=sum(max(0,min(b,d)-max(a,c)) for a,b in live for c,d in gates)
                        saved[case+'_flux']=response.flux
                        saved[case+'_uncertainty']=response.uncertainty_envelope
                        saved[case+'_covered']=response.covered
                        rows.append({'case':case,'sector':sector,'column_offset':offset,'integration_start_seconds':phase,
                                     'trajectory':path['name'],'pulse':pulse['name'],'pulse_live_seconds':float(on_seconds),
                                     'covered_pixels':int(response.covered.sum()),'stamp_pixels':int(response.covered.size),
                                     'summed_covered_flux':float(np.nansum(response.flux)),
                                     'summed_covered_uncertainty_entries':float(np.nansum(response.uncertainty_envelope)),
                                     'quadrature_pieces':pieces})
    assert len(rows)==144 and len(phase_rows)==4050
    write_json(OUT/'cases.json',rows);write_json(OUT/'field_weights.json',fields)
    np.savez_compressed(OUT/'predictions.npz',**saved)
    comparisons=[]
    # Report both coordinate variants on their common covered pixels.
    for a in rows:
        if a['column_offset']!=0: continue
        b=next(b for b in rows if b['column_offset']==-44 and all(a[k]==b[k] for k in ['sector','integration_start_seconds','trajectory','pulse']))
        mask=saved[a['case']+'_covered']&saved[b['case']+'_covered']
        fa,fb=saved[a['case']+'_flux'][mask],saved[b['case']+'_flux'][mask]
        comparisons.append({'case_offset_0':a['case'],'case_offset_minus44':b['case'],
                            'common_pixels':int(mask.sum()),'relative_l2_difference':float(np.linalg.norm(fa-fb)/np.linalg.norm(fa)),
                            'absolute_l1_difference':float(np.abs(fa-fb).sum())})
    write_json(OUT/'coordinate_sensitivity.json',comparisons)
    summary={'study':'LS7M calibrated PRF and exposure operator','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
             'python':platform.python_version(),'numpy':np.__version__,'config_sha256':digest(ROOT/'config/ls7m_response.json'),
             'calibration_cases':len(rows),'phase_images':len(phase_rows),
             'maximum_phase_flux_difference':max(r['maximum_flux_difference'] for r in phase_rows),
             'maximum_phase_uncertainty_difference':max(r['maximum_uncertainty_difference'] for r in phase_rows),
             'covered_pixels_range':[min(r['covered_pixels'] for r in rows),max(r['covered_pixels'] for r in rows)],
             'fully_covered_cases':sum(r['covered_pixels']==r['stamp_pixels'] for r in rows),
             'maximum_coordinate_relative_l2_difference':max(c['relative_l2_difference'] for c in comparisons),
             'absolute_origin_established':False,'mission_readout_phase_established':False,
             'quaternion_to_detector_motion_established':False,'upstream_target_exclusion_established':False,
             'native_response_comparisons':0,'new_detector_decisions':0,'added_observing_days':0}
    write_json(OUT/'summary.json',summary)
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':main()
