"""Read-only preparation input; no target code execution or collector dispatch."""
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import struct

TARGET = '/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12'
EXPECTED_BYTES = 30894944
EXPECTED_SHA256 = 'fa67443527ed9647f760d807e2a38f26340757123e643c4639cf273ed15d5ea7'
OUT = Path(__file__).resolve().parent / 'python-elf-diagnostic.json'

def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)

def main():
    descriptors = []
    bindings = []
    try:
        parent = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        descriptors.append(parent)
        for part in PurePosixPath(TARGET).parts[1:-1]:
            fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
            descriptors.append(fd)
            held = os.fstat(fd)
            assert identity(held) == identity(os.stat(part, dir_fd=parent, follow_symlinks=False))
            bindings.append((parent, part, fd, identity(held)))
            parent = fd
        leaf = PurePosixPath(TARGET).name
        fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, dir_fd=parent)
        descriptors.append(fd)
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1
        assert stat.S_IMODE(before.st_mode) == 0o755 and before.st_size == EXPECTED_BYTES
        chunks = []
        count = 0
        while count < EXPECTED_BYTES:
            chunk = os.read(fd, min(65536, EXPECTED_BYTES-count))
            assert chunk
            count += len(chunk)
            chunks.append(chunk)
        raw = b''.join(chunks)
        assert hashlib.sha256(raw).hexdigest() == EXPECTED_SHA256
        assert identity(before) == identity(os.fstat(fd)) == identity(os.stat(leaf, dir_fd=parent, follow_symlinks=False))
        for directory, part, held_fd, old in bindings:
            assert identity(os.fstat(held_fd)) == old == identity(os.stat(part, dir_fd=directory, follow_symlinks=False))
    finally:
        for fd in reversed(descriptors):
            os.close(fd)
    header = struct.Struct('<16sHHIQQQIHHHHHH')
    values = header.unpack_from(raw)
    ident, typ, machine, version, entry, phoff, shoff, flags, ehsize, phentsize, phnum, *_ = values
    assert ident[:7] == b'\x7fELF\x02\x01\x01' and machine == 62
    assert ehsize == 64 and phentsize == 56 and 0 < phnum <= 1024
    assert phoff + phentsize*phnum <= len(raw)
    programs = []
    loads = []
    dynamics = []
    for index in range(phnum):
        kind, pflags, offset, vaddr, paddr, filesz, memsz, align = struct.unpack_from('<IIQQQQQQ', raw, phoff+56*index)
        assert offset+filesz <= len(raw) and vaddr+memsz <= (1<<64)-1
        row = dict(index=index,kind=kind,flags=pflags,offset=offset,vaddr=vaddr,paddr=paddr,filesz=filesz,memsz=memsz,align=align)
        programs.append(row)
        if kind == 1: loads.append(row)
        if kind == 2: dynamics.append(row)
    assert len(dynamics) == 1
    segment = dynamics[0]
    assert 0 < segment['filesz'] <= 65536 and segment['filesz'] % 16 == 0
    dynamic_raw = raw[segment['offset']:segment['offset']+segment['filesz']]
    tags = []
    for off in range(0,len(dynamic_raw),16):
        tag, value = struct.unpack_from('<qQ',dynamic_raw,off)
        tags.append(dict(tag=tag,value=value))
        if tag == 0:break
    addresses = [x['value'] for x in tags if x['tag']==5]
    sizes = [x['value'] for x in tags if x['tag']==10]
    assert len(addresses)==len(sizes)==1
    address, size = addresses[0],sizes[0]
    assert 0 < size <= len(raw) and address+size <= (1<<64)-1
    candidates = []
    overlaps = []
    for load in loads:
        backed_end = load['vaddr']+load['filesz']
        if load['vaddr'] <= address and address+size <= backed_end:
            candidates.append(dict(program_header_index=load['index'],file_offset=load['offset']+address-load['vaddr']))
        start, end = max(address,load['vaddr']), min(address+size,backed_end)
        if start < end:
            overlaps.append(dict(program_header_index=load['index'],vaddr_start=start,vaddr_end=end,
                                 file_start=load['offset']+start-load['vaddr'],file_end=load['offset']+end-load['vaddr']))
    regions = []
    for role, offset, region in (('elf_header',0,raw[:64]),
                                ('program_header_table',phoff,raw[phoff:phoff+56*phnum]),
                                ('dynamic_table',segment['offset'],dynamic_raw)):
        regions.append(dict(role=role,file_offset=offset,bytes=len(region),sha256=hashlib.sha256(region).hexdigest(),raw_base64=base64.b64encode(region).decode()))
    report = dict(schema='radio-static-python-elf-preread-diagnostic-v1',domain='inert-readonly-preparation',
        target_path=TARGET,externally_expected_bytes=EXPECTED_BYTES,externally_expected_sha256=EXPECTED_SHA256,
        observed_bytes=len(raw),observed_sha256=hashlib.sha256(raw).hexdigest(),explicit_file_read_bytes=count,
        held_named_identity_stable=True,retained_regions=regions,program_headers=programs,dynamic_tags=tags,
        dt_strtab_vaddr=address,dt_strsz=size,whole_table_declared_file_backed_candidates=candidates,
        requested_table_declared_load_intersections=overlaps,original_closed_failure_path_identified=False,
        target_executed=False,collector_or_supervisor_dispatched=False,native_package_imported=False,
        complete_elf_or_runtime_certificate_issued=False,new_live_reservation_allocated=False,
        limitations='Current bounded readonly input, not an original collector failure receipt. Full ELF bytes were hashed but only exact header/table regions are retained. No loader/page-map emulation, native code invocation, transitive closure or scientific admission.')
    out = (json.dumps(report,sort_keys=True,indent=2)+'\n').encode()
    assert len(out) <= 65536
    fd = os.open(OUT,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
    with os.fdopen(fd,'wb') as stream:
        stream.write(out);stream.flush();os.fsync(stream.fileno())
    print(json.dumps({'status':'STATIC_READONLY_INPUT_RETAINED','bytes_read':count,'program_headers':phnum,
          'dt_strtab_vaddr':address,'dt_strsz':size,'whole_table_candidates':candidates,'intersections':overlaps,
          'report_bytes':len(out),'report_sha256':hashlib.sha256(out).hexdigest()},sort_keys=True))

if __name__ == '__main__':
    main()
