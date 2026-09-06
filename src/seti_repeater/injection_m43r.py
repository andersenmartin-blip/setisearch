"""Explicit native overlays; original telescope receipts are never altered.

Only filtered centers whose window contains the added native sample change.
Recompute their complete windows, then integrate complete affected columns in
ascending float32 row order. Never add an analytic delta to integrated scores.
"""
import math
import numpy as np
from . import search_v0p6 as core
from .transfer_m43g import immutable, array_hash
from .detector_m43q import digest
from .receiver_v0p6 import _predicted_midpoint_hz


def filtered_patch(values, centers, width, amplitude):
    if values.dtype != np.dtype('<f4') or values.ndim != 2:
        raise ValueError('native float32 rows required')
    centers=np.asarray(centers,dtype=np.int64)
    if centers.shape!=(len(values),) or not np.isfinite(amplitude) or amplitude<0:
        raise ValueError('invalid overlay')
    half=width//2
    if width not in core.M37_SPECTRAL_WIDTHS or np.any(centers-width+1<0) or np.any(centers+width>values.shape[1]):
        raise ValueError('incomplete patch windows')
    patches=[]
    for row,center in enumerate(centers):
        section=values[row,center-width+1:center+width].copy()
        section[width-1]+=np.float32(amplitude)
        windows=np.lib.stride_tricks.sliding_window_view(section,width)
        filtered=(np.sum(windows,axis=-1,dtype=np.float32)/np.sqrt(width)).astype('<f4')
        patches.append((int(center-half),immutable(filtered)))
    return patches


def replace_and_integrate(base_rows, raw_indices, patches):
    """Complete integration only where at least one native window changes."""
    affected=np.zeros(raw_indices.shape[1],dtype=bool)
    for row,(lo,v) in enumerate(patches):
        affected|=(raw_indices[row]>=lo)&(raw_indices[row]<lo+len(v))
    cols=np.flatnonzero(affected)
    rows=base_rows[:,cols].copy()
    for row,(lo,v) in enumerate(patches):
        offsets=raw_indices[row,cols]-lo
        use=(offsets>=0)&(offsets<len(v))
        rows[row,use]=v[offsets[use]]
    sums=np.zeros(len(cols),dtype='<f4')
    for row in rows:sums+=row
    sums/=np.float32(math.sqrt(len(rows)))
    return cols,sums


class ScoreStore:
    def __init__(self,arrays,provenance):
        self.arrays={k:immutable(np.ascontiguousarray(v)) for k,v in arrays.items()}
        self.provenance=provenance
        self.expected_ids={k:digest({'provenance':provenance,'key':list(k),'payload':array_hash(v)}) for k,v in self.arrays.items()}
    def get(self,kind,t,w):
        k=(kind,t,w);v=self.arrays[k]
        actual=digest({'provenance':self.provenance,'key':list(k),'payload':array_hash(v)})
        if actual!=self.expected_ids[k]:raise ValueError('pilot score payload changed')
        return v,actual


class NativeOverlay:
    def __init__(self,baseline,receiver,bank,table,basis,grid,progress=lambda m:None):
        self.baseline=baseline;self.receiver=receiver;self.bank=bank;self.table=table
        self.basis=basis;self.grid=grid;self.gathers={};self.indices={};self.factors={}
        self.cache_inventory=[]
        for e in range(3):
            label=f'epoch{e+1}_on'
            f=core.factor_table_for_scan(table,basis,label);self.factors[e]=f
            for w in core.M37_SPECTRAL_WIDTHS:
                cache=receiver.cache(label,w)
                if e not in self.indices:
                    self.indices[e]=core.nearest_native_indices(cache.source.geometry,f[:,:,None]*grid.support_hz)
                idx=self.indices[e]
                rows=np.stack([cache.values[r,idx[:,r,:]-w//2] for r in range(cache.source.integration_count)],axis=1)
                sums=np.zeros((len(bank),grid.support_bin_count),dtype='<f4')
                for r in range(cache.source.integration_count):sums+=rows[:,r,:]
                sums/=np.float32(math.sqrt(cache.source.integration_count))
                expected=np.stack([baseline.get('on',t,w)[0][e] for t in range(len(bank))])
                if not np.array_equal(sums.view('<u4'),expected.view('<u4')):
                    raise ValueError('cropped native gather differs from M43P anchor')
                self.gathers[e,w]=immutable(rows)
                self.cache_inventory.append({'scan':label,'width':w,'source_identity':cache.source.identity,
                    'cache_identity':cache.identity,'row_gather_sha256':array_hash(rows),'anchor_exact':True})
            progress(f'{label}: eight native caches and all cropped baseline scores exact')
        self.patches={};self.overlay_receipt={'kind':'uninjected-background'}

    def trial(self,truth,amplitude):
        self.patches={}
        details=[]
        for e in truth['active_epochs']:
            label=f'epoch{e+1}_on';src=self.receiver.cache(label,1).source
            centers=core.nearest_native_indices(src.geometry,
                self.grid.score_hz[truth['score_index']]*self.factors[e][truth['local_template']])
            row_amplitude=float(amplitude/math.sqrt(src.integration_count))
            details.append({'scan':label,'background_source_identity':src.identity,'native_centers':centers.tolist(),
                'per_row_float32_addition':float(np.float32(row_amplitude))})
            if amplitude:
                for w in core.M37_SPECTRAL_WIDTHS:
                    self.patches[e,w]=filtered_patch(src.values,centers,w,row_amplitude)
        self.overlay_receipt={'schema':'m43r-native-overlay-v1','truth':truth,'nominal_epoch_snr':amplitude,
            'placement':'after frozen normalization, before native filter and proxy gather',
            'profile':'one nearest-even native channel per integration, no fractional leakage or intra-row smear',
            'background_provenance':self.baseline.provenance,'sources':details,
            'patch_payloads':{f'{e}:{w}':[{'start':lo,'sha256':array_hash(v)} for lo,v in p]
                for (e,w),p in sorted(self.patches.items())}}
        arrays={k:v.copy() for k,v in self.baseline.arrays.items()}
        for (e,w),patches in self.patches.items():
            for t in range(len(self.bank)):
                cols,values=replace_and_integrate(self.gathers[e,w][t],self.indices[e][t],patches)
                arrays['on',t,w][e,cols]=values
        return ScoreStore(arrays,{'baseline':self.baseline.provenance,'native_overlay_sha256':digest(self.overlay_receipt)})

    def __call__(self,records,bank,table):
        signatures={};queries=[];memo={}
        for r in records:
            t=r['template_index'];q=r['proxy_carrier_index'];w=r['spectral_width_channels'];values=[]
            for e in r['active_epochs_zero_based']:
                key=(t,q,w,e)
                if key not in memo:
                    cache=self.receiver.cache(f'epoch{e+1}_on',w);g=cache.source.geometry
                    pred=_predicted_midpoint_hz(float(self.grid.score_hz[q]),self.factors[e][t])/1e6
                    lo=math.floor((pred*1e6-100-g.raw_zero_hz)/g.channel_width_hz)-2
                    hi=math.ceil((pred*1e6+100-g.raw_zero_hz)/g.channel_width_hz)+2
                    raw=np.arange(lo,hi+1,dtype=np.int64)
                    freq=(g.raw_zero_hz+raw.astype('<f8')*g.channel_width_hz)/1e6
                    keep=np.abs((freq-pred)*1e6)<=100.;raw=raw[keep];freq=freq[keep]
                    if not raw.size or raw.min()<w//2 or raw.max()>=g.channel_count-w//2:
                        raise core.V0P6CoverageError('receiver neighborhood incomplete')
                    sums=np.zeros(len(raw),dtype='<f4')
                    for row in range(cache.source.integration_count):
                        v=cache.values[row,raw-w//2].copy()
                        if (e,w) in self.patches:
                            start,patch=self.patches[e,w][row];offset=raw-start
                            use=(offset>=0)&(offset<len(patch));v[use]=patch[offset[use]]
                        sums+=v
                    sums/=np.float32(math.sqrt(cache.source.integration_count));win=int(np.argmax(sums))
                    sig={'predicted_mid_mhz':pred,'peak_frequency_mhz':float(freq[win]),'peak_snr':float(sums[win]),
                        'offset_from_prediction_hz':float((freq[win]-pred)*1e6)}
                    memo[key]=(sig,{'epoch':e,'template':t,'score_index':q,'width':w,'raw_start':int(raw[0]),
                        'raw_stop':int(raw[-1])+1,'winning_raw_index':int(raw[win]),'background_cache':cache.identity})
                sig,query=memo[key];values.append({'epoch_zero_based':e,**sig});queries.append({'record_id':r['record_id'],**query})
            signatures[r['record_id']]=values
        return signatures,{'source_family':'explicit-M43R-native-overlay-on-receipt-verified-background',
            'overlay_sha256':digest(self.overlay_receipt),'signatures_sha256':digest(signatures),
            'queries':queries,'queries_sha256':digest(queries)}
