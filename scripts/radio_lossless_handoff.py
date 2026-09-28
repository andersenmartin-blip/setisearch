"""Bounded atomic request/done-file handoff; no unconditional terminal polling."""
import argparse
import json
import os
from pathlib import Path
import time
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_journal_radio import durable_write,sync_dir

def publish(path,value):
    path=Path(path)
    if path.exists():raise ValueError('Handoff cannot overwrite an existing sequence')
    temp=path.with_name(path.name+'.pending');durable_write(temp,canonical(value))
    os.rename(temp,path);sync_dir(path.parent)

def next_message(directory,sequence,timeout=20):
    directory=Path(directory);target=directory/f'request{sequence:04d}.json';started=time.monotonic()
    while True:
        if target.exists():
            raw=target.read_bytes()
            if not 0<len(raw)<=600000:raise ValueError('Bounded request framing required')
            obj=json.loads(raw)
            if canonical(obj)!=raw or obj.get('id')!=sequence:raise ValueError('Sequence/canonical framing changed')
            return {'kind':'request','bytes':len(raw),'first':raw[:48000].decode('ascii')}
        done=directory/'done.json'
        if done.exists():return {'kind':'done','result':json.loads(done.read_bytes())}
        if time.monotonic()-started>timeout:raise TimeoutError('Request/done handoff absent; stop without retry')
        time.sleep(.01)

class FileRPC:
    def __init__(self,directory):
        self.path=Path(directory);self.path.mkdir(parents=True,exist_ok=False);self.sequence=0
    def __call__(self,method,params):
        self.sequence+=1;n=self.sequence
        publish(self.path/f'request{n:04d}.json',{'id':n,'method':method,'params':params})
        target=self.path/f'response{n:04d}.json';started=time.monotonic()
        while not target.exists():
            if time.monotonic()-started>120:raise TimeoutError('Tool response absent; stop without retry')
            time.sleep(.01)
        raw=target.read_bytes()
        if len(raw)>16*1024**2:raise ValueError('Response framing cap exceeded')
        reply=json.loads(raw)
        if reply.get('id')!=n or reply.get('ok') is not True:raise RuntimeError('Tool broker stopped: '+str(reply.get('error')))
        return reply['result']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('sequence',type=int);a=p.parse_args()
    print(json.dumps(next_message(a.directory,a.sequence),ensure_ascii=True))
