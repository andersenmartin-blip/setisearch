"""Size-bounded M43H transport retaining legacy range checkpoint integrity."""
import json
from urllib.request import Request,urlopen
from . import http_range_v0p6 as old

MAX_REQUEST=8*1024**2
MAX_READ=32*1024**2
TIMEOUT=30.
COUNTERS={'head_attempts':0,'head_completed':0,'range_attempts':0,'range_completed':0,'accepted_range_bytes':0}


def live_identity(url):
    COUNTERS['head_attempts']+=1
    identity=old.remote_identity(url,timeout=TIMEOUT)
    COUNTERS['head_completed']+=1
    return identity


class BoundedMirror(old.SparseRangeMirror):
    def __init__(self,path,identity):
        super().__init__(path,identity,workers=1,timeout=TIMEOUT,retries=1,validate_checkpoint_payloads=True)

    def _load_checkpoint(self,validate_payloads):
        r=json.loads(self.checkpoint_path.read_text())
        if any(s['stop']-s['start']>MAX_REQUEST for s in r.get('segments',[])):
            raise ValueError('checkpoint segment exceeds M43H request bound')
        super()._load_checkpoint(True)

    def prefetch(self,ranges):
        # Each parent invocation has one bounded interval, so its merge cannot
        # create an oversized request or a queue of resident response payloads.
        for r in old._merge_ranges(ranges):
            for start in range(r.start,r.stop,MAX_REQUEST):
                super().prefetch((old.ByteRange(start,min(start+MAX_REQUEST,r.stop)),))

    def _request(self,interval):
        if interval.length>MAX_REQUEST:raise ValueError('request exceeds bound')
        COUNTERS['range_attempts']+=1
        req=Request(self.identity.url,headers={'User-Agent':'setisearch-m43h/1.0',
            'Range':f'bytes={interval.start}-{interval.stop-1}','If-Range':self.identity.etag,'Accept-Encoding':'identity'})
        with urlopen(req,timeout=TIMEOUT) as response:
            status=int(getattr(response,'status',response.getcode()))
            match=old._CONTENT_RANGE.fullmatch(str(response.headers.get('Content-Range','')))
            coords=tuple(map(int,match.groups())) if match else None
            if (status!=206 or coords!=(interval.start,interval.stop-1,self.identity.size)
                    or response.headers.get('ETag')!=self.identity.etag
                    or response.headers.get('Content-Encoding','identity') not in ('','identity')):
                raise ValueError('HTTP identity/range mismatch before body read')
            payload=response.read(interval.length+1)
        if len(payload)!=interval.length:raise ValueError('HTTP payload length mismatch')
        COUNTERS['range_completed']+=1;COUNTERS['accepted_range_bytes']+=len(payload)
        return payload

    def read(self,size=-1):
        if type(size) is not int or size<0 or size>MAX_READ:
            raise ValueError('unbounded or oversized HDF5 read rejected')
        return super().read(size)
