"""Separate exploratory acquisition; original qualification runner is never called."""
import hashlib
import importlib.metadata
import importlib.util
import json
import resource
import signal
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCOPE = ROOT / 'tools/radio_quicklook_20261009/scope.json'

def main():
    started, cpu = time.monotonic(), time.process_time()
    scope = json.loads(SCOPE.read_text())
    for name, expected in scope['pinned_files'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen code/source mismatch: '+name)
    spec = importlib.util.spec_from_file_location('original_pure_reader', ROOT/'pilot_reader_20261008/value_reader.py')
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    source = json.loads((ROOT/'pilot_source_20261008/primary/source_manifest.json').read_text())
    sources = reader.validate_source(source)
    out = ROOT / 'results/radio_quicklook_20261009/arrays'
    out.mkdir(parents=True, exist_ok=False)
    ledger = {'source_body_bytes_received':1158240,
              'source_body_bytes_charged_upper_bound':1158240,
              'new_value_requests_attempted':0, 'complete':False,
              'spent_metadata_body_bytes':1158240,
              'source_body_byte_ceiling':2147483648}
    receipts, decoded, pipelines = [], [], []
    lo, hi = scope['crop_channel_interval_half_open']
    if not reader.PHYSICAL_INTERVAL[0] <= lo < hi <= reader.PHYSICAL_INTERVAL[1]:
        raise ValueError('Crop outside frozen physical source chunk')
    result = {'status':'EXPLORATORY_ACQUISITION_IN_PROGRESS',
              'original_qualification':'FAIL_CLOSED_UNCHANGED',
              'scope_sha256':hashlib.sha256(SCOPE.read_bytes()).hexdigest(),
              'source_channel0':lo, 'crop_channel_interval_half_open':[lo,hi],
              'value_read_requests':receipts,'decoded_files':decoded,
              'local_pipeline_records':pipelines,'scientific_search_run':False}
    def deadline(signum, frame):
        raise TimeoutError('Bounded exploratory acquisition deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(1800)
    resource.setrlimit(resource.RLIMIT_CPU, (600, 610))
    resource.setrlimit(resource.RLIMIT_AS, (4*1024**3,4*1024**3))
    try:
        h5py, plugin, np = reader.current_codecs()
        result['versions'] = {n:importlib.metadata.version(n) for n in ('h5py','hdf5plugin','numpy')}
        result['versions']['hdf5'] = h5py.version.hdf5_version
        opener = urllib.request.build_opener(reader.NoRedirect())
        for item in sources:
            path = out / (item['label']+'.compact.h5')
            with h5py.File(path, 'x', rdcc_nbytes=8*1024**2) as handle:
                dataset, pipeline = reader.create_compact_dataset(handle,item,h5py,plugin)
                pipelines.append({'scan_id':item['label'],**pipeline})
                for chunk in item['chunks']:
                    body = reader.acquire_chunk(item,chunk,ledger,out/'source_byte_ledger.json',receipts,opener)
                    origin = (chunk['time_row'],0,0)
                    dataset.id.write_direct_chunk(origin,body,filter_mask=0)
                    mask, retained = dataset.id.read_direct_chunk(origin)
                    if mask != 0 or retained != body:
                        raise ValueError('Compressed chunk roundtrip failed')
                    receipts[-1]['compact_raw_roundtrip_sha256'] = hashlib.sha256(retained).hexdigest()
                    reader.atomic_json(out/'acquisition_summary.json',result)
                handle.flush()
                selected = np.asarray(dataset[:,0,lo-reader.PHYSICAL_INTERVAL[0]:hi-reader.PHYSICAL_INTERVAL[0]],dtype='<f4')
                if selected.shape != (16,hi-lo) or not np.isfinite(selected).all() or (selected<0).any():
                    raise ValueError('Complete finite nonnegative power required')
                npy = out/(item['label']+'.npy')
                with npy.open('xb') as f:
                    np.save(f,selected,allow_pickle=False)
                decoded.append({'scan_id':item['label'],'array_file':npy.name,
                                'shape':list(selected.shape),'source_channel0':lo,
                                'array_sha256':hashlib.sha256(selected.tobytes()).hexdigest(),
                                'file_sha256':hashlib.sha256(npy.read_bytes()).hexdigest(),
                                'power_min':float(selected.min()),'power_max':float(selected.max())})
                print('DECODED',item['label'],selected.shape,flush=True)
                reader.atomic_json(out/'acquisition_summary.json',result)
        ledger['complete']=True
        result['status']='SIX_SCANS_ACQUIRED_EXPLORATORY_ONLY'
    except BaseException as e:
        result.update(status='FAILED_CLOSED_NO_RETRY',error_type=type(e).__name__,error=str(e))
        raise
    finally:
        signal.alarm(0)
        result.update(cpu_s=time.process_time()-cpu,wall_s=time.monotonic()-started,
                      peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        reader.atomic_json(out/'source_byte_ledger.json',ledger)
        reader.atomic_json(out/'acquisition_summary.json',result)

if __name__ == '__main__':
    main()
