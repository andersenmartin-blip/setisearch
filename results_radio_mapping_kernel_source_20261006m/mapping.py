"""Bounded Linux/x86-64 ELF and mapping geometry; no execution authority.

A snapshot matching a held fd is not a continuous mapped-content witness and
cannot authenticate L callbacks or a whole native/runtime/IO lifetime.
"""
import hashlib
import os
import re
import struct

MAX_MAP_BYTES = 128 * 1024
MAX_MAPS = 4096
MAX_AUX_BYTES = 16 * 1024
MAX_ELF_PREFIX = 64 * 1024
MAX_PHDRS = 128
MAX_KERNEL_BYTES = 64 * 1024
MAX_ADDRESS = 2 ** 64 - 1
EHDR = struct.Struct('<16sHHIQQQIHHHHHH')
PHDR = struct.Struct('<IIQQQQQQ')
AUX = struct.Struct('<QQ')
MAP = re.compile(rb'([0-9a-f]+)-([0-9a-f]+) ([r-][w-][x-][ps]) ([0-9a-f]+) ([0-9a-f]+):([0-9a-f]+) ([0-9]+)(?: +([^\n]*))?\n')


class Refusal(ValueError): pass


def exact_int(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise Refusal('bounded exact integer required')


def page_size(value):
    exact_int(value, 4096, 65536)
    if value & (value - 1): raise Refusal('power-of-two page size required')


def parse_maps(raw, page):
    page_size(page)
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_MAP_BYTES or not raw.endswith(b'\n'):
        raise Refusal('bounded complete maps bytes required')
    rows=[];last=0
    for line in raw.splitlines(keepends=True):
        if len(rows)>=MAX_MAPS or len(line)>4096: raise Refusal('maps row/line cap')
        match=MAP.fullmatch(line)
        if not match: raise Refusal('exact maps syntax required')
        start,end,perms,offset,major,minor,inode,name=match.groups()
        value={'start':int(start,16),'end':int(end,16),'permissions':perms.decode(),
               'offset':int(offset,16),'device_major':int(major,16),'device_minor':int(minor,16),
               'inode':int(inode),'raw_name_hex':(name or b'').hex()}
        for key in ('start','end','offset','inode'): exact_int(value[key],0,MAX_ADDRESS)
        if (value['start']>=value['end'] or value['start']<last
                or value['start']%page or value['end']%page or value['offset']%page):
            raise Refusal('overlapping/unordered/unaligned maps geometry')
        last=value['end'];rows.append(value)
    return rows


def parse_auxv(raw):
    if type(raw) is not bytes or not 0<len(raw)<=MAX_AUX_BYTES or len(raw)%AUX.size:
        raise Refusal('bounded complete ELF64 auxv required')
    values={};ended=False
    for offset in range(0,len(raw),AUX.size):
        kind,value=AUX.unpack_from(raw,offset)
        if ended: raise Refusal('auxv trailing records')
        if kind==0:
            if value!=0: raise Refusal('nonzero auxv terminator')
            ended=True;continue
        if kind in values: raise Refusal('duplicate auxv tag')
        values[kind]=value
    if not ended: raise Refusal('missing auxv terminator')
    if 6 not in values or 33 not in values or values[33]==0:
        raise Refusal('AT_PAGESZ/AT_SYSINFO_EHDR required')
    page_size(values[6])
    return values


def parse_elf(raw, declared_file_bytes):
    exact_int(declared_file_bytes,EHDR.size,2**40)
    if type(raw) is not bytes or not EHDR.size<=len(raw)<=MAX_ELF_PREFIX:
        raise Refusal('bounded ELF prefix required')
    fields=EHDR.unpack_from(raw)
    ident,kind,machine,version,entry,phoff,shoff,flags,ehsize,phsize,phnum,shsize,shnum,shstr=fields
    if (ident[:7]!=b'\x7fELF\x02\x01\x01' or ident[7] not in (0,3) or ident[8:]!=b'\0'*8
            or kind not in (2,3) or machine!=62 or version!=1 or flags!=0
            or ehsize!=EHDR.size or phsize!=PHDR.size or not 0<phnum<=MAX_PHDRS):
        raise Refusal('exact supported ELF64 little-endian x86-64 header required')
    end=phoff+phnum*phsize
    if phoff<EHDR.size or end>len(raw) or end>declared_file_bytes:
        raise Refusal('complete bounded original program-header table required')
    loads=[];phdr_virtual=None
    for index in range(phnum):
        type_,permission,file_offset,vaddr,paddr,file_size,memory_size,align=PHDR.unpack_from(raw,phoff+index*phsize)
        if type_==6:
            if phdr_virtual is not None or file_offset!=phoff or file_size!=phnum*phsize or memory_size!=file_size:
                raise Refusal('ambiguous original PT_PHDR')
            phdr_virtual=vaddr
        if type_!=1: continue
        if (permission & ~7 or file_size>memory_size or file_offset+file_size>declared_file_bytes
                or vaddr+memory_size>MAX_ADDRESS or align>2**32
                or (align>1 and (align & (align-1) or file_offset%align!=vaddr%align))):
            raise Refusal('invalid PT_LOAD extent/flags/alignment')
        loads.append({'index':index,'flags':permission,'file_offset':file_offset,'vaddr':vaddr,
                      'file_bytes':file_size,'memory_bytes':memory_size,'alignment':align})
    if not loads or not any(segment['flags']&1 for segment in loads):
        raise Refusal('executable PT_LOAD required')
    return {'type':kind,'entry':entry,'program_header_offset':phoff,'program_header_virtual':phdr_virtual,
            'program_header_count':phnum,'program_header_end':end,'loads':loads,
            'prefix_pin':{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()},
            'complete_file_body_verified':False}


def administrative_main_base(elf,auxv):
    """Derive only this administrative main's base from its own auxv/table."""
    if auxv.get(4)!=PHDR.size or auxv.get(5)!=elf['program_header_count'] or 3 not in auxv or 9 not in auxv:
        raise Refusal('exact administrative AT_PHDR/PHENT/PHNUM/ENTRY required')
    phoff=elf['program_header_offset'];end=elf['program_header_end']
    candidates=[segment['vaddr']+phoff-segment['file_offset'] for segment in elf['loads']
                if segment['file_offset']<=phoff and end<=segment['file_offset']+segment['file_bytes']]
    if len(candidates)!=1 or (elf['program_header_virtual'] is not None and elf['program_header_virtual']!=candidates[0]):
        raise Refusal('unique original program-header mapping required')
    base=auxv[3]-candidates[0];exact_int(base,0,MAX_ADDRESS)
    if base%auxv[6] or base+elf['entry']!=auxv[9] or (elf['type']==2 and base!=0):
        raise Refusal('administrative base/entry/ET_EXEC differs')
    return base


def executable_binding(rows, elf, load_base, descriptor_identity, page):
    """Snapshot inode+offset coverage for every executable file-backed page."""
    page_size(page);exact_int(load_base,0,MAX_ADDRESS)
    if load_base%page: raise Refusal('aligned loader base required')
    if elf['type']==2 and load_base!=0: raise Refusal('ET_EXEC cannot use relocated base in this scope')
    if type(descriptor_identity) is not dict or set(descriptor_identity)!={'device','inode','bytes'}:
        raise Refusal('exact external held-descriptor metadata required')
    for key in ('device','inode','bytes'): exact_int(descriptor_identity[key],1,2**64-1)
    devmajor,devminor=os.major(descriptor_identity['device']),os.minor(descriptor_identity['device'])
    covered=[]
    for segment in elf['loads']:
        if not segment['flags']&1: continue
        if segment['flags']&2 or segment['file_bytes']==0 or segment['memory_bytes']!=segment['file_bytes']:
            raise Refusal('writable/anonymous executable PT_LOAD unsupported')
        if segment['file_offset']%page!=segment['vaddr']%page:
            raise Refusal('loader page offset congruence differs')
        if segment['file_offset']+segment['file_bytes']>descriptor_identity['bytes']:
            raise Refusal('executable extent exceeds held file')
        start=load_base+segment['vaddr']//page*page
        end=load_base+(segment['vaddr']+segment['file_bytes']+page-1)//page*page
        if end>MAX_ADDRESS or start>=end: raise Refusal('relocated extent overflow')
        file_offset=segment['file_offset']//page*page;cursor=start;pieces=[]
        for row in rows:
            if row['end']<=cursor or row['start']>=end: continue
            if row['start']>cursor: raise Refusal('executable mapping gap')
            if (row['permissions']!='r-xp' or row['inode']!=descriptor_identity['inode']
                    or (row['device_major'],row['device_minor'])!=(devmajor,devminor)
                    or row['offset']+cursor-row['start']!=file_offset+cursor-start
                    or bytes.fromhex(row['raw_name_hex']).endswith(b' (deleted)')):
                raise Refusal('mapped inode/device/offset/permission differs from held descriptor')
            stop=min(end,row['end']);pieces.append({'map':dict(row),'start':cursor,'end':stop});cursor=stop
            if cursor==end: break
        if cursor!=end: raise Refusal('incomplete executable mapping coverage')
        covered.append({'program_header_index':segment['index'],'start':start,'end':end,'pieces':pieces})
    if not covered: raise Refusal('no executable mapping witness')
    return {'status':'SNAPSHOT_EXECUTABLE_MAPPING_GEOMETRY_ONLY','load_base':load_base,'segments':covered,
            'descriptor_identity':dict(descriptor_identity),'mapped_content_verified':False,
            'continuous_mapping_custody':False,'callback_origin_authenticated':False,
            'native_runtime_or_science_authority':False}


def vdso_region(rows, auxv):
    page=auxv[6];page_size(page)
    found=[row for row in rows if bytes.fromhex(row['raw_name_hex'])==b'[vdso]']
    if len(found)!=1: raise Refusal('one exact vdso mapping required')
    row=found[0]
    if (row['start']!=auxv[33] or row['permissions']!='r-xp' or row['inode']!=0
            or row['device_major']!=0 or row['device_minor']!=0 or row['offset']!=0
            or not 0<row['end']-row['start']<=MAX_KERNEL_BYTES):
        raise Refusal('auxv/kernel mapping identity or extent differs')
    return dict(row)


def vdso_witness(rows, auxv, first, second):
    region=vdso_region(rows,auxv);size=region['end']-region['start']
    if type(first) is not bytes or type(second) is not bytes or len(first)!=size or first!=second:
        raise Refusal('two exact stable bounded vdso snapshots required')
    elf=parse_elf(first,size)
    if elf['type']!=3: raise Refusal('kernel vDSO must be ET_DYN in this restricted scope')
    for segment in elf['loads']:
        if (segment['file_offset']!=segment['vaddr'] or segment['vaddr']+segment['memory_bytes']>size
                or segment['flags']&2):
            raise Refusal('unsupported kernel ELF mapping geometry')
    return {'status':'ADMINISTRATIVE_SELF_VDSO_SNAPSHOT_ONLY','region':region,'elf':elf,
            'memory_pin':{'bytes':size,'sha256':hashlib.sha256(first).hexdigest()},
            'cross_process_or_historical_kernel_identity':False,'complete_kernel_namespace_qualified':False,
            'target_kernel_objects_supported':False,'continuous_content_custody':False,
            'native_runtime_or_science_authority':False}


def dispatch(*args,**kwargs): raise Refusal('M snapshot source cannot launch target or grant native/science authority')
