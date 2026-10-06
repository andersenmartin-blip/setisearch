/* N wire-v2 callback barrier, derived from immutable L. Not activated or qualified.
 * Every unsupported object/channel condition terminates; no silent skips.
 * Callback descriptors are newly opened: they do NOT establish which inode
 * the loader mapped. An independent kernel mapping/IO observer is mandatory.
 */
#define _GNU_SOURCE
#include <link.h>
#include <stdint.h>
#include <stdatomic.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>
#include <poll.h>
#include <errno.h>

#ifndef __x86_64__
#error "L source has no qualified architecture other than Linux x86-64"
#endif
_Static_assert(LAV_CURRENT == 2, "exact glibc audit version required");
_Static_assert(sizeof(uintptr_t) == 8, "64-bit cookie required");
#define CHANNEL_FD 198
#define MAX_OBJECTS 256
#define MAX_NAME 1024
#define HEADER 100
enum { HANDSHAKE=1, OPEN=2, PREINIT=3, CLOSE=4, VETO=5, ACTIVITY=6 };
enum { BAD_VERSION=1, BAD_NAMESPACE=2, BAD_PATH=3, BAD_FILE=4,
       BAD_COOKIE=5, BAD_PHASE=6, OBJECT_CAP=7, IDENTITY_DRIFT=8 };
static atomic_flag locked = ATOMIC_FLAG_INIT;
static uint32_t sequence, owner;
static uint64_t generations, main_generation;
static int running;
struct object { int fd, live; struct stat before; };
static struct object objects[MAX_OBJECTS+1];

static void enter(void) {
    if (atomic_flag_test_and_set(&locked)) _exit(123);
    if (owner && owner != (uint32_t)syscall(SYS_getpid)) _exit(124);
}
static void leave(void) { atomic_flag_clear(&locked); }
static void u16(unsigned char *p, uint16_t x) { p[0]=(unsigned char)x; p[1]=(unsigned char)(x>>8); }
static void u32(unsigned char *p, uint32_t x) { for(unsigned i=0;i<4;i++) p[i]=(unsigned char)(x>>(i*8)); }
static void u64(unsigned char *p, uint64_t x) { for(unsigned i=0;i<8;i++) p[i]=(unsigned char)(x>>(i*8)); }
static uint64_t ns(struct timespec t) { return (uint64_t)t.tv_sec*1000000000u+(uint64_t)t.tv_nsec; }

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

static unsigned length(const char *s) {
    unsigned n=0; while(n<MAX_NAME && s[n]) n++; return n;
}
static void emit(unsigned kind, uint64_t gen, uint64_t namespace_id, uint64_t base,
                 unsigned flags, const char *name, const char *path, int fd,
                 const struct stat *st) {
    unsigned char body[HEADER+2*MAX_NAME]={0};
    struct timespec now;
    if (syscall(SYS_clock_gettime,CLOCK_MONOTONIC,&now) || sequence>=4096) _exit(125);
    unsigned nl=length(name), pl=length(path);
    if (nl>=MAX_NAME || pl>=MAX_NAME) _exit(125);
    body[0]='R';body[1]='L';body[2]='A';body[3]='1';
    uint32_t event_sequence=sequence++;
    u16(body+4,2);u16(body+6,(uint16_t)kind);u32(body+8,event_sequence);u32(body+12,owner);
    u64(body+16,gen);u64(body+24,namespace_id);u64(body+32,base);
    if(st) {
        u64(body+40,(uint64_t)st->st_dev);u64(body+48,(uint64_t)st->st_ino);
        u64(body+56,(uint64_t)st->st_size);u32(body+64,(uint32_t)st->st_mode);
        u64(body+72,ns(st->st_mtim));u64(body+80,ns(st->st_ctim));
    }
    u32(body+68,flags);u64(body+88,ns(now));u16(body+96,(uint16_t)nl);u16(body+98,(uint16_t)pl);
    for(unsigned i=0;i<nl;i++) body[HEADER+i]=(unsigned char)name[i];
    for(unsigned i=0;i<pl;i++) body[HEADER+nl+i]=(unsigned char)path[i];
    struct iovec io={.iov_base=body,.iov_len=HEADER+nl+pl};
    union { struct cmsghdr alignment; unsigned char bytes[CMSG_SPACE(sizeof(int))]; } control={0};
    struct msghdr msg={.msg_iov=&io,.msg_iovlen=1};
    if(fd>=0) {
        msg.msg_control=control.bytes;msg.msg_controllen=sizeof(control.bytes);
        struct cmsghdr *c=CMSG_FIRSTHDR(&msg);
        c->cmsg_level=SOL_SOCKET;c->cmsg_type=SCM_RIGHTS;c->cmsg_len=CMSG_LEN(sizeof(int));
        *(int *)CMSG_DATA(c)=fd;
    }
    long sent=syscall(SYS_sendmsg,CHANNEL_FD,&msg,MSG_DONTWAIT|MSG_NOSIGNAL);
    if(sent != (long)io.iov_len) _exit(125);
    if(kind!=VETO) await_ack(kind,event_sequence,gen);
}
static void veto(unsigned reason) {
    emit(VETO,0,0,0,reason,"","",-1,0);_exit(126);
}
static void descriptor_name(int fd, char *path) {
    char proc[64]="/proc/self/fd/", digits[16];unsigned n=0,pos=14;
    unsigned x=(unsigned)fd;do {digits[n++]=(char)('0'+x%10);x/=10;}while(x);
    while(n) { proc[pos++]=digits[--n]; }
    proc[pos]=0;
    long size=syscall(SYS_readlinkat,AT_FDCWD,proc,path,MAX_NAME-1);
    if(size<=0 || size>=MAX_NAME-1) veto(BAD_PATH);
    path[size]=0;
    if(path[0]!='/') veto(BAD_PATH);
}
static int same_stat(const struct stat *a, const struct stat *b) {
    return a->st_dev==b->st_dev && a->st_ino==b->st_ino && a->st_mode==b->st_mode &&
           a->st_nlink==b->st_nlink && a->st_size==b->st_size &&
           ns(a->st_mtim)==ns(b->st_mtim) && ns(a->st_ctim)==ns(b->st_ctim);
}
unsigned int la_version(unsigned int version) {
    enter();owner=(uint32_t)syscall(SYS_getpid);
    if(version<2) veto(BAD_VERSION);
    emit(HANDSHAKE,0,0,0,2,"","",-1,0);leave();return 2;
}
unsigned int la_objopen(struct link_map *map, Lmid_t lmid, uintptr_t *cookie) {
    enter();
    if(!owner) _exit(125);
    if(lmid!=LM_ID_BASE) veto(BAD_NAMESPACE);
    if(generations>=MAX_OBJECTS) veto(OBJECT_CAP);
    const char *name=map->l_name;
    if(!name || length(name)>=MAX_NAME || (name[0] && name[0]!='/')) veto(BAD_PATH);
    if(!name[0] && (running || main_generation)) veto(BAD_PHASE);
    const char *open_name=name[0]?name:"/proc/self/exe";
    int fd=(int)syscall(SYS_openat,AT_FDCWD,open_name,O_RDONLY|O_CLOEXEC|O_NONBLOCK,0);
    if(fd<0) veto(BAD_FILE);
    uint64_t gen=++generations;struct object *o=&objects[gen];
    if(syscall(SYS_fstat,fd,&o->before) || !S_ISREG(o->before.st_mode) || o->before.st_size<=0) veto(BAD_FILE);
    char path[MAX_NAME];descriptor_name(fd,path);
    o->fd=fd;o->live=1;*cookie=(uintptr_t)gen;
    if(!name[0]) main_generation=gen;
    emit(OPEN,gen,0,(uint64_t)map->l_addr,0,name,path,fd,&o->before);
    leave();return 0; /* Symbol binding audit is explicitly unsupported. */
}
void la_preinit(uintptr_t *cookie) {
    enter();
    if(running || !main_generation || *cookie!=(uintptr_t)main_generation) veto(BAD_PHASE);
    running=1;emit(PREINIT,main_generation,0,0,0,"","",-1,0);leave();
}
unsigned int la_objclose(uintptr_t *cookie) {
    enter();uint64_t gen=(uint64_t)*cookie;
    if(!running || !gen || gen>generations || !objects[gen].live) veto(BAD_COOKIE);
    struct stat now;
    if(syscall(SYS_fstat,objects[gen].fd,&now) || !same_stat(&now,&objects[gen].before)) veto(IDENTITY_DRIFT);
    objects[gen].live=0;
    emit(CLOSE,gen,0,0,0,"","",-1,0);
    /* Hold even unloaded generations until process death; parent duplicates
       hold them beyond EOF/exit. No close-before-terminal custody shortcut. */
    leave();return 0;
}
void la_activity(uintptr_t *cookie, unsigned int flag) {
    enter();
    if(flag!=LA_ACT_ADD && flag!=LA_ACT_DELETE && flag!=LA_ACT_CONSISTENT) veto(BAD_PHASE);
    emit(ACTIVITY,(uint64_t)*cookie,0,0,flag,"","",-1,0);leave();
}
