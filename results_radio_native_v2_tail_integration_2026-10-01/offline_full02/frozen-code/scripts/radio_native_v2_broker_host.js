// Actual connector boundary for the existing native-v2 broker operations.
// Load in functions.exec with its tools object, or require for offline tests.
// This component does not supply a functions-to-worker filesystem bridge.
const HOST_SCHEMA = 'radio-native-v2-tool-host-accounting-v1';
const REPOSITORY = 'andersenmartin-blip/setisearch';
const BRANCH = 'm43-support-qualification';
const BROKER_PROTOCOL = 'radio-native-v2-inline-broker-accounting-v2';
const PREFIX = 'results_radio_native_v2_engineering_20260930a/live01';
const MIB = 1024 * 1024;
const HOST_LIMITS = Object.freeze({ cases: 8, calls: 512, request_bytes: 384 * MIB,
  response_bytes: 512 * MIB, seconds: 4800, case_calls: 64,
  case_request_bytes: 48 * MIB, case_response_bytes: 64 * MIB, case_seconds: 600 });
// Local raw evidence is independent of the broker's remote stored-file cap,
// and of the visible request/reply accounting above. No local deletion credit.
const LOCAL_LIMITS = Object.freeze({ receipt_bytes: 1536 * MIB, case_receipt_bytes: 192 * MIB,
  git_spool_bytes: 320 * MIB, case_git_spool_bytes: 40 * MIB });
// These are complete visible tool-result envelope reservations, separate from
// the Python broker's reservations for its normalized protocol result.
const TOOL_RESERVATIONS = Object.freeze({ fetch: 8 * MIB, create_tree: 4 * MIB,
  create_commit: 256 * 1024, update_ref: 64 * 1024,
  git_fetch: MIB, git_cat_file_batch: 4 * MIB });

function utf8Bytes(value) {
  let length = 0;
  for (const ch of value) {
    const cp = ch.codePointAt(0);
    length += cp <= 0x7f ? 1 : cp <= 0x7ff ? 2 : cp <= 0xffff ? 3 : 4;
  }
  return length;
}
function sha256(value) {
  const constants = [0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,
    0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,
    0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,
    0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,
    0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,
    0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,
    0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,
    0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,
    0xbef9a3f7,0xc67178f2];
  const hash = [0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,
    0x1f83d9ab,0x5be0cd19];
  const block = new Uint8Array(64), words = new Int32Array(64);
  let position = 0, length = 0;
  const rotate = (n, amount) => n >>> amount | n << 32 - amount;
  function compress() {
    for (let i = 0; i < 16; i++) words[i] = block[4*i] << 24 | block[4*i+1] << 16 |
      block[4*i+2] << 8 | block[4*i+3];
    for (let i = 16; i < 64; i++) {
      const a = words[i-15], b = words[i-2];
      words[i] = (words[i-16] + (rotate(a,7)^rotate(a,18)^a>>>3) + words[i-7] +
        (rotate(b,17)^rotate(b,19)^b>>>10)) | 0;
    }
    let [a,b,c,d,e,f,g,h] = hash;
    for (let i = 0; i < 64; i++) {
      const first = (h + (rotate(e,6)^rotate(e,11)^rotate(e,25)) + (e&f^~e&g) + constants[i] + words[i]) | 0;
      const second = ((rotate(a,2)^rotate(a,13)^rotate(a,22)) + (a&b^a&c^b&c)) | 0;
      h=g;g=f;f=e;e=(d+first)|0;d=c;c=b;b=a;a=(first+second)|0;
    }
    [a,b,c,d,e,f,g,h].forEach((n,i) => { hash[i] = hash[i] + n | 0; });
  }
  function push(byte) {
    block[position++] = byte;
    if (position === 64) { compress(); position = 0; }
  }
  for (const ch of value) {
    let cp = ch.codePointAt(0);
    if (cp >= 0xd800 && cp <= 0xdfff) cp = 0xfffd;
    if (cp <= 0x7f) { push(cp); length++; }
    else if (cp <= 0x7ff) { push(0xc0 | cp >> 6); push(0x80 | cp & 63); length+=2; }
    else if (cp <= 0xffff) { push(0xe0 | cp >> 12); push(0x80 | cp >> 6 & 63); push(0x80 | cp & 63); length+=3; }
    else { push(0xf0 | cp >> 18); push(0x80 | cp >> 12 & 63); push(0x80 | cp >> 6 & 63); push(0x80 | cp & 63); length+=4; }
  }
  push(0x80);
  while (position !== 56) push(0);
  const high = Math.floor(length / 0x20000000), low = length * 8 >>> 0;
  for (const n of [high, low]) for (let shift = 24; shift >= 0; shift -= 8) push(n >>> shift & 255);
  return hash.map(n => (n>>>0).toString(16).padStart(8,'0')).join('');
}
function assert(ok, message) { if (!ok) throw new Error(message); }
function object(value) { return value && typeof value === 'object' && !Array.isArray(value); }
function keys(value, expected) {
  assert(object(value) && Object.keys(value).sort().join(',') === expected.sort().join(','), 'Exact operation fields required');
}
function gitSha(value) { assert(typeof value === 'string' && /^[0-9a-f]{40}$/.test(value), 'Immutable Git SHA required'); return value; }
function safePath(value) {
  assert(typeof value === 'string' && value.split('/').every(part => part && part !== '.' && part !== '..') &&
    /^[\x20-\x7e]+$/.test(value) && !/[\\]/.test(value), 'Safe immutable ASCII archive path required');
  return value;
}
function absolutePath(value) {
  assert(typeof value === 'string' && value.startsWith('/') && value !== '/' &&
    safePath(value.slice(1)), 'Exact canonical absolute local path required');
  return value;
}
function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (object(value)) return '{' + Object.keys(value).sort().map(key => JSON.stringify(key)+':'+canonical(value[key])).join(',') + '}';
  const result = JSON.stringify(value);
  assert(result !== undefined && (typeof value !== 'number' || Number.isFinite(value)), 'Finite canonical JSON required');
  return result;
}
function shellQuote(value) { return "'" + value.replace(/'/g,"'\\''") + "'"; }
function gitBatchBytes(files) {
  return Object.values(files).reduce((total,pin) => total + pin.bytes + utf8Bytes(pin.blob+' blob '+pin.bytes+'\n') + 1, 0);
}
function limitsWithin(values, hard) {
  keys(values, Object.keys(hard));
  for (const [key,value] of Object.entries(values))
    assert(Number.isSafeInteger(value) && value > 0 && value <= hard[key], 'Finite frozen host limits required');
}

/*
 * persistRaw(record) must durably save record.storage_json before returning
 * the exact six receipt fields below. That byte stream contains request_json
 * and untouched response_json, without a structuredContent projection.
 * response_json is JSON.stringify of the complete returned tool object, never
 * a projection of structuredContent. raw_result is that original object.
 *
 * groupedGitReadback({commit, paths, files, callGit, git_plan, spool_path,
 * deadline_ms}) must use callGit('git_fetch'), then
 * callGit('git_cat_file_batch'). Optional supplied execArgs must match the
 * generated git_plan exactly; arbitrary shell commands are never accepted.
 * It must preserve the raw --batch byte stream durably before projecting to
 * result={path:{sha,content}}. Return {result,commit,single_cat_file_batch:true,
 * raw_git_receipt:{path,bytes,sha256,durable:true}}. Full-sized readback uses
 * a local durable spool; sending its bytes through capped terminal stdout is
 * not qualified. The concrete spool/worker bridge remains an external pin.
 */
function createBrokerHost(options) {
  const { tools: connectorTools, persistRaw, groupedGitReadback } = options;
  assert(object(connectorTools) && typeof persistRaw === 'function' && typeof groupedGitReadback === 'function',
    'Actual tools, durable raw sink and grouped Git bridge required');
  const limits = Object.freeze({ ...options.limits || HOST_LIMITS });
  limitsWithin(limits, HOST_LIMITS);
  const reservations = Object.freeze({ ...options.responseReservations || TOOL_RESERVATIONS });
  limitsWithin(reservations, TOOL_RESERVATIONS);
  const localLimits = Object.freeze({ ...options.localLimits || LOCAL_LIMITS });
  limitsWithin(localLimits, LOCAL_LIMITS);
  const repoPath = absolutePath(options.repoPath), spoolRoot = absolutePath(options.spoolRoot);
  const timeoutMs = options.operationTimeoutMs === undefined ? 120000 : options.operationTimeoutMs;
  assert(Number.isSafeInteger(timeoutMs) && timeoutMs > 0 && timeoutMs <= 120000, 'Finite operation deadline required');
  const clock = options.clock || Date.now, setTimer = options.setTimer || setTimeout, clearTimer = options.clearTimer || clearTimeout;
  const started = clock(), records = [], completed = [];
  const counters = { calls:0, request_bytes:0, response_bytes:0, response_charged_bytes:0,
    unknown_response_bytes:0, unknown_response_count:0, tool_argument_bytes:0,
    receipt_bytes:0, receipt_charged_bytes:0, unknown_receipt_bytes:0,
    git_spool_bytes:0, git_spool_charged_bytes:0, unknown_git_spool_bytes:0 };
  let stopped = false, busy = false, freeze = null, caseStart = 0, caseBase = null, phase = {}, stopReason = null;
  const stop = error => { stopped = true; stopReason = String(error); return error; };
  const caseUsage = () => Object.fromEntries(Object.entries(counters).map(([key,value]) => [key,value-(caseBase ? caseBase[key] : 0)]));
  const usage = () => ({ schema:HOST_SCHEMA, ...counters, cases:completed.length,
    elapsed_seconds:(clock()-started)/1000, automatic_retry:false,
    visible_tool_objects_only:true, hidden_http_bytes_known:false });
  const timeLeft = () => Math.min(timeoutMs, limits.seconds*1000-(clock()-started),
    limits.case_seconds*1000-(clock()-caseStart));
  const check = () => {
    assert(!stopped, 'Host permanently stopped; no retry');
    assert(freeze !== null && timeLeft() > 0, 'Frozen host deadline exhausted');
    const perCase = caseUsage();
    assert(counters.calls <= limits.calls && perCase.calls <= limits.case_calls &&
      counters.request_bytes <= limits.request_bytes && perCase.request_bytes <= limits.case_request_bytes &&
      counters.response_charged_bytes <= limits.response_bytes &&
      perCase.response_charged_bytes <= limits.case_response_bytes &&
      counters.receipt_charged_bytes <= localLimits.receipt_bytes &&
      perCase.receipt_charged_bytes <= localLimits.case_receipt_bytes &&
      counters.git_spool_charged_bytes <= localLimits.git_spool_bytes &&
      perCase.git_spool_charged_bytes <= localLimits.case_git_spool_bytes,
      'Frozen actual-envelope or independent local evidence budget exhausted');
  };
  async function deadline(promise, milliseconds) {
    let timer;
    const timed = new Promise((resolve,reject) => { timer = setTimer(() => reject(stop(new Error('Actual host operation deadline exceeded; reply uncertain'))), milliseconds); });
    try { return await Promise.race([promise, timed]); } finally { clearTimer(timer); }
  }
  async function callTool(operation, args, isMutation = false) {
    check();
    const tool = operation.startsWith('git_') ? 'exec_command' : 'mcp__codex_apps__github_'+operation;
    assert(typeof connectorTools[tool] === 'function', 'Actual connector operation unavailable');
    const requestJson = JSON.stringify({ tool, arguments:args });
    assert(typeof requestJson === 'string', 'Serializable actual tool request required');
    const argumentJson = JSON.stringify(args), requestBytes = utf8Bytes(requestJson), reservation = reservations[operation];
    assert(Number.isSafeInteger(reservation), 'Frozen complete tool reply reservation required');
    // JSON.stringify(raw) contains no literal control bytes; enclosing that
    // already serialized JSON as a string needs at most twice its UTF-8 size.
    const receiptReservation = utf8Bytes(JSON.stringify({ request_json:requestJson, response_json:'' })) + 2*reservation;
    const perCase = caseUsage();
    assert(counters.calls < limits.calls && perCase.calls < limits.case_calls &&
      counters.request_bytes+requestBytes <= limits.request_bytes &&
      perCase.request_bytes+requestBytes <= limits.case_request_bytes &&
      counters.response_charged_bytes+reservation <= limits.response_bytes &&
      perCase.response_charged_bytes+reservation <= limits.case_response_bytes &&
      counters.receipt_charged_bytes+receiptReservation <= localLimits.receipt_bytes &&
      perCase.receipt_charged_bytes+receiptReservation <= localLimits.case_receipt_bytes,
      'Cannot reserve actual tool request and whole reply before dispatch');
    counters.calls++; counters.request_bytes+=requestBytes; counters.tool_argument_bytes+=utf8Bytes(argumentJson);
    counters.response_charged_bytes+=reservation; counters.unknown_response_bytes+=reservation; counters.unknown_response_count++;
    counters.receipt_charged_bytes+=receiptReservation; counters.unknown_receipt_bytes+=receiptReservation;
    const record = { ordinal:records.length, operation, tool, request_json:requestJson,
      request_bytes:requestBytes, request_sha256:sha256(requestJson),
      response_reserved_bytes:reservation, response_unknown:true, response_charged_bytes:reservation,
      local_receipt_reserved_bytes:receiptReservation, local_receipt_unknown:true,
      mutation_attempted:false, dispatch_started:false, automatic_retry:false };
    records.push(record);
    // Defer dispatch until deadline() has installed the timer. Recheck after
    // serialization/hash work so exhausted preparation cannot dispatch.
    const task = Promise.resolve().then(async () => {
      check(); record.dispatch_started = true; record.mutation_attempted = isMutation;
      let raw;
      try { raw = await connectorTools[tool](args); }
      catch (error) { record.error = String(error); throw stop(error); }
      // A late returned envelope is still charged and persisted. It cannot
      // reopen the host or start another operation after a deadline.
      const responseJson = JSON.stringify(raw);
      assert(typeof responseJson === 'string', 'Serializable complete raw tool object required');
      const responseBytes = utf8Bytes(responseJson), responseHash = sha256(responseJson);
      counters.response_bytes+=responseBytes; counters.response_charged_bytes+=responseBytes-reservation;
      counters.unknown_response_bytes-=reservation; counters.unknown_response_count--;
      Object.assign(record, { response_unknown:false, response_bytes:responseBytes,
        response_sha256:responseHash, response_charged_bytes:responseBytes });
      const storageJson = JSON.stringify({ request_json:requestJson, response_json:responseJson });
      const storageBytes = utf8Bytes(storageJson), storageHash = sha256(storageJson);
      // Returned bytes are known even if the subsequent durable sink fails.
      // Keep the conservative reservation charged until durability is proven.
      record.local_receipt_bytes = storageBytes; record.local_receipt_sha256 = storageHash;
      const excessStorage = Math.max(0,storageBytes-receiptReservation);
      counters.receipt_charged_bytes+=excessStorage; counters.unknown_receipt_bytes+=excessStorage;
      const localCase = caseUsage();
      assert(counters.receipt_charged_bytes <= localLimits.receipt_bytes &&
        localCase.receipt_charged_bytes <= localLimits.case_receipt_bytes,
        'Returned raw envelope cannot fit independent local durable receipt cap');
      const expected = { request_bytes:requestBytes, request_sha256:record.request_sha256,
        response_bytes:responseBytes, response_sha256:responseHash,
        stored_bytes:storageBytes, stored_sha256:storageHash };
      const saved = await persistRaw({ ...record, response_json:responseJson, storage_json:storageJson, raw_result:raw });
      keys(saved, Object.keys(expected));
      assert(Object.entries(expected).every(([key,value]) => saved[key] === value), 'Durable untouched tool receipt differs');
      counters.receipt_bytes+=storageBytes; counters.receipt_charged_bytes+=storageBytes-receiptReservation-excessStorage;
      counters.unknown_receipt_bytes-=receiptReservation+excessStorage;
      record.raw_receipt_durable = true; record.local_receipt_unknown = false;
      assert(storageBytes <= receiptReservation, 'Actual local raw receipt exceeded reservation');
      assert(responseBytes <= reservation, 'Actual whole tool reply exceeded reservation');
      check();
      // Parse only the persisted snapshot; never normalize the raw tool object.
      return JSON.parse(responseJson);
    });
    try { return await deadline(task, timeLeft()); } catch (error) { record.error = String(error); throw stop(error); }
  }
  function parsed(raw, operation) {
    assert(object(raw) && raw.isError !== true, 'Connector error envelope');
    const value = operation === 'fetch' ? JSON.parse(raw.structuredContent.content) : raw.structuredContent;
    assert(object(value), 'Structured connector response absent');
    return value;
  }
  function beginCase(freezeJson, expectedBundleSha256) {
    try {
    assert(!stopped && !busy && freeze === null, 'Host cannot start another case');
    assert(typeof freezeJson === 'string' && /^[\x20-\x7e]*$/.test(freezeJson) &&
      typeof expectedBundleSha256 === 'string' && /^[0-9a-f]{64}$/.test(expectedBundleSha256) &&
      sha256(freezeJson) === expectedBundleSha256, 'Independently pinned immutable broker freeze bytes required');
    const value = JSON.parse(freezeJson);
    assert(canonical(value) === freezeJson, 'Canonical unchanged broker freeze bytes required');
    keys(value,['schema','mode','broker_protocol','repository','branch','ordinal','prefix','parent','parent_tree',
      'limits','files','manifest_sha256','per_operation_response_reservations','single_inline_tree_request',
      'single_grouped_readback','force','automatic_retry','execution_restart_authorized','scientific_admission_authorized']);
    assert(value.schema === 'radio-native-v2-inline-terminal-archive-v1' && value.mode === 'ENGINEERING_ONLY' &&
      value.single_inline_tree_request === true && value.single_grouped_readback === true &&
      value.broker_protocol === BROKER_PROTOCOL && value.repository === REPOSITORY &&
      value.branch === BRANCH && value.force === false && value.automatic_retry === false &&
      value.execution_restart_authorized === false && value.scientific_admission_authorized === false,
      'Existing immutable engineering-only broker freeze required');
    limitsWithin(value.limits,{ calls:64, request_bytes:48*MIB, response_bytes:64*MIB, stored_bytes:36*MIB,
      files:28, seconds:600, peak_rss_bytes:512*MIB });
    assert(canonical(value.per_operation_response_reservations) === canonical({fetch:4*MIB,create_tree:MIB,
      create_commit:65536,update_ref:16384,fetch_files:48*MIB}), 'Exact existing broker reply reservations required');
    assert(Number.isSafeInteger(value.ordinal) && value.ordinal === completed.length && value.ordinal < limits.cases &&
      typeof value.prefix === 'string' && new RegExp('^'+PREFIX+'/case'+String(value.ordinal).padStart(2,'0')+'-[0-9a-f]{16}$').test(value.prefix),
      'Fresh ordered broker namespace required');
    gitSha(value.parent); gitSha(value.parent_tree);
    if (completed.length) assert(value.parent === completed[completed.length-1].commit, 'Expected previous published parent required');
    assert(object(value.files) && Object.keys(value.files).length >= 2 && Object.keys(value.files).length <= value.limits.files, 'Frozen archive inventory required');
    for (const [path,pin] of Object.entries(value.files)) {
      safePath(path); assert(path.startsWith(value.prefix+'/'), 'Archive outside immutable namespace');
      keys(pin,['bytes','sha256','blob']); gitSha(pin.blob);
      assert(Number.isSafeInteger(pin.bytes) && pin.bytes >= 0 && /^[0-9a-f]{64}$/.test(pin.sha256), 'Frozen exact file pins required');
    }
    const manifestPin = value.files[value.prefix+'/manifest.json'], headPin = value.files[value.prefix+'/HEAD'];
    assert(/^[0-9a-f]{64}$/.test(value.manifest_sha256) && manifestPin && manifestPin.sha256 === value.manifest_sha256 &&
      headPin && headPin.bytes === 65 && Object.values(value.files).reduce((sum,pin) => sum+pin.bytes,0) <= value.limits.stored_bytes,
      'Bounded manifest/HEAD/inventory freeze binding required');
    freeze = JSON.parse(JSON.stringify(value)); caseStart = clock(); caseBase = { ...counters };
    phase = { bundleSha256:expectedBundleSha256, head:null, parentChecked:false, tree:null, candidate:null, candidateChecked:false,
      lateParentChecked:false, updated:false, grouped:false, permittedTrees:new Set([freeze.parent_tree]) };
    check();
    } catch (error) { throw stop(error); }
  }
  async function invoke(operation, params) {
    assert(!busy && !stopped, 'Sequential host only; no retry'); busy = true;
    try {
      check(); let value;
      if (operation === 'fetch') {
        keys(params,['url']);
        const base = 'https://api.github.com/repos/'+REPOSITORY+'/git/';
        assert(typeof params.url === 'string' && params.url.startsWith(base), 'Approved engineering Git endpoint required');
        const suffix = params.url.slice(base.length), isHead = suffix === 'ref/heads/'+encodeURIComponent(BRANCH);
        assert(isHead || /^(commits|trees)\/[0-9a-f]{40}$/.test(suffix), 'Immutable engineering Git read only');
        if (suffix.startsWith('commits/')) assert(suffix.slice(8) === freeze.parent || suffix.slice(8) === phase.candidate,
          'Only frozen parent and this candidate commit may be read');
        if (suffix.startsWith('trees/')) assert(phase.permittedTrees.has(suffix.slice(6)),
          'Only pinned root trees and their observed immutable descendants may be read');
        value = parsed(await callTool(operation,params),operation);
        if (isHead) {
          assert(value.ref === 'refs/heads/'+BRANCH && value.object.type === 'commit', 'Exact branch ref identity/type differs');
          phase.head = gitSha(value.object.sha);
          assert(phase.head === (phase.updated ? phase.candidate : freeze.parent), 'Frozen expected parent/head conflict');
          if (phase.candidateChecked && !phase.updated) phase.lateParentChecked = true;
          if (phase.updated && phase.grouped) phase.finalHeadChecked = true;
        } else if (suffix.startsWith('commits/')) {
          assert(value.sha === suffix.slice(8), 'Immutable commit identity differs');
          if (value.sha === freeze.parent) {
            assert(value.tree.sha === freeze.parent_tree, 'Frozen parent tree differs'); phase.parentChecked = true;
          } else {
            assert(value.tree.sha === phase.tree && Array.isArray(value.parents) && value.parents.length === 1 &&
              value.parents[0].sha === freeze.parent, 'Candidate expected single parent/tree differs'); phase.candidateChecked = true;
          }
        } else if (suffix.startsWith('trees/')) {
          assert(value.sha === suffix.slice(6) && value.truncated === false && Array.isArray(value.tree), 'Exact complete immutable tree response required');
          for (const row of value.tree) if (row.type === 'tree') phase.permittedTrees.add(gitSha(row.sha));
        }
      } else if (operation === 'create_tree') {
        keys(params,['repository_full_name','base_tree_sha','tree_elements']);
        assert(params.repository_full_name === REPOSITORY && params.base_tree_sha === freeze.parent_tree &&
          phase.head === freeze.parent && phase.parentChecked && phase.tree === null && Array.isArray(params.tree_elements) &&
          params.tree_elements.length === Object.keys(freeze.files).length, 'One frozen inline tree operation required');
        const seen = new Set();
        for (const row of params.tree_elements) {
          keys(row,['path','mode','type','content']); const pin = freeze.files[row.path];
          assert(pin && !seen.has(row.path) && row.mode === '100644' && row.type === 'blob' &&
            typeof row.content === 'string' && /^[\x00-\x7f]*$/.test(row.content) &&
            utf8Bytes(row.content) === pin.bytes && sha256(row.content) === pin.sha256, 'Exact frozen inline file differs');
          seen.add(row.path);
        }
        value = parsed(await callTool(operation,params,true),operation); phase.tree = gitSha(value.sha); phase.permittedTrees.add(phase.tree);
      } else if (operation === 'create_commit') {
        keys(params,['repository_full_name','parent_sha','tree_sha','message']);
        assert(params.repository_full_name === REPOSITORY && params.parent_sha === freeze.parent && params.tree_sha === phase.tree &&
          phase.tree !== null && phase.candidate === null && typeof params.message === 'string' && utf8Bytes(params.message) <= 1024,
          'One bounded frozen-parent commit required');
        value = parsed(await callTool(operation,params,true),operation); phase.candidate = gitSha(value.sha);
      } else if (operation === 'update_ref') {
        keys(params,['repository_full_name','branch_name','sha','force']);
        assert(params.repository_full_name === REPOSITORY && params.branch_name === BRANCH && params.force === false &&
          params.sha === phase.candidate && phase.candidateChecked && phase.lateParentChecked && !phase.updated,
          'Confirmed expected-parent single nonforced update required');
        value = parsed(await callTool(operation,params,true),operation);
        assert(value.success === true, 'Unconfirmed branch update'); phase.updated = true;
      } else if (operation === 'fetch_files') {
        keys(params,['repository_full_name','ref','paths','encoding']);
        assert(params.repository_full_name === REPOSITORY && params.ref === phase.candidate && phase.updated && !phase.grouped &&
          params.encoding === 'base64' && Array.isArray(params.paths) &&
          JSON.stringify(params.paths) === JSON.stringify(Object.keys(freeze.files).sort()), 'Exact grouped immutable readback required');
        const spoolPath = spoolRoot+'/case'+String(freeze.ordinal).padStart(2,'0')+'-'+phase.bundleSha256+'.git-batch';
        const spoolReservation = gitBatchBytes(freeze.files), localCase = caseUsage();
        assert(counters.git_spool_charged_bytes+spoolReservation <= localLimits.git_spool_bytes &&
          localCase.git_spool_charged_bytes+spoolReservation <= localLimits.case_git_spool_bytes,
          'Cannot reserve complete raw Git batch in independent local spool cap');
        counters.git_spool_charged_bytes+=spoolReservation; counters.unknown_git_spool_bytes+=spoolReservation;
        const gitPlan = {
          git_fetch:{ cmd:"git --no-replace-objects -c core.hooksPath=/dev/null -c gc.auto=0 fetch --no-tags --no-write-fetch-head -- "+
            shellQuote('https://github.com/'+REPOSITORY+'.git')+' '+shellQuote(phase.candidate),
            workdir:repoPath,max_output_tokens:1024,yield_time_ms:1000 },
          git_cat_file_batch:{ cmd:"set -eu\numask 077\nset -C\ngit --no-replace-objects -c core.hooksPath=/dev/null cat-file --batch > "+
            shellQuote(spoolPath)+" <<'SETI_NATIVE_V2_BATCH_INPUT'\n"+
            params.paths.map(path => phase.candidate+':'+path).join('\n')+'\nSETI_NATIVE_V2_BATCH_INPUT',
            workdir:repoPath,max_output_tokens:1024,yield_time_ms:1000 }
        };
        let gitSequence = 0;
        const callGit = async (kind,args) => {
          check();
          assert(kind === ['git_fetch','git_cat_file_batch'][gitSequence++] && gitSequence <= 2,
            'Exactly one immutable Git fetch and one cat-file batch required');
          if (args !== undefined) assert(canonical(args) === canonical(gitPlan[kind]), 'Only exact host-generated immutable Git commands required');
          const raw = await callTool(kind,gitPlan[kind]);
          assert(raw.exit_code === 0 && raw.session_id === undefined && typeof raw.output === 'string', 'Grouped Git operation incomplete');
          return raw;
        };
        const grouped = await deadline(Promise.resolve().then(() => groupedGitReadback({ commit:phase.candidate,
          paths:params.paths.slice(), files:JSON.parse(JSON.stringify(freeze.files)), callGit,
          git_plan:JSON.parse(JSON.stringify(gitPlan)),spool_path:spoolPath,
          raw_git_reserved_bytes:spoolReservation,deadline_ms:timeLeft() })),timeLeft());
        assert(object(grouped) && grouped.commit === phase.candidate && grouped.single_cat_file_batch === true && gitSequence === 2,
          'Grouped immutable Git operation identity/count differs');
        const receipt = grouped.raw_git_receipt;
        keys(receipt,['path','bytes','sha256','durable']);
        assert(receipt.path === spoolPath &&
          Number.isSafeInteger(receipt.bytes) && receipt.bytes > 0 && /^[0-9a-f]{64}$/.test(receipt.sha256) && receipt.durable === true,
          'Untouched durable Git batch receipt required');
        counters.git_spool_bytes+=receipt.bytes; counters.git_spool_charged_bytes+=receipt.bytes-spoolReservation;
        counters.unknown_git_spool_bytes-=spoolReservation;
        assert(receipt.bytes === spoolReservation, 'Raw grouped Git batch byte length differs from exact frozen blob inventory');
        value = grouped.result; keys(value,Object.keys(freeze.files));
        for (const [path,pin] of Object.entries(freeze.files)) {
          const row = value[path]; keys(row,['sha','content']);
          assert(row.sha === pin.blob && typeof row.content === 'string' &&
            /^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(row.content), 'Grouped exact blob/base64 differs');
        }
        // Python Publisher independently decodes, hashes and compares every
        // returned byte against its frozen source and manifest pins.
        phase.grouped = true; phase.rawGitReceipt = JSON.parse(JSON.stringify(receipt));
      } else throw new Error('Unsupported existing broker operation');
      check(); return value;
    } catch (error) { throw stop(error); } finally { busy = false; }
  }
  function finishCase() {
    try {
      check(); assert(!busy && phase.updated && phase.grouped && phase.finalHeadChecked, 'Exact terminal publication/readback incomplete');
      const receipt = { ordinal:freeze.ordinal, parent:freeze.parent, commit:phase.candidate, tree:phase.tree,
        bundle_sha256:phase.bundleSha256,actual_tool_usage:caseUsage(), raw_git_receipt:phase.rawGitReceipt, automatic_retry:false };
      completed.push(receipt); freeze = null; return receipt;
    } catch (error) { throw stop(error); }
  }
  return { beginCase, invoke, finishCase, usage,
    state:() => ({ stopped,busy,stop_reason:stopReason,update_may_have_landed:records.some(row => row.operation === 'update_ref' && row.dispatch_started),
      candidate:phase.candidate || null, records:records.map(record => ({ ...record })) }),
    capabilityManifest:() => ({ schema:HOST_SCHEMA, broker_protocol:BROKER_PROTOCOL,
      status:'COMPONENT_ONLY_NOT_EXECUTABLE', repository:REPOSITORY, branch:BRANCH,
      operation_timeout_ms:timeoutMs, limits, local_evidence_limits:localLimits,complete_tool_response_reservations:reservations,
      actual_operation_count_includes_underlying_git_tools:true, raw_tool_envelope_before_parse:true,
      local_storage_accounting_includes_exact_envelope_payload_and_git_batch:true,
      host_rss_measured:false,full_size_integrated_storage_and_memory_qualified:false,
      grouped_git_operations:2, single_cat_file_batch:true, automatic_retry:false, force:false,
      unqualified_external_boundaries:['durable raw receipt sink','grouped Git spool/worker bridge',
        'functions-to-Python invoke bridge','host runtime and dependency closure'],
      rng_draws:0,telescope_reads:0,case_reservations:0,scientific_admission_authorized:false }) };
}

if (typeof module !== 'undefined') module.exports = { HOST_SCHEMA, HOST_LIMITS, LOCAL_LIMITS,TOOL_RESERVATIONS,
  REPOSITORY,BRANCH,BROKER_PROTOCOL,PREFIX,utf8Bytes,sha256,canonical,gitBatchBytes,createBrokerHost };
