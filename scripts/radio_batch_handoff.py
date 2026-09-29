"""One atomic response delivery plus bounded next-request read, without polling PTY."""
import argparse
import json
import os
from pathlib import Path
import time
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_journal_radio import sync_dir
from radio_lossless_handoff import FileRPC,publish
MAX_REQUEST=1049600

def next_message(directory,sequence,timeout=20):
    directory=Path(directory);target=directory/f'request{sequence:04d}.json';started=time.monotonic()
    while True:
        if target.exists():
            raw=target.read_bytes()
            if not 0<len(raw)<=MAX_REQUEST:raise ValueError('Bounded batch request required')
            obj=json.loads(raw)
            if canonical(obj)!=raw or obj.get('id')!=sequence:raise ValueError('Canonical sequence differs')
            return {'kind':'request','bytes':len(raw),'first':raw[:48000].decode('ascii')}
        done=directory/'done.json'
        if done.exists():return {'kind':'done','result':json.loads(done.read_bytes())}
        if time.monotonic()-started>timeout:raise TimeoutError('Next request/done absent; no retry')
        time.sleep(.01)

def deliver_and_next(directory,sequence,timeout=20):
    directory=Path(directory);target=directory/f'response{sequence:04d}.json';temp=Path(str(target)+'.tmp')
    if target.exists():raise ValueError('Existing response cannot be replaced')
    raw=temp.read_bytes()
    if not 0<len(raw)<=16*1024**2:raise ValueError('Bounded response required')
    reply=json.loads(raw)
    if type(reply.get('id')) is not int or reply['id']!=sequence or type(reply.get('ok')) is not bool:
        raise ValueError('Response identity/status differs')
    if set(reply)!=({'id','ok','result'} if reply['ok'] else {'id','ok','error','automatic_retry'}):
        raise ValueError('Exact response frame required')
    if not reply['ok'] and reply['automatic_retry'] is not False:raise ValueError('Retries prohibited')
    with temp.open('rb') as stream:os.fsync(stream.fileno())
    os.rename(temp,target);sync_dir(directory)
    return next_message(directory,sequence+1,timeout)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('sequence',type=int);p.add_argument('--deliver',action='store_true');a=p.parse_args()
    f=deliver_and_next if a.deliver else next_message
    print(json.dumps(f(a.directory,a.sequence),ensure_ascii=True))
