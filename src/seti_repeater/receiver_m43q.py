"""Stationary receiver signatures from verified M43I native-filter caches."""
import math
import numpy as np
from . import search_v0p6 as core
from . import transfer_m43i as transfer
from .receiver_v0p6 import _predicted_midpoint_hz


def measure_signature(cache,template,score_index):
    template=core._strict_int(template,'receiver template')
    score_index=core._strict_int(score_index,'receiver score index')
    if type(cache) is not transfer.TelescopeCache:raise ValueError('M43I cache required')
    if not 0<=score_index<cache.grid.score_bin_count:raise ValueError('receiver carrier outside score grid')
    g=cache.grid.support_guard_bins
    transfer.gather_bank_slice(cache,g,g+1,template_indices=[template],chunk_bins=1)
    geometry=cache.source.geometry; half=cache.width//2
    predicted=_predicted_midpoint_hz(float(cache.grid.score_hz[score_index]),cache.factors[template])/1e6
    hz=predicted*1e6
    lo=math.floor((hz-100.-geometry.raw_zero_hz)/geometry.channel_width_hz)-2
    hi=math.ceil((hz+100.-geometry.raw_zero_hz)/geometry.channel_width_hz)+2
    raw=np.arange(lo,hi+1,dtype=np.int64)
    frequency=(geometry.raw_zero_hz+raw.astype('<f8')*geometry.channel_width_hz)/1e6
    use=np.abs((frequency-predicted)*1e6)<=100.
    raw=raw[use];frequency=frequency[use]
    if not raw.size or raw.min()<half or raw.max()>=geometry.channel_count-half:
        raise core.V0P6CoverageError('complete receiver neighborhood absent')
    sums=np.zeros(len(raw),dtype='<f4')
    for row in range(cache.source.integration_count):sums+=cache.values[row,raw-half]
    sums/=np.float32(math.sqrt(cache.source.integration_count))
    if not np.isfinite(sums).all():raise ValueError('nonfinite stationary receiver score')
    winner=int(np.argmax(sums))
    signature={'predicted_mid_mhz':predicted,'peak_frequency_mhz':float(frequency[winner]),
        'peak_snr':float(sums[winner]),'offset_from_prediction_hz':float((frequency[winner]-predicted)*1e6)}
    receipt={'adapter':'m43q-stationary-native-peak-v1','cache_identity':cache.identity,
        'source_identity':cache.source.identity,'template_index':template,'score_index':score_index,
        'width':cache.width,'local_half_width_hz':100.,'raw_start':int(raw[0]),'raw_stop':int(raw[-1])+1,
        'native_channels':len(raw),'winning_raw_index':int(raw[winner]),
        'tie_break':'first ascending native-channel maximum','mask_applied':False}
    return signature,receipt
