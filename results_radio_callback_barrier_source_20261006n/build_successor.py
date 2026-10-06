"""Copy the immutable L source and apply the exact new wire/ACK barrier delta."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
HERE=Path(__file__).resolve().parent
EXPECTED={'bytes':6816,'sha256':'d4ab251c65caeeb28eb84706c89ce4c959da2f8c5235920061069abeee135551'}

WAIT = r'''
/* The parent must retain/reject the event and independently validate its
 * stopped callback/mapping/kernel/process boundary before any future approval.
 * These raw bytes cannot authenticate that parent. The executable outer is
 * deliberately absent. Only wire-v2 peers can release this source barrier. */
static uint32_t read32(const unsigned char *p) {
    uint32_t value=0;for(unsigned i=0;i<4;i++) value|=(uint32_t)p[i]<<(i*8);return value;
}
static uint64_t read64(const unsigned char *p) {
    uint64_t value=0;for(unsigned i=0;i<8;i++) value|=(uint64_t)p[i]<<(i*8);return value;
}
static void await_ack(unsigned kind,uint32_t event_sequence,uint64_t gen) {
    struct timespec now;
    if(syscall(SYS_clock_gettime,CLOCK_MONOTONIC,&now)) _exit(125);
    uint64_t deadline=ns(now)+2000000000u;
    for(;;) {
        if(syscall(SYS_clock_gettime,CLOCK_MONOTONIC,&now)) _exit(125);
        uint64_t at=ns(now);
        if(at>=deadline) _exit(125);
        struct pollfd ready={.fd=CHANNEL_FD,.events=POLLIN,.revents=0};
        int milliseconds=(int)((deadline-at+999999u)/1000000u);
        long polled=syscall(SYS_poll,&ready,1,milliseconds);
        if(polled<0 && errno==EINTR) continue;
        if(polled<=0 || !(ready.revents&POLLIN)) _exit(125);
        unsigned char body[29]={0};
        struct iovec io={.iov_base=body,.iov_len=sizeof(body)};
        struct msghdr msg={.msg_iov=&io,.msg_iovlen=1};
        long count=syscall(SYS_recvmsg,CHANNEL_FD,&msg,MSG_DONTWAIT);
        if(count<0 && (errno==EINTR || errno==EAGAIN)) continue;
        if(count!=28 || (msg.msg_flags & ~MSG_EOR) || body[0]!='R' || body[1]!='A' || body[2]!='C' || body[3]!='K'
             || body[4]!=2 || body[5] || body[6]!=(unsigned char)kind || body[7]
             || read32(body+8)!=event_sequence || read32(body+12)!=owner
             || read64(body+16)!=gen || read32(body+24)>1) _exit(125);
        if(read32(body+24)==0) _exit(126);
        return;
    }
}
'''


def main():
    path=ROOT/'results_radio_loader_collector_source_20261006l'/'audit_collector.c';raw=path.read_bytes()
    if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=EXPECTED:
        raise ValueError('immutable L callback source differs')
    source=raw.decode()
    changes=[('#include <unistd.h>','#include <unistd.h>\n#include <poll.h>\n#include <errno.h>'),
             ('static unsigned length(const char *s) {',WAIT+'\nstatic unsigned length(const char *s) {'),
             ('u16(body+4,1);u16(body+6,(uint16_t)kind);u32(body+8,sequence++);u32(body+12,owner);',
              'uint32_t event_sequence=sequence++;\n    u16(body+4,2);u16(body+6,(uint16_t)kind);u32(body+8,event_sequence);u32(body+12,owner);'),
             ('if(sent != (long)io.iov_len) _exit(125);','if(sent != (long)io.iov_len) _exit(125);\n    if(kind!=VETO) await_ack(kind,event_sequence,gen);')]
    for old,new in changes:
        if source.count(old)!=1: raise ValueError('one exact maintained replacement required')
        source=source.replace(old,new,1)
    source=source.replace('/* L restricted Linux/x86-64/glibc LD_AUDIT source. Not activated or qualified.',
                          '/* N wire-v2 callback barrier, derived from immutable L. Not activated or qualified.',1)
    with (HERE/'audit_collector.c').open('xb') as out: out.write(source.encode())
    with (HERE/'L_BASE_SOURCE_PIN.json').open('x') as out:
        json.dump({'schema':'radio-N-original-L-source-pin-v1','authority_commit':'33f543de37ad6e66fac46d35d892024aa7b1776c',
                   'path':str(path.relative_to(ROOT)),'pin':EXPECTED,'original_unchanged':True,
                   'delta':'wire version2 and bounded exact acknowledgment before non-veto callback return',
                   'native_activation':False},out,sort_keys=True);out.write('\n')


if __name__=='__main__': main()
