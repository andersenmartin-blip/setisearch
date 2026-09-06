"""M43O oracle and source-order gate. No telescope loading or candidate logic."""
import hashlib
import numpy as np
from seti_repeater import search_v0p6 as core
from seti_repeater.transfer_m43i import array_hash

SUBSETS=((0,1),(0,2),(1,2),(0,1,2))
MODES=('raw','active3')


def validate_vectors(vectors, labels, kind, expected_hashes):
    expected=tuple(f'epoch{i}_{kind}' for i in (1,2,3))
    if kind not in ('on','off') or tuple(labels)!=expected or len(vectors)!=3 or len(expected_hashes)!=3:
        raise ValueError('epoch order, kind or inventory differs')
    shape=vectors[0].shape
    for value,digest in zip(vectors,expected_hashes):
        if (value.dtype!=np.dtype('<f4') or value.ndim!=2 or value.shape!=shape
                or not value.flags.c_contiguous or not np.isfinite(value).all() or array_hash(value)!=digest):
            raise ValueError('epoch vector differs from retained batch')


def reference_stack(vectors,subset,mode):
    if mode not in MODES or tuple(subset) not in SUBSETS:raise ValueError('unfrozen stack rule')
    score=np.zeros(vectors.shape[1:],dtype='<f4');admit=np.ones(score.shape,dtype=bool)
    for epoch in subset:
        score+=vectors[epoch]
        if mode=='active3':admit &= vectors[epoch]>=np.float32(3)
    score/=np.float32(np.sqrt(len(subset)))
    score[~admit]=-np.inf
    return score


def qualify_stacks(vectors,labels,kind,expected_hashes,*,chunk_bins):
    validate_vectors(vectors,labels,kind,expected_hashes)
    if not isinstance(chunk_bins,int) or isinstance(chunk_bins,bool) or chunk_bins<1:
        raise ValueError('positive integer chunk required')
    rows,n=vectors[0].shape
    hashes={(mode,subset):hashlib.sha256() for mode in MODES for subset in SUBSETS}
    counts={key:0 for key in hashes}
    for left in range(0,n,chunk_bins):
        right=min(n,left+chunk_bins)
        # Preserve [epoch, template, carrier] before flattening only the latter axes.
        block=np.stack([v[:,left:right] for v in vectors],axis=0)
        flat=block.reshape(3,-1)
        for mode,subset in hashes:
            actual=core.stack_hypothesis(flat,subset,minimum_active_epoch_snr=None if mode=='raw' else 3.,
                stack_statistic='sum',exclusion_mask=None).reshape(rows,right-left)
            expected=reference_stack(block,subset,mode)
            if actual.dtype!=expected.dtype or not np.array_equal(actual,expected):
                raise RuntimeError(f'stack mismatch: {kind}, {mode}, {subset}, carriers {left}:{right}')
            hashes[mode,subset].update(memoryview(np.ascontiguousarray(actual)).cast('B'))
            counts[mode,subset]+=int(np.isfinite(actual).sum())
    records=[]
    for mode,subset in hashes:
        if mode=='raw' and counts[mode,subset]!=rows*n:raise ValueError('nonfinite raw arithmetic')
        records.append({'mode':mode,'subset':list(subset),'cells_compared':rows*n,
            'finite_cells':counts[mode,subset],'score_sha256':hashes[mode,subset].hexdigest(),'reference_exact':True})
    return records
