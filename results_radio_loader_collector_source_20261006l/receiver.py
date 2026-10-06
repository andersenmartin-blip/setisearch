"""Real SCM_RIGHTS receiver source, tested with fabricated events/ordinary files.

No launcher, observer authentication, mapping attribution, runtime qualification
or native dispatch is provided. Callback-reopened descriptors do not prove
which inode was originally mapped. Socket peer credentials alone cannot cure it.
"""
import array
import hashlib
import json
import os
from pathlib import PurePosixPath
import socket
import stat
import struct

HEADER = struct.Struct("<4sHHIIQQQQQQIIQQQHH")
MAX_PACKET = 100 + 2 * 1024
MAX_EVENTS = 4096
MAX_OBJECTS = 256
MAX_READ = 1024 ** 3
MAX_RAW = 8 * 1024 ** 2
HANDSHAKE, OPEN, PREINIT, CLOSE, VETO, ACTIVITY = range(1, 7)


class Refusal(ValueError): pass


def canonical(value): return (json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode()
def identity(st):
    return {"device":st.st_dev,"inode":st.st_ino,"bytes":st.st_size,"mode":st.st_mode,
            "mtime_ns":st.st_mtime_ns,"ctime_ns":st.st_ctime_ns}
def path(value):
    if (type(value) is not str or not value.startswith("/") or value=="/" or "\0" in value
            or ".." in PurePosixPath(value).parts or str(PurePosixPath(value))!=value
            or len(value.encode())>=1024 or value.endswith(" (deleted)")):
        raise Refusal("canonical ordinary descriptor path required")


class Receiver:
    def __init__(self, pid, executable, expected_files):
        if type(pid) is not int or not 0<pid<2**32: raise Refusal("fixed local pid required")
        path(executable)
        if type(expected_files) is not dict or not 0<len(expected_files)<=MAX_OBJECTS or executable not in expected_files:
            raise Refusal("finite prospective file pins required")
        for name,pin in expected_files.items():
            path(name)
            if (type(pin) is not dict or set(pin)!={"bytes","sha256"} or type(pin["bytes"]) is not int
                    or not 0<pin["bytes"]<=MAX_READ or type(pin["sha256"]) is not str
                    or len(pin["sha256"])!=64 or any(c not in "0123456789abcdef" for c in pin["sha256"])):
                raise Refusal("exact bounded external pin required")
        self.pid=pid;self.executable=executable;self.expected=json.loads(canonical(expected_files))
        self.phase="new";self.sequence=0;self.time=0;self.main=None;self.objects={}
        self.raw=[];self.failures=[];self.read_bytes=0;self.raw_bytes=0;self.eof=False;self.poisoned=False

    def receive(self, channel):
        """One datagram; retain raw failure and close all refused descriptors."""
        if self.poisoned or self.eof: raise Refusal("closed or failed stream cannot resume")
        received=[];owned=False;raw=b""
        try:
            if channel.getsockopt(socket.SOL_SOCKET,socket.SO_TYPE)!=socket.SOCK_SEQPACKET:
                raise Refusal("sequenced packet channel required")
            raw,ancillary,flags,_=channel.recvmsg(MAX_PACKET+1,socket.CMSG_SPACE(16),socket.MSG_CMSG_CLOEXEC)
            invalid_ancillary=False
            for level,kind,body in ancillary:
                if level!=socket.SOL_SOCKET or kind!=socket.SCM_RIGHTS:
                    invalid_ancillary=True;continue
                width=array.array("i").itemsize;whole=len(body)//width*width
                values=array.array("i");values.frombytes(body[:whole]);received.extend(values)
                if whole!=len(body): invalid_ancillary=True
            if invalid_ancillary: raise Refusal("unsupported ancillary record")
            if flags & (socket.MSG_TRUNC|socket.MSG_CTRUNC): raise Refusal("truncated packet or descriptors")
            if not raw:
                if received or self.phase!="running": raise Refusal("EOF without complete startup")
                self.eof=True;return False
            self.raw_bytes+=len(raw)
            if self.raw_bytes>MAX_RAW or self.sequence>=MAX_EVENTS: raise Refusal("raw/event envelope exceeded")
            self.raw.append(raw.hex())
            event=self.decode(raw)
            if event["sequence"]!=self.sequence or event["pid"]!=self.pid or event["monotonic_ns"]<self.time:
                raise Refusal("event sequence/pid/time drift")
            self.transition(event,received)
            owned=event["kind"]==OPEN
            self.sequence+=1;self.time=event["monotonic_ns"];return True
        except BaseException as exc:
            self.poisoned=True
            self.failures.append({"raw_hex":raw.hex(),"descriptor_count":len(received),"reason":str(exc)})
            raise
        finally:
            if not owned:
                for fd in received: os.close(fd)

    def decode(self,raw):
        if not HEADER.size<=len(raw)<=MAX_PACKET: raise Refusal("bounded complete binary packet required")
        values=HEADER.unpack_from(raw)
        names=("magic","version","kind","sequence","pid","generation","namespace","load_base",
               "device","inode","bytes","mode","flags","mtime_ns","ctime_ns","monotonic_ns","name_len","path_len")
        e=dict(zip(names,values))
        if e["magic"]!=b"RLA1" or e["version"]!=1 or not 1<=e["kind"]<=6 or e["monotonic_ns"]==0:
            raise Refusal("exact wire version/kind/time required")
        if e["name_len"]>=1024 or e["path_len"]>=1024 or HEADER.size+e["name_len"]+e["path_len"]!=len(raw):
            raise Refusal("exact bounded name/path lengths required")
        body=raw[HEADER.size:]
        try: e["loader_name"]=body[:e["name_len"]].decode();e["resolved_path"]=body[e["name_len"]:].decode()
        except UnicodeError as exc: raise Refusal("UTF8 spelling required") from exc
        if e["namespace"]!=0: raise Refusal("extra namespaces unsupported")
        if e["kind"]!=OPEN:
            if any(e[k] for k in ("load_base","device","inode","bytes","mode","mtime_ns","ctime_ns","name_len","path_len")):
                raise Refusal("unexpected non-open payload fields")
        elif e["flags"]!=0: raise Refusal("unexpected open flags")
        return e

    def transition(self,e,fds):
        kind=e["kind"];gen=e["generation"]
        if kind!=OPEN and fds: raise Refusal("descriptor on non-open event")
        if kind==HANDSHAKE:
            if self.phase!="new" or gen!=0 or e["flags"]!=2: raise Refusal("one exact glibc handshake required")
            self.phase="startup"
        elif kind==OPEN:
            if self.phase not in ("startup","running") or gen!=len(self.objects)+1 or gen>MAX_OBJECTS or len(fds)!=1:
                raise Refusal("exclusive sequential generation and one descriptor required")
            resolved=e["resolved_path"];path(resolved)
            name=e["loader_name"]
            if "\0" in name: raise Refusal("loader spelling contains NUL")
            if not name:
                if self.phase!="startup" or self.main is not None or resolved!=self.executable:
                    raise Refusal("unique original main executable required")
            elif not name.startswith("/"): raise Refusal("relative/kernel pseudo-object unsupported")
            fd=fds[0];st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_size<=0: raise Refusal("ordinary held object required")
            declared={k:e[k] for k in identity(st)}
            if identity(st)!=declared: raise Refusal("descriptor identity differs from callback")
            if os.readlink('/proc/self/fd/'+str(fd))!=resolved: raise Refusal("held descriptor path differs")
            if resolved not in self.expected or st.st_size!=self.expected[resolved]["bytes"]:
                raise Refusal("unknown object or prospective size differs")
            digest=hashlib.sha256();offset=0
            while offset<st.st_size:
                amount=min(65536,st.st_size-offset)
                if self.read_bytes+amount>MAX_READ: raise Refusal("held object read cap")
                raw=os.pread(fd,amount,offset);self.read_bytes+=len(raw)
                if not raw: raise Refusal("held object truncated")
                offset+=len(raw);digest.update(raw)
            if identity(os.fstat(fd))!=declared or digest.hexdigest()!=self.expected[resolved]["sha256"]:
                raise Refusal("held object identity/hash changed")
            self.objects[gen]={"fd":fd,"identity":declared,"file_pin":dict(self.expected[resolved]),
                               "loader_name":name,"resolved_path":resolved,"load_base":e["load_base"],
                               "opened_sequence":self.sequence,"closed_sequence":None}
            if not name: self.main=gen
        elif kind==PREINIT:
            if self.phase!="startup" or gen!=self.main or e["flags"]: raise Refusal("startup/main preinit differs")
            self.phase="running"
        elif kind==CLOSE:
            if self.phase!="running" or gen not in self.objects or self.objects[gen]["closed_sequence"] is not None or e["flags"]:
                raise Refusal("unknown/double/early object close")
            if identity(os.fstat(self.objects[gen]["fd"]))!=self.objects[gen]["identity"]:
                raise Refusal("close descriptor identity drift")
            self.objects[gen]["closed_sequence"]=self.sequence
        elif kind==ACTIVITY:
            if self.phase not in ("startup","running") or e["flags"] not in (0,1,2): raise Refusal("unsupported activity")
            if gen and gen not in self.objects: raise Refusal("unknown activity cookie")
        else: raise Refusal("collector veto retained")

    def finish(self,waited_pid,exit_code):
        try: return self._finish(waited_pid,exit_code)
        except BaseException as exc:
            self.poisoned=True
            self.failures.append({"terminal_refusal":str(exc),"descriptor_count":len(self.objects)})
            raise

    def _finish(self,waited_pid,exit_code):
        if self.poisoned or not self.eof or self.phase!="running" or type(waited_pid) is not int or waited_pid!=self.pid or type(exit_code) is not int or exit_code!=0:
            raise Refusal("complete EOF and independently supplied exact successful wait required")
        for row in self.objects.values():
            if identity(os.fstat(row["fd"]))!=row["identity"]: raise Refusal("terminal held identity drift")
        self.phase="finished"
        return {"schema":"radio-L-descriptor-receiver-source-v1","status":"FD_STREAM_CHECK_ONLY_NO_AUTHENTICATED_NATIVE_OBSERVATION",
                "events":self.sequence,"raw_bytes":self.raw_bytes,"read_bytes":self.read_bytes,
                "generations":[{k:v for k,v in self.objects[g].items() if k!='fd'} for g in sorted(self.objects)],
                "transient_generations_retained":sum(v['closed_sequence'] is not None for v in self.objects.values()),
                "collector_authentication":False,"mapped_inode_binding":False,"historical_custody":False,
                "continuous_content_custody":False,"kernel_pseudo_objects_supported":False,
                "symbol_coverage":False,"process_descendant_terminal_io_qualified":False,
                "runtime_qualified":False,"codec_certificate":False,"native_or_science_authority":False}

    def close_retained_descriptors(self):
        """End an unqualified fixture/failed receiver without discarding events."""
        for row in self.objects.values():
            if row["fd"] is not None: os.close(row["fd"]);row["fd"]=None
        self.poisoned=True


def dispatch(*args,**kwargs): raise Refusal("L source has no native launcher or activation authority")
