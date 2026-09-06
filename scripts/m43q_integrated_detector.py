#!/usr/bin/env python3
"""Frozen integrated M43Q replay of M43P anchors and native receiver queries."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np
from m43e_economical_bank import read_sealed,write_sealed
from m43f_source_cache_preflight import build_context
from m43o_real_stacks import ancestor
from m43q_fixture import run_fixture
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43i as transfer
from seti_repeater.detector_m43q import catalogue_bridge,digest,execute
from seti_repeater.receiver_m43q import measure_signature

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43q_integrated_detector'
CONFIG=ROOT/'config/m43q_integrated_detector.json'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen(commit):
    cfg=json.loads(CONFIG.read_text())
    if subprocess.check_output(['git','show',commit+':config/m43q_integrated_detector.json'],cwd=ROOT)!=CONFIG.read_bytes():
        raise ValueError('configuration differs from public freeze')
    for name,h in cfg['pinned_sha256'].items():
        if sha(ROOT/name)!=h:raise ValueError('frozen dependency changed: '+name)
    if np.__version__!=cfg['numpy_version']:raise ValueError('NumPy runtime changed')
    return cfg


class AnchorStore:
    """Verify full parent arrays once, and copied template bytes at every use."""
    def __init__(self,work,cfg):
        self.arrays={};self.expected_ids={};self.row_hashes={};self.descriptors={};self.inventory=[]
        self.selection=cfg['parent_template_indices']
        for kind in ('on','off'):
            for width in core.M37_SPECTRAL_WIDTHS:
                cp=read_sealed(ROOT/f'results_m43p_combined_controls/{kind}.width{width:03d}.json')
                if not cp['complete'] or [s['scan'] for s in cp['sources']]!=[f'epoch{e}_{kind}' for e in (1,2,3)]:
                    raise ValueError('parent source inventory incomplete')
                for e,source in enumerate(cp['sources']):
                    for item in source['arrays']:
                        a=np.load(work/item['path'],mmap_mode='r',allow_pickle=False)
                        if (a.dtype!=np.dtype('<f4') or a.shape!=(item['template_stop']-item['template_start'],cfg['support_carriers'])
                                or transfer.array_hash(a)!=item['score_sha256']):raise ValueError('retained M43P batch bytes changed')
                        self.inventory.append({'path':item['path'],'score_sha256':item['score_sha256'],
                            'source_identity':source['source_identity'],'cache_identity':source['cache_identity']})
                        for parent_t in range(item['template_start'],item['template_stop']):
                            if parent_t not in self.selection:continue
                            t=self.selection.index(parent_t);row=parent_t-item['template_start']
                            self.arrays[(kind,t,width,e)]=a[row]
                            self.row_hashes[(kind,t,width,e)]=transfer.array_hash(a[row])
                for t,parent_t in enumerate(self.selection):
                    descriptor={'parent_checkpoint_sha256':cp['result_sha256'],'parent_template_index':parent_t,
                        'kind':kind,'width':width,'epoch_row_sha256':[self.row_hashes[(kind,t,width,e)] for e in range(3)]}
                    self.descriptors[(kind,t,width)]=descriptor;self.expected_ids[(kind,t,width)]=digest(descriptor)
    def get(self,kind,t,w):
        rows=[]
        for e in range(3):
            row=np.array(self.arrays[(kind,t,w,e)],copy=True)
            if transfer.array_hash(row)!=self.row_hashes[(kind,t,w,e)]:raise ValueError('anchor changed after initial validation')
            rows.append(row)
        values=np.stack(rows)
        values=np.frombuffer(values.tobytes(),dtype='<f4').reshape(values.shape)
        return values,digest(self.descriptors[(kind,t,w)])


class NativeReceiver:
    def __init__(self,source_root,metadata,basis,parent,table,grid):
        self.root=source_root;self.metadata=metadata;self.basis=basis;self.parent=parent;self.table=table;self.grid=grid
        self.cfg=json.loads((ROOT/'config/m43o_real_stacks.json').read_text())
        self.sources={};self.caches={};self.checks=[]
    def cache(self,label,width):
        if (label,width) not in self.caches:
            anchor=next(x for x in self.cfg['sources'] if x['scan']==label)
            if label not in self.sources:
                self.sources[label]=transfer.load_telescope_source(self.root/label/self.cfg['window'],trusted_receipt_sha256=anchor['receipt_sha256'])
            src=self.sources[label];f=core.factor_table_for_scan(self.table,self.basis,label)
            c=transfer.build_telescope_cache(src,f,self.grid,width,bank_sha256=self.table.template_bank_sha256)
            old,_=ancestor(self.cfg,label,width)
            if src.identity!=old['source_identity'] or c.identity!=old['cache_identity']:raise ValueError('native receiver ancestry differs')
            self.caches[(label,width)]=c
        return self.caches[(label,width)]
    def anchors(self,cfg):
        for width in core.M37_SPECTRAL_WIDTHS:
            for e in range(1,4):
                label=f'epoch{e}_on';cache=self.cache(label,width);src=cache.source
                for t in cfg['receiver_parent_templates']:
                    for q in cfg['receiver_score_indices']:
                        observed,receipt=measure_signature(cache,t,q)
                        # Independent direct windows and a separate winner comparison.
                        pred=sum(float(self.grid.score_hz[q])*float(f) for f in cache.factors[t])/src.integration_count/1e6
                        near=int(round((pred*1e6-src.geometry.raw_zero_hz)/src.geometry.channel_width_hz))
                        radius=int(np.ceil(100/src.geometry.channel_width_hz))+3
                        raw=np.arange(near-radius,near+radius+1)
                        freq=(src.geometry.raw_zero_hz+raw.astype('<f8')*src.geometry.channel_width_hz)/1e6
                        keep=np.abs((freq-pred)*1e6)<=100.;raw=raw[keep];freq=freq[keep]
                        if raw.min()<width//2 or raw.max()>=src.geometry.channel_count-width//2:raise ValueError('reference receiver window incomplete')
                        sums=np.zeros(len(raw),dtype='<f4')
                        for row in range(src.integration_count):
                            windows=src.values[row,raw[:,None]+np.arange(-(width//2),width//2+1)]
                            sums+=(np.sum(windows,axis=1,dtype=np.float32)/np.sqrt(width)).astype('<f4')
                        sums/=np.float32(np.sqrt(src.integration_count))
                        best=max(range(len(raw)),key=lambda i:(float(sums[i]),-int(raw[i])))
                        expected={'predicted_mid_mhz':pred,'peak_frequency_mhz':float(freq[best]),'peak_snr':float(sums[best]),
                            'offset_from_prediction_hz':float((freq[best]-pred)*1e6)}
                        if observed!=expected or receipt['winning_raw_index']!=int(raw[best]):raise RuntimeError('native receiver reference mismatch')
                        self.checks.append({'scan':label,'parent_template':t,'score_index':q,'width':width,
                            'signature':observed,'receipt':receipt,'reference_exact':True})
            write_sealed(OUT/'receiver_anchors.json',{'checks':self.checks,'complete':len(self.checks)==144})
            print(f'width {width}: native receiver anchors exact ({len(self.checks)}/144)',flush=True)
    def __call__(self,records,bank,table):
        signatures={};queries=[]
        for r in records:
            t=bank[r['template_index']]['m43_parent_template_index'];q=r['proxy_carrier_index'];w=r['spectral_width_channels']
            values=[]
            for e in r['active_epochs_zero_based']:
                label=f'epoch{e+1}_on';sig,receipt=measure_signature(self.cache(label,w),t,q)
                values.append({'epoch_zero_based':e,**sig});queries.append({'record_id':r['record_id'],'scan':label,**receipt})
            signatures[r['record_id']]=values
        return signatures,{'source_family':'receipt-verified-M43I-native-filter-caches','signatures_sha256':digest(signatures),
            'catalogue_sha256':table.template_bank_sha256,'records_sha256':digest(records),'queries':queries,'queries_sha256':digest(queries)}


def run(work,source_root,freeze):
    cfg=frozen(freeze);started=time.monotonic();OUT.mkdir(exist_ok=True)
    try:
        synthetic,synthetic_bridge,known=run_fixture()
        if synthetic['result_sha256']!=cfg['synthetic_result_sha256']:raise ValueError('known-answer pipeline changed')
        write_sealed(OUT/'synthetic.json',{'pipeline':synthetic,'bridge':synthetic_bridge,'known_dispositions':known})
        _,_,_,metadata,basis,parent,parent_table,_=build_context()
        bank,table,bridge=catalogue_bridge(parent,cfg['parent_template_indices'],basis)
        if bridge!=cfg['bridge']:raise ValueError('catalogue bridge changed')
        store=AnchorStore(work,cfg);grid=core.make_m37_proxy_carrier_grid(cfg['window'])
        receiver=NativeReceiver(source_root,metadata,basis,parent,parent_table,grid)
        receiver.anchors(cfg)
        result=execute(window='m43q-real-anchor-diagnostic',grid=grid,bank=bank,table=table,basis=basis,
            scans=metadata['scans'],store=store,shifts=np.asarray(cfg['scramble_shifts'],dtype=np.int64),
            minimum_shift_bins=cfg['minimum_shift_bins'],reference_floor=cfg['diagnostic_reference_floor'],
            receiver_factory=receiver,maximum_records=cfg['maximum_records'],progress=lambda m:print(m,flush=True))
        parent_logic=read_sealed(ROOT/'results_m43p_combined_controls/on.logic.json')
        expected_null=np.max(np.asarray([x['null_maxima'] for x in parent_logic['checks']],dtype='<f8'),axis=0)
        if not np.array_equal(np.asarray(result['null_maxima']),expected_null):raise ValueError('global handoff differs from M43P maxima')
        if any(d['scientific_candidate'] for d in result['decisions']):raise ValueError('diagnostic mislabelled as science')
        write_sealed(OUT/'pipeline.json',{'pipeline':result,'bridge':bridge,'anchor_inventory':store.inventory})
        summary={'selected_templates':len(bank),'full_bank_geometry_templates':1701,'source_arrays_reused':len(store.inventory),
            'native_receiver_anchors':len(receiver.checks),'known_answer_members':len(known),
            'on_retained':len(result['retained']['on']),'off_retained':len(result['retained']['off']),
            'final_member_decisions':len(result['decisions']),'passes_physical_vetoes':sum(x['passes_evaluated_physical_vetoes'] for x in result['decisions']),
            'diagnostic_null_count':len(result['null_maxima']),'scientific_candidates':0}
        result={'milestone':'M43Q','status':'integrated-diagnostic-pipeline-qualified','freeze_commit':freeze,
            'config_sha256':sha(CONFIG),'wall_seconds':round(time.monotonic()-started,3),'summary':summary,
            'pipeline_result_sha256':result['result_sha256'],'synthetic_result_sha256':synthetic['result_sha256'],
            'artifacts':{name:read_sealed(OUT/name)['result_sha256'] for name in ('synthetic.json','receiver_anchors.json','pipeline.json')},
            'telescope_requests':0,'fresh_null_calibration':False,'native_injection_recovery_measured':False,
            'full_bank_spectral_search':False,'candidate_selection':False}
        write_sealed(OUT/'qualification.json',result);print(json.dumps(summary,indent=2),flush=True)
    except BaseException as error:
        write_sealed(OUT/'failure.json',{'milestone':'M43Q','freeze_commit':freeze,'error':repr(error),'complete':False})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze-commit',required=True);p.add_argument('--anchor-root',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True);a=p.parse_args();run(a.anchor_root,a.source_root,a.freeze_commit)
