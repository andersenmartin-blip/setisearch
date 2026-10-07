"""Pure P wire-v2 ACTIVITY/startup reducer; no observer or native authority."""
import hashlib
import struct

EVENT = struct.Struct('<4sHHIIQQQQQQIIQQQHH')
MAX_PACKET = 2148
HANDSHAKE, OPEN, PREINIT, CLOSE, VETO, ACTIVITY = range(1, 7)
CONSISTENT, ADD, DELETE = range(3)


class Refusal(ValueError): pass


def digest(raw): return hashlib.sha256(raw).hexdigest()


def decode(raw):
    if type(raw) is not bytes or not EVENT.size <= len(raw) <= MAX_PACKET:
        raise Refusal('complete bounded wire-v2 record required')
    fields = ('magic', 'version', 'kind', 'sequence', 'pid', 'generation',
              'namespace', 'load_base', 'device', 'inode', 'bytes', 'mode',
              'flags', 'mtime_ns', 'ctime_ns', 'monotonic_ns', 'name_len', 'path_len')
    event = dict(zip(fields, EVENT.unpack_from(raw)))
    if (event['magic'] != b'RLA1' or event['version'] != 2 or
            not 1 <= event['kind'] <= 6 or event['sequence'] >= 4096 or
            not event['pid'] or event['generation'] > 256 or
            event['namespace'] != 0 or not event['monotonic_ns'] or
            event['name_len'] >= 1024 or event['path_len'] >= 1024 or
            len(raw) != EVENT.size + event['name_len'] + event['path_len']):
        raise Refusal('exact P wire identity required')
    tail = raw[EVENT.size:]
    try:
        event['name'] = tail[:event['name_len']].decode()
        event['path'] = tail[event['name_len']:].decode()
    except UnicodeDecodeError as exc:
        raise Refusal('UTF-8 object names required') from exc
    if event['kind'] != OPEN:
        forbidden = ('load_base','device','inode','bytes','mode','mtime_ns','ctime_ns','name_len','path_len')
        if any(event[k] for k in forbidden) or event['name'] or event['path']:
            raise Refusal('non-open payload fields must be zero')
    elif event['flags'] != 0:
        raise Refusal('open flags must be zero')
    return event


class ActivityLedger:
    def __init__(self, pid):
        if type(pid) is not int or type(pid) is bool or not 0 < pid < 2**32:
            raise Refusal('exact process id required')
        self.pid = pid; self.sequence = 0; self.time = 0
        self.handshake = False; self.phase = 'new'; self.main = 0
        self.next_generation = 1; self.live = set(); self.batch = None
        self.batches = []; self.raw_records = []; self.failures = []
        self.poisoned = False

    def _refuse(self, message, raw):
        self.poisoned = True
        self.failures.append({'reason': message, 'raw_hex': raw.hex(),
                              'sha256': digest(raw), 'batch_retained': self.batch})
        raise Refusal(message)

    def consume(self, raw):
        if self.poisoned: raise Refusal('poisoned ledger cannot resume')
        try:
            event = decode(raw)
            if event['pid'] != self.pid or event['sequence'] != self.sequence or event['monotonic_ns'] <= self.time:
                raise Refusal('process/sequence/time order differs')
            record = {'raw_hex': raw.hex(), 'sha256': digest(raw), 'kind': event['kind'],
                      'sequence': event['sequence'], 'generation': event['generation'],
                      'retained': True}
            self.raw_records.append(record)
            kind, gen = event['kind'], event['generation']
            if kind == VETO: raise Refusal('producer veto retained')
            if kind == HANDSHAKE:
                if self.handshake or self.phase != 'new' or gen or event['flags'] != 2:
                    raise Refusal('one initial v2 handshake required')
                self.handshake = True; self.phase = 'startup'
            elif not self.handshake:
                raise Refusal('handshake required before activity')
            elif kind == ACTIVITY:
                flag = event['flags']
                if flag not in (CONSISTENT, ADD, DELETE): raise Refusal('unknown activity flag')
                if flag in (ADD, DELETE):
                    if self.batch is not None: raise Refusal('nested activity batch')
                    expected = 0 if flag == ADD and not self.main and self.next_generation == 1 else self.main
                    if gen != expected or (self.phase == 'running' and not gen):
                        raise Refusal('activity head generation differs')
                    self.batch = {'kind': 'add' if flag == ADD else 'delete', 'head': gen,
                                  'opened': [], 'closed': [], 'start_sequence': event['sequence']}
                else:
                    if self.batch is None: raise Refusal('CONSISTENT without batch')
                    expected = self.main or 0
                    if gen != expected: raise Refusal('CONSISTENT head generation differs')
                    if self.phase == 'running' and not (self.batch['opened'] or self.batch['closed']):
                        raise Refusal('empty runtime batch')
                    self.batch['consistent_sequence'] = event['sequence']
                    self.batches.append(self.batch); self.batch = None
            elif kind == OPEN:
                if self.batch is None or self.batch['kind'] != 'add': raise Refusal('open outside ADD batch')
                if gen != self.next_generation or gen in self.live: raise Refusal('generation order/reuse differs')
                if not event['path'].startswith('/'): raise Refusal('absolute descriptor path required')
                if event['name'] == '':
                    if self.main: raise Refusal('main replacement refused')
                    self.main = gen
                elif not event['name'].startswith('/'):
                    raise Refusal('absolute loader name required')
                self.live.add(gen); self.next_generation += 1; self.batch['opened'].append(gen)
            elif kind == CLOSE:
                if self.batch is None or self.batch['kind'] != 'delete': raise Refusal('close outside DELETE batch')
                if gen not in self.live: raise Refusal('unknown/double close')
                if gen == self.main: raise Refusal('main close/replacement unsupported')
                self.live.remove(gen); self.batch['closed'].append(gen)
            elif kind == PREINIT:
                if self.phase != 'startup' or self.batch is not None or not self.batches or not self.main or gen != self.main:
                    raise Refusal('preinit requires closed initial ADD and live main')
                if self.main not in self.live: raise Refusal('main must remain live')
                self.phase = 'running'
            self.sequence += 1; self.time = event['monotonic_ns']
            record['accepted_structural_only'] = True
            return record
        except Refusal as exc:
            self._refuse(str(exc), raw)

    def receipt(self):
        if self.poisoned or self.phase != 'running' or self.batch is not None:
            raise Refusal('complete unpoisoned startup and closed batches required')
        return {'schema':'radio-P-structural-activity-receipt-v1', 'status':'SOURCE_STRUCTURE_ONLY',
                'batches':len(self.batches), 'records':len(self.raw_records),
                'main_generation':self.main, 'live_generations':sorted(self.live),
                'collector_authentication':False, 'continuous_loader_file_coverage':False,
                'native_runtime_qualification':False, 'codec_science_authority':False,
                'terminal_qualification':False, 'dispatch_enabled':False}


def dispatch(*args, **kwargs):
    raise Refusal('structural activity source has no native or science dispatch authority')
