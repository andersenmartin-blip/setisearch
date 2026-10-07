"""Derive the P C source from the exact immutable N source. No compilation."""
import hashlib
from pathlib import Path

SOURCE = Path('results_radio_callback_barrier_source_20261006n/audit_collector.c')
EXPECTED = '659ff8b2f3cbc325731a6c39361c224cc3d23cc8bef23789b54d4b21b3fdcf85'


def derive(raw):
    if not isinstance(raw, bytes) or hashlib.sha256(raw).hexdigest() != EXPECTED:
        raise ValueError('exact N source required')
    text = raw.decode()
    replacements = [
        ('struct object { int fd, live; struct stat before; };',
         'struct object { int fd, live; uintptr_t *cookie_slot; struct stat before; };'),
        ('o->fd=fd;o->live=1;*cookie=(uintptr_t)gen;',
         'o->fd=fd;o->live=1;o->cookie_slot=cookie;*cookie=(uintptr_t)gen;'),
        ('void la_activity(uintptr_t *cookie, unsigned int flag) {\n'
         '    enter();\n'
         '    if(flag!=LA_ACT_ADD && flag!=LA_ACT_DELETE && flag!=LA_ACT_CONSISTENT) veto(BAD_PHASE);\n'
         '    emit(ACTIVITY,(uint64_t)*cookie,0,0,flag,"","",-1,0);leave();\n'
         '}',
         'static uint64_t activity_generation(uintptr_t *cookie) {\n'
         '    if(!cookie) veto(BAD_COOKIE);\n'
         '    uint64_t found=0;\n'
         '    for(uint64_t gen=1;gen<=generations;gen++) {\n'
         '        if(objects[gen].cookie_slot==cookie) {\n'
         '            if(found) veto(BAD_COOKIE);\n'
         '            found=gen;\n'
         '        }\n'
         '    }\n'
         '    if(!generations) return 0;\n'
         '    if(!found || !main_generation || found!=main_generation) veto(BAD_COOKIE);\n'
         '    return found;\n'
         '}\n'
         'void la_activity(uintptr_t *cookie, unsigned int flag) {\n'
         '    enter();\n'
         '    if(flag!=LA_ACT_ADD && flag!=LA_ACT_DELETE && flag!=LA_ACT_CONSISTENT) veto(BAD_PHASE);\n'
         '    uint64_t gen=activity_generation(cookie);\n'
         '    emit(ACTIVITY,gen,0,0,flag,"","",-1,0);leave();\n'
         '}')]
    for old, new in replacements:
        if text.count(old) != 1:
            raise ValueError('unique N replacement context required')
        text = text.replace(old, new)
    if '(uint64_t)*cookie,0,0,flag' in text:
        raise ValueError('raw activity cookie serialization retained')
    return text.encode()


if __name__ == '__main__':
    import sys
    sys.stdout.buffer.write(derive(SOURCE.read_bytes()))
