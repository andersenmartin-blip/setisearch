"""Wire-v2 callback barrier primitives. No native launcher or release authority.

The bytes/transport fixtures check channel boundaries. They do not authenticate
an observer or certify that mapped-inode/kernel/process evidence is available.
"""
import array
import select
import socket
import struct
import time

EVENT = struct.Struct('<4sHHIIQQQQQQIIQQQHH')
ACK = struct.Struct('<4sHHIIQI')
MAX_PACKET = 100 + 2 * 1024
MAX_EVENT_COUNT = 4096
MAX_GENERATIONS = 256
CALLBACK_TIMEOUT = 2.0


class Refusal(ValueError): pass


def event_identity(raw):
    if type(raw) is not bytes or not EVENT.size<=len(raw)<=MAX_PACKET:
        raise Refusal('complete bounded event bytes required')
    values=EVENT.unpack_from(raw)
    magic,version,kind,sequence,pid,generation=values[:6]
    name_len,path_len=values[-2:]
    if (magic!=b'RLA1' or version!=2 or not 1<=kind<=6 or sequence>=MAX_EVENT_COUNT or pid==0
            or generation>MAX_GENERATIONS or name_len>=1024 or path_len>=1024
            or len(raw)!=EVENT.size+name_len+path_len):
        raise Refusal('exact new event version/identity/length required')
    # This is only framing, not the L/M object/namespace/content validator.
    return {'kind':kind,'sequence':sequence,'pid':pid,'generation':generation}


def fixture_ack_bytes(event,decision):
    """Pure fixture encoding; the returned bytes confer no release authority."""
    if type(event) is not dict or set(event)!={'kind','sequence','pid','generation'}:
        raise Refusal('exact parsed fixture identity required')
    limits={'kind':(1,6),'sequence':(0,MAX_EVENT_COUNT-1),'pid':(1,2**32-1),'generation':(0,MAX_GENERATIONS)}
    for name,(low,high) in limits.items():
        if type(event[name]) is not int or not low<=event[name]<=high: raise Refusal('exact bounded fixture identity required')
    if type(decision) is not int or decision not in (0,1): raise Refusal('exact rejection/fixture approval bit required')
    return ACK.pack(b'RACK',2,event['kind'],event['sequence'],event['pid'],event['generation'],decision)


def inspect_ack(raw,event):
    fixture_ack_bytes(event,1)  # exact types/ranges before identity comparison
    if type(raw) is not bytes or len(raw)!=ACK.size: raise Refusal('one complete exact acknowledgment required')
    magic,version,kind,sequence,pid,generation,decision=ACK.unpack(raw)
    if (magic!=b'RACK' or version!=2 or decision not in (0,1)
            or {'kind':kind,'sequence':sequence,'pid':pid,'generation':generation}!=event):
        raise Refusal('acknowledgment version/event/process/generation drift')
    if decision!=1: raise Refusal('observer rejection retained')
    return {'status':'FIXTURE_ACK_BYTES_MATCH_NO_OBSERVER_AUTHENTICATION',
            'event':dict(event),'observer_authentication':False,'native_or_science_release_authority':False}


class SourceBarrier:
    """Real local socket wait used only in source fixtures; no observer release."""
    def __init__(self): self.poisoned=False;self.closed=False;self.failure=None;self.raw_ack=None
    def wait_fixture(self,channel,event,seconds=CALLBACK_TIMEOUT):
        if self.poisoned or self.closed: raise Refusal('closed or failed barrier cannot resume')
        if type(seconds) not in (int,float) or type(seconds) is bool or not 0<seconds<=CALLBACK_TIMEOUT:
            raise Refusal('bounded source-fixture timeout required')
        received=[];raw=b''
        try:
            if channel.getsockopt(socket.SOL_SOCKET,socket.SO_TYPE)!=socket.SOCK_SEQPACKET:
                raise Refusal('sequenced packet acknowledgment channel required')
            deadline=time.monotonic()+seconds
            while True:
                remaining=deadline-time.monotonic()
                if remaining<=0: raise Refusal('callback acknowledgment timeout')
                ready,_,_=select.select([channel],[],[],remaining)
                if not ready: raise Refusal('callback acknowledgment timeout')
                try:
                    raw,ancillary,flags,_=channel.recvmsg(ACK.size+1,socket.CMSG_SPACE(16),socket.MSG_DONTWAIT|socket.MSG_CMSG_CLOEXEC)
                except BlockingIOError: continue
                invalid=False
                for level,kind,body in ancillary:
                    if level==socket.SOL_SOCKET and kind==socket.SCM_RIGHTS:
                        width=array.array('i').itemsize;whole=len(body)//width*width
                        values=array.array('i');values.frombytes(body[:whole]);received.extend(values)
                    invalid=True
                allowed=socket.MSG_EOR|socket.MSG_CMSG_CLOEXEC
                if invalid or flags&~allowed: raise Refusal('acknowledgment ancillary/truncation/unknown-flag veto')
                if not raw: raise Refusal('peer closed before acknowledgment')
                self.raw_ack=raw.hex();receipt=inspect_ack(raw,event);self.closed=True;return receipt
        except BaseException as exc:
            self.poisoned=True;self.failure={'reason':str(exc),'raw_ack_hex':raw.hex(),'received_descriptors':len(received)}
            raise
        finally:
            import os
            for fd in received: os.close(fd)


def reject(channel,event):
    """A veto may be sent; positive production release is deliberately closed."""
    raw=fixture_ack_bytes(event,0)
    if channel.sendmsg([raw],[],socket.MSG_DONTWAIT|socket.MSG_NOSIGNAL)!=len(raw):
        raise Refusal('short observer veto send')


def release(*args,**kwargs):
    raise Refusal('no qualified authenticated mapped-inode/kernel/process/terminal outer; positive release closed')


def dispatch(*args,**kwargs): raise Refusal('N source has no native execution or scientific authority')
