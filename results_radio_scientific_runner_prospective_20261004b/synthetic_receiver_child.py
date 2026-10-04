"""Fixed isolated child: complete maintained gates and 96 tiny synthetic rows.

There is no telescope loader, remote acquisition, PRNG or actual-domain branch.
The bootstrap authenticates scope and supervisor source before importing it.
"""
import hashlib
import json
import os
import stat
import sys
import time
import types


def read(path, count, sha):
    if (type(path) is not str or not path.startswith('/') or path != os.path.normpath(path)
            or not 0 < count <= 4*1024**2):
        raise ValueError('invalid bounded bootstrap path/pin')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for part in path.split('/')[1:-1]:
            following = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
            os.close(fd); fd = following
        source = os.open(path.split('/')[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
        try:
            before = os.fstat(source)
            if not stat.S_ISREG(before.st_mode) or before.st_size != count:
                raise ValueError('bootstrap file type/size differs')
            raw = bytearray()
            while len(raw) < count:
                block = os.read(source, min(65536, count-len(raw)))
                if not block:
                    raise ValueError('bootstrap truncated')
                raw.extend(block)
            if hashlib.sha256(raw).hexdigest() != sha:
                raise ValueError('bootstrap raw pin differs')
            return bytes(raw)
        finally:
            os.close(source)
    finally:
        os.close(fd)


def main():
    if len(sys.argv) != 4:
        raise ValueError('exact child argv required')
    scope_path, sha, size = sys.argv[1:]
    raw = read(scope_path, int(size), sha)
    candidate = json.loads(raw)
    selected = candidate['runner']
    source = read(selected['path'], selected['bytes'], selected['sha256'])
    runner = types.ModuleType('radio_receiver_runner_v2')
    runner.__file__ = selected['path']
    sys.modules[runner.__name__] = runner
    exec(compile(source, selected['path'], 'exec'), runner.__dict__)
    spec = runner.validate_scope(runner.parse(raw, {'bytes': int(size), 'sha256': sha}),
                                 candidate['claim_root'])
    modules = runner.load_modules(spec)
    packet, admission, _ = runner.admitted_fixture(spec, modules)
    adapter = modules['receiver_telescope_adapter']
    calls = []

    def loader(request):
        calls.append(request.label)
        if spec['fault'] == 'raise-first':
            sys.stderr.buffer.write(b'controlled-synthetic-root-cause\x00\xff\n')
            sys.stderr.buffer.flush()
            raise RuntimeError('deliberate synthetic loader failure')
        if spec['fault'] == 'hang-first':
            sys.stderr.write('synthetic loader entered\n'); sys.stderr.flush()
            time.sleep(120)
        return adapter.LoadedRows(request.receipt_raw, tuple(packet['rows'][request.label]))

    class FixtureClock:
        def __init__(self):
            self.value = admission.record()['validated_current_epoch_milliseconds']

        def __call__(self):
            value = self.value; self.value += 1
            return value

    cadence = adapter.qualify_synthetic_fixture(row_loader=loader,
        fixture_row_pins=packet['row_pins'], fixture_clock=FixtureClock(),
        **packet['metadata'])
    record = {
        'schema': 'radio-synthetic-receiver-child-result-v2',
        'dispatch_identity': spec['dispatch_identity'], 'packet_sha256': spec['packet']['sha256'],
        'receiver_adapter_sha256': spec['modules']['receiver_telescope_adapter']['sha256'],
        'receiver_result': json.loads(cadence.record_raw), 'loader_calls': calls,
        'normalized_row_bytes': sum(len(row) for rows in packet['rows'].values() for row in rows),
        'isolated_flags': {'isolated': sys.flags.isolated, 'no_site': sys.flags.no_site,
                           'dont_write_bytecode': sys.flags.dont_write_bytecode},
        'scientific_execution_authorized': False, 'telescope_values_opened': False}
    sys.stdout.buffer.write(runner.canonical(record))


if __name__ == '__main__':
    main()
