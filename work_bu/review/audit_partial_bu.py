"""Independent BU five-scan saved-output audit, without production imports.

All seed identities, geometry, support and classifications are recomputed.
Numerical comparisons use independent direct element sums at fixed bounded
coordinates; this is not a second complete search or an independent decoder.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
import os
import signal
import time
import numpy as np

WIDTHS = (1, 3, 9, 33)
STRIDES = (1, 1, 2, 8)
BATCHES = [list(range(k, k+8)) for k in (1, 9, 17, 25)]
STATES = ('REJECTED_AVAILABLE_OFF', 'INCOMPLETE_OFF_COVERAGE', 'THREE_ON_FAIL', 'UNSUPPORTED')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate JSON key')
        result[key] = value
    return result


def _bad(value):
    raise ValueError('Nonfinite JSON value: '+value)


def read(path):
    return json.loads(Path(path).read_text(), object_pairs_hook=_pairs, parse_constant=_bad)


def load(path):
    with np.load(path, allow_pickle=False) as arrays:
        return {key: arrays[key] for key in arrays.files}


def same(a, b):
    return np.array_equal(a, b, equal_nan=True) if a.dtype.kind == 'f' else np.array_equal(a, b)


def publication(path, record):
    require(Path(path).name == Path(record['path']).name, 'Publication basename differs')
    require(sha(path) == record['sha256'], 'Publication SHA differs: '+str(path))
    if 'bytes' in record:
        require(Path(path).stat().st_size == record['bytes'], 'Publication size differs')


def snapshot(folder):
    result=[]
    for path in sorted(Path(folder).rglob('*')):
        require(not path.is_symlink(), 'Symlink in saved output tree')
        if path.is_dir():
            continue
        require(path.is_file(), 'Nonregular saved output')
        result.append({'path':str(path.relative_to(folder)),'bytes':path.stat().st_size,'sha256':sha(path)})
    require(len(result) <= 512, 'Saved output member cap differs')
    return result


def scalar_track(y, offsets, center, width):
    half = width//2
    return math.fsum(float(y[row, center+int(offset)+delta])
                     for row, offset in enumerate(offsets)
                     for delta in range(-half, half+1))


def direct_vector(y, offsets, centers, width):
    """No convolution, prefix sum, production kernel, or shared helper."""
    total = np.zeros(len(centers), dtype=np.float64)
    for row, offset in enumerate(offsets):
        for delta in range(-(width//2), width//2+1):
            total += y[row, centers+int(offset)+delta].astype(np.float64)
    return total


def fixed_rows(n):
    # Fixed before data: maximum129 evenly spaced catalog positions per q.
    return np.unique(np.linspace(0, n-1, min(n,129), dtype=np.int64)) if n else np.zeros(0,dtype=np.int64)


def classifications(center, maximum, valid):
    supported = np.logical_and.reduce(valid[:,:5], axis=1)
    on3 = np.logical_and.reduce(valid[:,(0,2,4)] & (center[:,(0,2,4)] >= 10),axis=1)
    off = np.logical_or.reduce(valid[:,(1,3)] & (maximum[:,(1,3)] >= 5),axis=1)
    status = np.array(['UNSUPPORTED']*len(valid),dtype='<U28')
    for index in range(len(valid)):
        if supported[index]:
            status[index] = ('THREE_ON_FAIL' if not on3[index] else
                             'REJECTED_AVAILABLE_OFF' if off[index] else 'INCOMPLETE_OFF_COVERAGE')
    return supported,on3,off,status


def audit_normalization(plan, records, supports, out):
    """Independent partition anchors; shared NumPy interp reconstruction."""
    anchors_checked = support_values = 0
    for scope, record, y in zip(plan['scans'], records, supports):
        rawpath = Path(scope['path'])
        require(sha(rawpath) == scope['input_sha256'], 'Native input hash differs')
        raw = np.load(rawpath,mmap_mode='r',allow_pickle=False)
        require(raw.shape == (16,1048576) and raw.dtype == np.dtype('<f4'), 'Native matrix differs')
        anchors = load(out/Path(record['anchor_audit']['path']).name)
        starts = np.arange(0,1048576,4096,dtype=np.int64)
        require(same(anchors['block_start'],starts) and same(anchors['block_stop'],starts+4096), 'Anchor blocks differ')
        channels = starts.astype(np.float64)+2047.5
        require(same(anchors['anchor_channel'],channels), 'Anchor centers differ')
        for index, start in enumerate(starts):
            block = raw[:,start:start+4096]
            ordered = np.partition(block,(2047,2048),axis=1)
            median = (ordered[:,2047]+ordered[:,2048])/np.float32(2)
            deviations = np.partition(np.abs(block-median[:,None]),(2047,2048),axis=1)
            scale = ((deviations[:,2047]+deviations[:,2048])/np.float32(2))*np.float32(1.4826)
            require(same(median,anchors['block_median'][index]) and same(scale,anchors['block_MAD_scale'][index]), 'Independent anchor median/MAD differs')
            anchors_checked += 16
        positions = np.arange(record['support_start'],record['support_stop'],dtype=np.float64)
        for row in range(16):
            median = np.interp(positions,channels,anchors['block_median'][:,row].astype(np.float64))
            scale = np.interp(positions,channels,anchors['block_MAD_scale'][:,row].astype(np.float64))
            expected = ((raw[row,record['support_start']:record['support_stop']].astype(np.float64)-median)/scale).astype(np.float32)
            require(same(expected,y[row]), 'Normalized support reconstruction differs')
            support_values += len(expected)
        require(sha(rawpath) == scope['input_sha256'], 'Native input changed during normalization review')
    return {'independent_native_anchor_pairs_checked':anchors_checked,
            'normalized_support_values_exactly_reconstructed':support_values,
            'interpolation_independence':'Shared NumPy interp primitive; independent anchor extraction and orchestration'}


def audit(planpath, out, check_normalization=False):
    began = time.monotonic()
    planpath,out = Path(planpath),Path(out)
    original_snapshot=snapshot(out)
    plan = read(planpath); ph = sha(planpath)
    require(plan['schema'] == 'SETI_BU_PARTIAL_HIP44295_LOCAL_Q_ESS_V1', 'Plan family differs')
    require(plan['core_q_list'] == list(range(1,33)), 'Prospective q scope differs')
    require(plan['complete_OFF_support'] is False and plan['missing_scan'] == 5 and plan['original_coverage_credit'] == 0, 'Missing control/coverage scope differs')
    require([s['scan'] for s in plan['scans']] == list(range(5)), 'Only five complete scans allowed')
    for scope in plan['scans']:
        require(sha(scope['header_path']) == scope['header_sha256'], 'Header evidence hash differs')
        header=read(scope['header_path']);attrs=header['attrs']
        require(header['archive']['id'] == scope['archive_id'] and attrs['source_name'] == scope['target'], 'Native header identity differs')
        require(attrs['tstart'] == scope['header_tstart_mjd'] and attrs['tsamp'] == scope['dt_seconds'], 'Native timing differs from plan')
        require(attrs['foff']*1e6 == scope['df_hz'] and attrs['fch1'] == scope['source_header_first_frequency_mhz'], 'Native frequency metadata differs')
        require(attrs['nchans'] == scope['source_nchannels'] and scope['fch1_mhz'] == attrs['fch1']+plan['native_channel_start']*attrs['foff'], 'Native source extent/origin differs')
        require(scope['tref_midpoint_mjd'] == attrs['tstart']+7.5*attrs['tsamp']/86400, 'Midpoint timing differs')
    for path,digest in plan['source_sha256'].items():
        require(sha(path) == digest, 'Frozen source differs')
    result = read(out/'BATCH_COMPLETE.json')
    qs = BATCHES[result['batch']-1]
    require(result['plan_sha256'] == ph and result['q_list'] == qs and result['track_trials'] == 360837120, 'Batch scope/count differs')
    require(result['complete_OFF_support'] is False and result['original_coverage_credit'] == 0 and result['full_cadence_candidate_assessment'] == 'NOT_EVALUABLE_MISSING_OFF5', 'Batch claims differ')
    prepared = read(out/'NORMALIZED_INPUTS_COMPLETE.json')
    require(prepared['plan_sha256'] == ph and prepared['q_list'] == qs and prepared['missing_scan'] == 5, 'Normalized input binding differs')
    records = prepared['scans']; supports=[]
    for scope,record in zip(plan['scans'],records):
        require(scope['scan'] == record['scan'], 'Normalized scan order differs')
        path = out/Path(record['normalized_support_path']).name
        require(sha(path) == record['normalized_support_sha256'], 'Normalized support hash differs')
        y = np.load(path,mmap_mode='r',allow_pickle=False)
        require(y.dtype == np.dtype('<f4') and y.shape == (16,40960) and np.isfinite(y).all(), 'Support type/shape/values differ')
        require(record['support_start'] == (min(qs)-1)*4096 and record['support_stop'] == (max(qs)+2)*4096, 'Support geometry differs')
        publication(out/Path(record['anchor_audit']['path']).name,record['anchor_audit'])
        supports.append(y)
    normal = audit_normalization(plan,records,supports,out) if check_normalization else {'not_repeated_this_batch':True}
    rates = np.linspace(-4,4,839,dtype=np.float64)
    times = (np.arange(16,dtype=np.float64)-7.5)*plan['scans'][0]['dt_seconds']
    offsets = np.rint(rates[:,None]*times[None,:]/plan['scans'][0]['df_hz']).astype(np.int32)
    count_scalar=count_vectors=count_assoc=0
    max_scalar_error=max_vector_error=max_forced_error=0.0
    total_seeds=0; totals={state:0 for state in STATES}; q_reviews=[]
    for q,inline in zip(qs,result['results']):
        folder=out/f'q{q:03d}'; complete=read(folder/'PARTIAL_Q_COMPLETE.json')
        require(complete == inline and complete['q'] == q and complete['track_trials'] == 45104640, 'Saved q result differs')
        grids=[]; catalogs=[]
        for scope,record,y,summary in zip(plan['scans'],records,supports,complete['scans']):
            scan=scope['scan']; require(read(folder/f'scan{scan}_summary.json') == summary, 'Scan summary differs')
            for pub in summary['publications']:publication(folder/Path(pub['path']).name,pub)
            grid,scalars,catalog=[load(folder/f'scan{scan}_{label}.npz') for label in ('grid','audit','catalog')]
            grids.append(grid);catalogs.append(catalog)
            require(same(grid['drift_hz_s'],rates) and same(grid['offsets'],offsets), 'Rate grid differs')
            require(len(catalog['ess']) == summary['local_hits'] and (catalog['ess'] >= 10).all() and np.isfinite(catalog['ess']).all(), 'Catalog length/scores differ')
            ri=catalog['drift_index']; widthcol=catalog['width_channels']; c=catalog['channel_at_midpoint']
            require(((ri>=0)&(ri<839)).all() and ((c>=q*4096)&(c<(q+1)*4096)).all(), 'Catalog grid support differs')
            require(same(catalog['drift_hz_s'],rates[ri]) and same(catalog['frequency_at_midpoint_mhz'],scope['fch1_mhz']+c*scope['df_hz']/1e6), 'Catalog physical coordinates differ')
            require(np.isin(widthcol,WIDTHS).all(), 'Catalog width differs')
            for width,stride in zip(WIDTHS,STRIDES):
                centers=np.arange(q*4096,(q+1)*4096,stride,dtype=np.int32)
                require(same(grid[f'centers_width_{width}'],centers), 'Search center grid differs')
                calibration=grid[f'calibration_width_{width}']
                require(calibration.shape == (839,2) and np.isfinite(calibration).all() and (calibration[:,1]>0).all(), 'Calibration shape/values differ')
                chosen=np.array([0,len(centers)//2,len(centers)-1]); sample=centers[chosen]
                require(same(scalars[f'scalar_centers_width_{width}'],sample) and same(scalars[f'scalar_ris_width_{width}'],np.array([0,419,838])), 'Scalar audit coordinates differ')
                mask=widthcol==width
                require(((c[mask]-q*4096)%stride==0).all(), 'Catalog center stride differs')
                require((catalog['ess'][mask] <= grid[f'max_ess_width_{width}'][(c[mask]-q*4096)//stride]).all(), 'Catalog exceeds saved maximum')
                for row,index in enumerate((0,419,838)):
                    vector=direct_vector(y,offsets[index],centers-record['support_start'],width)
                    med=float(np.median(vector)); scale=float(1.4826*np.median(np.abs(vector-med)))
                    err=float(np.max(np.abs(np.array([med,scale])-calibration[index])))
                    require(err < 5e-5, 'Independent bounded calibration vector differs')
                    max_vector_error=max(max_vector_error,err); count_vectors+=1
                    for column,center in enumerate(sample):
                        summed=scalar_track(y,offsets[index],int(center)-record['support_start'],width)
                        err=abs(summed-float(scalars[f'scalar_sums_width_{width}'][row,column]))
                        require(err < 5e-5, 'Independent scalar track differs')
                        max_scalar_error=max(max_scalar_error,err);count_scalar+=1
        association_pub=complete['association']['publication']; publication(folder/'PARTIAL_ASSOCIATION.npz',association_pub)
        assoc=load(folder/'PARTIAL_ASSOCIATION.npz')
        seeds={key:np.concatenate([catalogs[i][key] for i in (0,2,4)]) for key in catalogs[0]}
        seeds['source_scan']=np.concatenate([np.full(len(catalogs[i]['ess']),i,dtype=np.int8) for i in (0,2,4)])
        n=len(seeds['ess']); total_seeds+=n
        for key,value in seeds.items():require(same(value,assoc['seed_'+key]), 'Association seed catalog differs')
        center=assoc['forced_center_local_ess']; maximum=assoc['forced_neighborhood_max_local_ess']; valid=assoc['forced_valid']
        require(center.shape == maximum.shape == valid.shape == (n,6), 'Association six-slot shape differs')
        require(np.isnan(center[:,5]).all() and np.isnan(maximum[:,5]).all() and not valid[:,5].any() and (assoc['predicted_native_center'][:,5] == -1).all(), 'OFF5 was substituted')
        require(np.isfinite(center[:,:5][valid[:,:5]]).all() and np.isfinite(maximum[:,:5][valid[:,:5]]).all(), 'Supported associations must be finite')
        sample_rows=fixed_rows(n)
        for scope,record,y,grid in zip(plan['scans'],records,supports,grids):
            scan=scope['scan']
            source_times=np.array([plan['scans'][int(index)]['tref_midpoint_mjd'] for index in seeds['source_scan']])
            gaps=(scope['tref_midpoint_mjd']-source_times)*86400
            predicted=np.rint((seeds['frequency_at_midpoint_mhz']+seeds['drift_hz_s']*gaps/1e6-scope['fch1_mhz'])*1e6/scope['df_hz']).astype(np.int32)
            radii=np.ceil(1+.5*(rates[1]-rates[0])*np.abs(gaps)/abs(scope['df_hz'])).astype(np.int64)
            shifts=offsets[seeds['drift_index']]; local=predicted-record['support_start']; half=seeds['width_channels']//2
            supported=(local+shifts.min(axis=1)-half-radii>=0)&(local+shifts.max(axis=1)+half+radii<y.shape[1])
            require(same(predicted,assoc['predicted_native_center'][:,scan]) and same(supported,valid[:,scan]), 'Independent association geometry/support differs')
            require(np.isnan(center[~supported,scan]).all() and np.isnan(maximum[~supported,scan]).all(), 'Unsupported association was filled')
            for row in sample_rows[supported[sample_rows]]:
                index=int(seeds['drift_index'][row]); width=int(seeds['width_channels'][row]); radius=int(radii[row]); midpoint=int(local[row])
                sums=np.array([scalar_track(y,offsets[index],midpoint+delta,width) for delta in range(-radius,radius+1)])
                median,scale=grid[f'calibration_width_{width}'][index]
                scores=(sums-median)/scale
                expected=np.array([scores[radius],scores.max()]); actual=np.array([center[row,scan],maximum[row,scan]])
                err=float(np.max(np.abs(expected-actual))); tolerance=5e-5/scale+1e-12
                require(err <= tolerance, 'Independent forced scalar scores differ')
                # No threshold is silently crossed inside the accepted numerical bound.
                for threshold in (5,10):
                    require(np.array_equal(expected>=threshold,actual>=threshold), 'Numerical replay changes a classification threshold')
                max_forced_error=max(max_forced_error,err);count_assoc+=1
        supported,on3,off,status=classifications(center,maximum,valid)
        for key,value in [('available_scans_supported',supported),('three_ON_pass',on3),('available_OFF_veto',off),('candidate_status',status)]:
            require(same(assoc[key],value), 'Independent partial classification differs: '+key)
        require(not assoc['complete_OFF_support'].any(), 'Complete OFF qualification is impossible')
        expected_source_error=np.abs(center[np.arange(n),seeds['source_scan']]-seeds['ess'])
        require(same(expected_source_error,assoc['source_ess_error']) and (expected_source_error == 0).all(), 'Source consistency differs')
        summary=complete['association']; counts={state:int((status==state).sum()) for state in STATES}
        require(summary['status_counts'] == counts and summary['ON_local_catalog_rows'] == n and summary['three_ON_pass_rows'] == int(on3.sum()) and summary['available_OFF_veto_rows'] == int(off.sum()), 'Association summary counts differ')
        for state,value in counts.items():totals[state]+=value
        q_reviews.append({'q':q,'ON_seed_rows':n,'status_counts':counts})
    require(count_scalar == 1440 and count_vectors == 480, 'Bounded audit coordinate count differs')
    require(sha(planpath) == ph, 'Plan changed during independent audit')
    require(snapshot(out) == original_snapshot, 'Saved output tree changed during independent review')
    return {'schema':'SETI_BU_INDEPENDENT_SAVED_OUTPUT_REVIEW_V1','status':'PASS_BOUNDED_INDEPENDENT_REVIEW',
            'completed_utc':datetime.now(timezone.utc).isoformat(),'plan_sha256':ph,
            'batch_complete_sha256':sha(out/'BATCH_COMPLETE.json'),'batch':result['batch'],'q_list':qs,
            'all_saved_output_files_unchanged_during_review':True,'saved_output_file_count':len(original_snapshot),
            'ON_seed_rows_all_semantically_reviewed':total_seeds,'status_counts':totals,'q_reviews':q_reviews,
            'independent_scalar_audit_sums':count_scalar,'independent_calibration_vectors':count_vectors,
            'independent_selected_forced_measurement_slots':count_assoc,
            'maximum_scalar_sum_error':max_scalar_error,'maximum_calibration_error':max_vector_error,
            'maximum_selected_forced_ess_error':max_forced_error,'normalization_review':normal,
            'complete_OFF_support':False,'original_coverage_credit':0,
            'full_cadence_candidate_assessment':'NOT_EVALUABLE_MISSING_OFF5','wall_seconds':time.monotonic()-began,
            'limits':['Not a second full839rate search; calibrated ESS is not a false-alarm probability.',
                      'Association geometry and classification all rows; numerical forced replay fixed<=129seedrows perq.',
                      'Original codec/native provenance inherited, no independent decode or full-six-scan qualification.',
                      'Forced points use destination q-local calibration even outside that q core, matching the declared BN family.']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True);parser.add_argument('--check-normalization',action='store_true')
    args=parser.parse_args()
    def deadline(signum,frame):
        raise TimeoutError('Independent BU review120second wallclock limit')
    signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,120)
    result=audit(args.plan,args.out,args.check_normalization)
    args.receipt.parent.mkdir(parents=True,exist_ok=True)
    with args.receipt.open('x') as stream:
        json.dump(result,stream,indent=2,sort_keys=True,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    print(json.dumps(result,sort_keys=True),flush=True)
