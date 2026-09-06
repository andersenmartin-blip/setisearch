"""Known-answer whole-pipeline fixture, with synthetic scores/signatures."""
import json
from pathlib import Path
import numpy as np
from seti_repeater import search_v0p6 as core
from seti_repeater.detector_m43q import catalogue_bridge,digest,execute

ROOT=Path(__file__).resolve().parents[1]


class MemoryStore:
    def __init__(self,arrays):
        self.arrays={};self.expected_ids={}
        for key,a in arrays.items():
            a=np.asarray(a,dtype='<f4');a=np.frombuffer(np.ascontiguousarray(a).tobytes(),dtype='<f4').reshape(a.shape)
            self.arrays[key]=a;self.expected_ids[key]=digest({'kind':key[0],'template':key[1],'width':key[2],
                'synthetic_score_sha256':core.float32_array_sha256(a)})
    def get(self,kind,t,w):
        a=self.arrays[(kind,t,w)]
        observed=digest({'kind':kind,'template':t,'width':w,'synthetic_score_sha256':core.float32_array_sha256(a)})
        return a,observed


def fixture():
    scans=json.loads((ROOT/'config/hd156668b_m37_preflight.json').read_text())['scans']
    labels=[{'scan_index':s,'scan_label':scan['label'],'integration_index':r} for s,scan in enumerate(scans) for r in range(16)]
    basis=core.make_factor_basis_from_arrays(np.arange(96,dtype='<f8')+57470,labels,
        np.ones(96,dtype='<f8'),np.zeros((96,2),dtype='<f8'),expected_sha256=None)
    parent=[{'template_index':0,'coefficient_x':0.,'coefficient_y':0.},
            {'template_index':1,'coefficient_x':.75,'coefficient_y':.25}]
    bank,table,bridge=catalogue_bridge(parent,[0,1],basis)
    grid=core.make_proxy_carrier_grid(.0005,1.,200,64)
    arrays={(kind,t,w):np.full((3,grid.support_bin_count),4 if kind=='on' else 0,dtype='<f4')
            for kind in ('on','off') for t in range(2) for w in core.M37_SPECTRAL_WIDTHS}
    g=grid.support_guard_bins
    for q in (50,100,150,200,250,290,350):arrays[('on',1,1)][:2,g+q]=100
    arrays[('off',1,1)][:2,g+50]=100
    arrays[('off',1,1)][:2,g+101]=100
    arrays[('off',1,1)][0,g+150]=np.float32(5.5)
    arrays[('off',1,1)][2,g+350]=100
    # A width-OR exclusion must remove the (0,1) member at q=200.
    arrays[('on',1,129)][:,g+200]=[100,0,0]
    store=MemoryStore(arrays)
    def receiver(records,bank,table):
        signatures={}
        for r in records:
            q=r['proxy_carrier_index'];pred=r['proxy_carrier_mhz']
            peak=float(grid.score_hz[270]/1e6) if q in (250,290) else pred
            snr=8. if q in (250,290) else 1.
            signatures[r['record_id']]=[{'epoch_zero_based':e,'predicted_mid_mhz':pred,
                'peak_frequency_mhz':peak,'peak_snr':snr,'offset_from_prediction_hz':(peak-pred)*1e6}
                for e in r['active_epochs_zero_based']]
        return signatures,{'source_family':'synthetic-known-answer-signatures','signatures_sha256':digest(signatures)}
    shifts=np.array([[0,11,23],[0,17,31],[0,101,137],[0,271,307]],dtype=np.int64)
    kwargs=dict(window='m43q-synthetic',grid=grid,bank=bank,table=table,basis=basis,scans=scans,store=store,
        shifts=shifts,minimum_shift_bins=10,reference_floor=50.,receiver_factory=receiver,maximum_records=10000)
    return kwargs,bridge


def run_fixture():
    kwargs,bridge=fixture();r=execute(**kwargs)
    selected={x['proxy_carrier_index']:x['member_disposition'] for x in r['receiver_alias']['records']
              if x['template_index']==1 and x['active_epochs_zero_based']==[0,1]}
    expected={50:'rfi_veto_matched_off_same_hypothesis',100:'rfi_veto_local_off_track',
              150:'rfi_veto_single_adjacent_off',250:'rfi_veto_receiver_frame_alias',
              290:'rfi_veto_receiver_frame_alias',350:'pending_receiver_alias_evaluation'}
    if selected!=expected:raise RuntimeError(f'known-answer disposition mismatch: {selected}')
    if any(x['scientifically_eligible'] for x in r['rank']['evidence']):raise RuntimeError('four nulls cannot establish p<=.01')
    return r,bridge,selected


if __name__=='__main__':
    r,b,s=run_fixture();print(json.dumps({'bridge':b,'expected_dispositions':s,'result_sha256':r['result_sha256']},indent=2))
