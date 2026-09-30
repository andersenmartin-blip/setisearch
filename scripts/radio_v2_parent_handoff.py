"""Bounded delivery/next-request framing for the new v2 archive tool broker."""
import argparse
import json
import os
from pathlib import Path
import time
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_journal_radio import sync_dir

def next_message(directory,sequence):
    directory=Path(directory);started=time.monotonic()
    while True:
        path=directory/f'request{sequence:04d}.json'
        if path.exists():
            raw=path.read_bytes()
            if not 0<len(raw)<=600000:raise ValueError('Frozen RPC request cap exceeded')
            request=json.loads(raw)
            if canonical(request)!=raw or request.get('id')!=sequence:raise ValueError('RPC frame differs')
            return {'kind':'request','bytes':len(raw),'first':raw[:48000].decode('ascii')}
        path=directory/'done.json'
        if path.exists():return {'kind':'done','result':json.loads(path.read_bytes())}
        if time.monotonic()-started>20:raise TimeoutError('Next request absent; no retry')
        time.sleep(.01)

def deliver(directory,sequence):
    directory=Path(directory);target=directory/f'response{sequence:04d}.json';temp=Path(str(target)+'.tmp')
    if target.exists():raise ValueError('Existing RPC response cannot be overwritten')
    raw=temp.read_bytes()
    if not 0<len(raw)<=4*1024**2:raise ValueError('Frozen RPC reply bound exceeded')
    value=json.loads(raw)
    expected={'id','ok','result'} if value.get('ok') is True else {'id','ok','error','automatic_retry'}
    if (set(value)!=expected or value['id']!=sequence or type(value['ok']) is not bool
            or value['ok'] is False and value['automatic_retry'] is not False):
        raise ValueError('RPC reply frame differs')
    with temp.open('rb') as stream:os.fsync(stream.fileno())
    os.rename(temp,target);sync_dir(directory)
    return next_message(directory,sequence+1)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory');parser.add_argument('sequence',type=int)
    parser.add_argument('--deliver',action='store_true');args=parser.parse_args()
    print(json.dumps((deliver if args.deliver else next_message)(args.directory,args.sequence)))
