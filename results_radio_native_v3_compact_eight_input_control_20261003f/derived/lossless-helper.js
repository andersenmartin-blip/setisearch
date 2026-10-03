'use strict';
function requireNodeWorkerAdmission(role,scope,bundlePath,bundleDigest){
 const actual=[process.argv0,...process.execArgv,...process.argv.slice(1)];
 require('node:child_process').execFileSync("/opt/codex/runtimes/codex-primary-runtime/dependencies/python/bin/python3.12",['-I','-S','-B','-c',"import hashlib,json,os,stat,sys\nfrom pathlib import Path\np=sys.argv[1]; wanted={'bytes': 149752, 'sha256': 'b1509d7ec03e3886ba9e34a9db16af98ad03b48d8b5dea8796ad43836e7d891d'}\nfd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)\ntry:\n before=os.fstat(fd)\n if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size!=wanted['bytes']:\n  raise ValueError('Exact pinned Node admission fixture required')\n raw=bytearray()\n while True:\n  block=os.read(fd,65536)\n  if not block:break\n  raw.extend(block)\n  if len(raw)>wanted['bytes']:raise ValueError('Node admission fixture exceeded pin')\n after=os.fstat(fd); named=os.stat(p,follow_symlinks=False)\n stable=lambda i:(i.st_dev,i.st_ino,i.st_size,i.st_mtime_ns,i.st_ctime_ns)\n if stable(before)!=stable(after) or stable(after)!=stable(named):raise ValueError('Node admission fixture changed')\nfinally:os.close(fd)\nif hashlib.sha256(raw).hexdigest()!=wanted['sha256']:raise ValueError('Node admission fixture source differs')\nm={'__name__':'frozen_node_admission','__file__':p}\nexec(compile(bytes(raw),p,'exec'),m)\nm['node_worker_entry'](sys.argv[2],sys.argv[3],sys.argv[4],json.loads(sys.argv[5]),json.loads(sys.argv[6]))\n",require('node:path').join(scope,'frozen-code',"scripts/radio_native_v3_compact_eight_case_resource_fixture.py"),role,bundlePath,bundleDigest,JSON.stringify(actual),JSON.stringify(process.env)],{env:{"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C"},maxBuffer:65536,stdio:['ignore','pipe','pipe']});
}
'use strict';
// OFFLINE engineering evidence only. No connector, SDK, Git, RNG, scientific
// case, telescope access, retry, or native reservation is used by this helper.
const fs = require('node:fs'), path = require('node:path'), cp = require('node:child_process'), crypto = require('node:crypto');
const SCHEMA = 'radio-native-v2-compact-eight-case-lossless-projection-v1';
const HASH = /^[a-f0-9]{64}$/;
const ensure = (ok, message) => { if (!ok) throw Error(message); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
function* textChunks(value) {
  ensure(typeof value === 'string', 'Exact string scalar required');
  for (let offset = 0; offset < value.length;) {
    let end = Math.min(value.length, offset + 32768);
    const last = value.charCodeAt(end - 1), next = value.charCodeAt(end);
    if (end < value.length && last >= 0xd800 && last <= 0xdbff && next >= 0xdc00 && next <= 0xdfff) end--;
    yield value.slice(offset, end); offset = end;
  }
}
function* quoted(chunks) {
  yield '"';
  for (const chunk of chunks) yield JSON.stringify(chunk).slice(1, -1);
  yield '"';
}
function* jsonChunks(value, virtualStrings = new WeakMap()) {
  if (value && typeof value === 'object' && virtualStrings.has(value)) {
    yield* quoted(virtualStrings.get(value)());
  } else if (typeof value === 'string') yield* quoted(textChunks(value));
  else if (Array.isArray(value)) {
    yield '['; for (let i = 0; i < value.length; i++) { if (i) yield ','; yield* jsonChunks(value[i], virtualStrings); } yield ']';
  } else if (value && typeof value === 'object') {
    yield '{'; const keys = Object.keys(value);
    for (let i = 0; i < keys.length; i++) { if (i) yield ','; yield* quoted(textChunks(keys[i])); yield ':'; yield* jsonChunks(value[keys[i]], virtualStrings); }
    yield '}';
  } else {
    const literal = JSON.stringify(value); ensure(typeof literal === 'string', 'JSON scalar required'); yield literal;
  }
}
function digest(chunks, newline = false) {
  const hash = crypto.createHash('sha256'); let bytes = 0;
  for (const chunk of chunks) { const b = Buffer.from(chunk, 'utf8'); bytes += b.length; hash.update(b); }
  if (newline) { bytes++; hash.update('\n'); }
  return { bytes, sha256: hash.digest('hex') };
}
function shaFile(filename) {
  const fd = fs.openSync(filename, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK), hash = crypto.createHash('sha256'), buffer = Buffer.alloc(65536); let bytes = 0;
  try { const before=fs.fstatSync(fd); ensure(before.isFile()&&before.nlink===1,'Sole-link regular hash input required'); while (true) { const n = fs.readSync(fd, buffer, 0, buffer.length, null); if (!n) break; hash.update(buffer.subarray(0, n)); bytes += n; } }
  finally { fs.closeSync(fd); }
  return { bytes, sha256: hash.digest('hex') };
}
function writeJsonExclusive(filename, value) {
  checkCaseMetadataWrite(filename,digest(jsonChunks(value),true).bytes);
  const fd = fs.openSync(filename, 'wx', 0o600);
  try { for (const chunk of jsonChunks(value)) fs.writeSync(fd, chunk); fs.writeSync(fd, '\n'); fs.fsyncSync(fd); }
  finally { fs.closeSync(fd); }
  const directory=fs.openSync(path.dirname(filename),fs.constants.O_RDONLY|fs.constants.O_DIRECTORY|fs.constants.O_NOFOLLOW);
  try{fs.fsyncSync(directory);}finally{fs.closeSync(directory);}
  checkCaseMetadataWrite(filename,0);
}

const CASE_CAPACITY_EXCLUDED=new Set(["caller-observation.json", "caller-result.json", "deterministic-source.bin", "lossless-project-observation.json", "lossless-verify-retained-observation.json", "preparation-observation.json", "public-evidence/caller-observation.json", "public-evidence/preparation-observation.json", "public-evidence/preparation-subreaper-receipt.json", "store/items/request-000001/part", "worker-admission.json"]);
function caseCapacityExcluded(relative){
 return CASE_CAPACITY_EXCLUDED.has(relative)||relative.startsWith('frozen-code/')||relative.startsWith('derived/')||
 /^(?:caller|lossless-project|lossless-verify-retained|command-(?:[0-9]|[12][0-9]|3[0-7]|tail))-admission\.json$/.test(relative)||
 /^command-observations\/command-(?:[0-9]|[12][0-9]|3[0-7]|tail)-observation\.json$/.test(relative)||
 /^(?:preparation|caller|lossless-project|lossless-verify-retained|command-(?:[0-9]|[12][0-9]|3[0-7]|tail))-supervisor\/subreaper-(?:measurements|receipt)\.json$/.test(relative);
}
function checkCaseMetadataWrite(filename,additionalBytes){
 const absolute=path.resolve(filename),match=absolute.match(/^(.*?\/cases\/case0[0-7])\/(.+)$/);
 if(!match||caseCapacityExcluded(match[2]))return;
 if(!Number.isSafeInteger(additionalBytes)||additionalBytes<0)throw Error('Bounded metadata write required');
 const root=match[1];if(fs.realpathSync(root)!==root)throw Error('Canonical case metadata root required');
 if(Number(fs.statfsSync(root).bsize)!==4096)throw Error('Frozen 4096-byte capacity filesystem required');
 let total=0;const visit=directory=>{for(const name of fs.readdirSync(directory)){
  const retained=path.join(directory,name),info=fs.lstatSync(retained);
  if(info.isDirectory())visit(retained);else{
   if(!info.isFile()||info.nlink!==1)throw Error('Sole-link case metadata required');
   if(!caseCapacityExcluded(path.relative(root,retained)))total+=Math.max(info.size,info.blocks*512);
  }
 }};visit(root);
 if(total+Math.ceil(additionalBytes/4096)*4096>1835008)
  throw Error('Fixed engineering other-metadata capacity exceeded before write');
}

function readJson(filename) {
  const fd=fs.openSync(filename,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);
  try { const before=fs.fstatSync(fd); ensure(before.isFile()&&before.nlink===1&&before.size<=192*1024*1024,'Bounded sole-link JSON file required');
    const result=JSON.parse(fs.readFileSync(fd,'utf8')),after=fs.fstatSync(fd);
    ensure(before.dev===after.dev&&before.ino===after.ino&&before.size===after.size&&before.mtimeMs===after.mtimeMs,'JSON file changed during parse'); return result;
  } finally { fs.closeSync(fd); }
}
function identityCheck(transcript, prepared) {
  ensure(same(Object.keys(transcript), ['schema', 'control_case_identity', 'qualified', 'seen', 'deliveries', 'read_receipts']), 'Exact fresh eight-case top-level property order required');
  const id = transcript.control_case_identity;
  ensure(id && typeof id.namespace === 'string' && id.namespace.length && Number.isInteger(id.case_ordinal) && id.case_ordinal >= 0 && id.case_ordinal < 8 &&
    typeof id.source_case_id === 'string' && id.source_case_id.length && HASH.test(id.engineering_case_binding_sha256) && HASH.test(id.source_sha256) &&
    id.native_case_binding_verified === false, 'Distinct engineering identity with native binding false required');
  ensure(same(id,prepared.control_case_identity),'Exact prepared engineering identity required');
  ensure(id.source_sha256 === prepared.source_sha256, 'Actual deterministic source must bind the fresh engineering identity');
  ensure(Array.isArray(transcript.qualified?.client?.records) && Array.isArray(transcript.read_receipts), 'Complete caller records and source read receipts required');
}
function uniqueMap(rows, key, message) { const result = new Map(); for (const row of rows) { ensure(!result.has(row[key]), message); result.set(row[key], row); } return result; }
function envelopeCheck(record, receipt) {
  ensure(same(Object.keys(record.raw_result), receipt.envelope_entries.map(row => row[0])), 'Exact original source envelope property order required');
  for (const [key, value] of receipt.envelope_entries) {
    if (key === 'output') ensure(value === null, 'Removed source output must use the exact null receipt descriptor');
    else ensure(same(record.raw_result[key], value), 'Exact retained source envelope metadata required: ' + key);
  }
  ensure(record.response_bytes === receipt.envelope_bytes && record.response_sha256 === receipt.envelope_sha256, 'Receipt must bind the complete source envelope');
}
function project({ fullPath, preparedPath, recipePath, projectionPath, recipeArguments }) {
  const started = Date.now(), originalPin = shaFile(fullPath), prepared = readJson(preparedPath), recipePin = shaFile(recipePath);
  let transcript = readJson(fullPath); // This is the only complete full-transcript parse. Parent must independently observe this process.
  if (global.gc) global.gc();
  identityCheck(transcript, prepared);
  ensure(Array.isArray(recipeArguments) && recipeArguments.length === 7 && recipeArguments.every(v => typeof v === 'string') &&
    recipeArguments[0] === prepared.scope && recipeArguments[1] === prepared.python && recipeArguments[3] === String(transcript.control_case_identity.case_ordinal) &&
    recipeArguments[2].length && recipeArguments[4].length, 'Exact original root/python/run-id/case-ordinal/archive-prefix recipe arguments required');
  const plans = uniqueMap(prepared.reads, 'ordinal', 'Repeated preparation read ordinal refused'),
    commands = uniqueMap(prepared.reads.map(row => ({ ...row, cmd: row.arguments.cmd })), 'cmd', 'Repeated original source reader command refused'),
    receipts = uniqueMap(transcript.read_receipts, 'ordinal', 'Repeated source receipt ordinal refused'), replacements = [];
  ensure(plans.size === 38 && receipts.size === 38, 'Exactly 38 frozen maximum source reads required');
  let sourceCount = 0, requestCount = 0;
  for (let index = 0; index < transcript.qualified.client.records.length; index++) {
    const record = transcript.qualified.client.records[index]; ensure(record.ordinal === index, 'Original complete caller ordinal sequence required');
    if (record.kind === 'actual_source_read') {
      const request = JSON.parse(record.request_json), plan = commands.get(request.arguments.cmd), receipt = plan && receipts.get(plan.ordinal);
      ensure(plan && receipt && request.tool === 'exec_command' && same(request.arguments, plan.arguments), 'Exact original source reader request required');
      ensure(receipt.path === plan.path && receipt.offset === plan.offset && receipt.bytes === plan.bytes && receipt.source_sha256 === plan.source_sha256 && receipt.output_sha256 === plan.output_sha256,
        'Source read descriptor must bind the frozen source range');
      envelopeCheck(record, receipt);
      const outputPin = digest(textChunks(record.raw_result.output)), responsePin = digest(textChunks(record.response_json)), rawPin = digest(jsonChunks(record.raw_result));
      ensure(outputPin.bytes === plan.bytes && outputPin.sha256 === plan.output_sha256 && responsePin.bytes === record.response_bytes && responsePin.sha256 === record.response_sha256 && same(responsePin, rawPin),
        'Complete original source output and ordered response bytes must match every retained pin before omission');
      record.raw_result.output = { $compact_eight_lossless: 'immutable_source_range', source_plan_ordinal: plan.ordinal };
      record.response_json = { $compact_eight_lossless: 'ordered_source_read_envelope', source_plan_ordinal: plan.ordinal };
      replacements.push({ record_ordinal: index, field: 'raw_result.output', source_plan_ordinal: plan.ordinal }, { record_ordinal: index, field: 'response_json', source_plan_ordinal: plan.ordinal }); sourceCount++;
    } else if (record.kind === 'actual_connector' && record.tool.endsWith('_create_tree')) {
      const requestPin = digest(textChunks(record.request_json)), view = prepared.request_view;
      ensure(requestPin.bytes === view.request_bytes && requestPin.sha256 === view.request_sha256 && record.request_bytes === requestPin.bytes && record.request_sha256 === requestPin.sha256,
        'Exact original large create_tree request pin required');
      record.request_json = { $compact_eight_lossless: 'immutable_create_tree_request_view' };
      replacements.push({ record_ordinal: index, field: 'request_json', source_request_view: true }); requestCount++;
    }
  }
  ensure(sourceCount === 38 && requestCount === 1 && replacements.length === 77, 'Precisely 77 large fields must be omitted; no other field removal permitted');
  if (global.gc) global.gc();
  const relative = path.relative(prepared.scope, prepared.request_view.path);
  ensure(relative && !path.isAbsolute(relative) && relative.split(path.sep).every(part => part !== '..'), 'Request source must remain inside the original preparation root');
  const projection = { schema: SCHEMA, fixture_only: true, original_full_transcript: { ...originalPin, original_scratch_path: path.resolve(fullPath) },
    regeneration: { recipe_file: path.basename(recipePath), recipe_sha256: recipePin.sha256, recipe_bytes: recipePin.bytes,
      recipe_arguments: recipeArguments, regenerated_relative_source_path: relative, prepared },
    large_field_replacements: replacements, transcript, execution_authorized: false, scientific_execution_authorized: false,
    native_case_reservations: 0, native_case_executions: 0, scientific_cases_run: 0, rng_draws: 0, telescope_reads: 0,
    actual_connector_calls: 0, actual_functions_sdk_calls: 0, network_fetches: 0, automatic_retry: false,
    limitations: ['Offline lossless evidence projection only; source readers and tail evidence belong to the separately measured caller.',
      'Projection does not establish native binding, live transport, publication custody, scientific execution, or eight-case resource qualification.'] };
  writeJsonExclusive(projectionPath, projection);
  const pin = shaFile(projectionPath); transcript = null; if (global.gc) global.gc();
  return { schema: SCHEMA + '-project-audit', status: 'PASSED', original_full_transcript: originalPin, projection: pin, omitted_fields: 77,
    complete_original_envelope_pins_checked_before_omission: true, elapsed_seconds: (Date.now() - started) / 1000 };
}
function* rangeChunks(fd, offset, bytes) {
  const buffer = Buffer.alloc(65536); let used = 0;
  while (used < bytes) {
    const n = fs.readSync(fd, buffer, 0, Math.min(buffer.length, bytes - used), offset + used); ensure(n > 0, 'Regenerated source range truncated');
    const part = buffer.subarray(0, n); ensure(part.every(v => v < 128), 'Exact immutable ASCII source range required');
    yield part.toString('ascii'); used += n;
  }
}
function verifyProjection({ projectionPath, recipePath, freshRoot, auditPath, python, retainedSourcePath, retainedPayloadPath }) {
  const started = Date.now(), projection = readJson(projectionPath), regeneration = projection.regeneration, prepared = regeneration.prepared,
    transcript = projection.transcript, expected = projection.original_full_transcript, recipePin = shaFile(recipePath), projectionPin = shaFile(projectionPath);
  ensure(projection.schema === SCHEMA && projection.fixture_only === true && projection.execution_authorized === false && projection.scientific_execution_authorized === false,
    'Pinned offline engineering projection required');
  identityCheck(transcript, prepared);
  ensure(recipePin.sha256 === regeneration.recipe_sha256 && recipePin.bytes === regeneration.recipe_bytes, 'Exact frozen published preparation recipe required');
  ensure(Array.isArray(regeneration.recipe_arguments) && regeneration.recipe_arguments.length === 7 && regeneration.recipe_arguments[0] === prepared.scope &&
    regeneration.recipe_arguments[1] === prepared.python && regeneration.recipe_arguments[3] === String(transcript.control_case_identity.case_ordinal), 'Exact retained original recipe identity arguments required');
  const relative = path.relative(prepared.scope, prepared.request_view.path);
  ensure(path.isAbsolute(prepared.scope) && path.isAbsolute(prepared.request_view.path) && relative && !path.isAbsolute(relative) &&
    relative.split(path.sep).every(part => part !== '..') && regeneration.regenerated_relative_source_path === relative,
    'Exact bounded original-to-regenerated source path mapping required');
  ensure(typeof python === 'string' && path.isAbsolute(python), 'Absolute independently pinned Python executable required');
  let data, actualPrepared, sourceFile, payloadFile, independentlyRegenerated;
  if (retainedSourcePath !== undefined) {
    ensure(path.isAbsolute(retainedSourcePath) && path.resolve(retainedSourcePath) === path.resolve(prepared.request_view.path), 'Exact original retained source path required');
    data = prepared.scope; actualPrepared = prepared; sourceFile = retainedSourcePath;
    payloadFile = retainedPayloadPath || path.join(data, 'deterministic-source.bin');
    ensure(path.isAbsolute(payloadFile) && path.resolve(payloadFile) === path.resolve(path.join(prepared.scope, 'deterministic-source.bin')), 'Exact original retained deterministic payload path required');
    independentlyRegenerated = false;
  } else {
    ensure(path.isAbsolute(freshRoot) && !fs.existsSync(freshRoot), 'Exclusive fresh absolute regeneration root required; no overwrite or retry');
    fs.mkdirSync(freshRoot, { mode: 0o700 }); data = path.join(freshRoot, 'regenerated-archive'); fs.mkdirSync(data, { mode: 0o700 });
    const args = [...regeneration.recipe_arguments]; args[0] = data;
    const regenerated = cp.spawnSync(python, ['-I', '-S', '-B', recipePath, ...args], { encoding: 'utf8', maxBuffer: 1048576, timeout: 120000,
      env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C' } });
    ensure(!regenerated.error && regenerated.status === 0 && regenerated.stdout === '' && regenerated.stderr === '', 'Exact offline deterministic preparation failed without retry: ' + String(regenerated.error || regenerated.stderr));
    actualPrepared = readJson(path.join(data, 'prepared.json')); sourceFile = path.join(data, regeneration.regenerated_relative_source_path);
    payloadFile = path.join(data, 'deterministic-source.bin'); independentlyRegenerated = true;
  }
  const sourcePin = shaFile(sourceFile), payloadPin = shaFile(payloadFile);
  ensure(sourcePin.bytes === prepared.request_view.source_bytes && sourcePin.sha256 === prepared.request_view.source_sha256 &&
    payloadPin.bytes === prepared.source_bytes && payloadPin.sha256 === prepared.source_sha256 &&
    actualPrepared.archive_bytes === prepared.archive_bytes && actualPrepared.archive_files === prepared.archive_files && same(actualPrepared.files, prepared.files), 'Exact regenerated source, archive layout, and file pins required');
  for (const field of ['source_bytes', 'source_sha256', 'offset', 'bytes', 'sha256', 'request_prefix', 'request_suffix', 'request_bytes', 'request_sha256'])
    ensure(same(actualPrepared.request_view[field], prepared.request_view[field]), 'Regenerated request view differs: ' + field);
  ensure(actualPrepared.reads.length === prepared.reads.length, 'Exact original read count required');
  for (let i = 0; i < prepared.reads.length; i++) for (const field of ['ordinal', 'tool', 'offset', 'bytes', 'source_sha256', 'output_sha256', 'response_reserved_bytes'])
    ensure(same(actualPrepared.reads[i][field], prepared.reads[i][field]), 'Regenerated source read content descriptor differs: ' + field);
  // Original paths, commands, wall times, envelopes, binding values, and property
  // order stay in the retained transcript. Only regenerated byte ranges replace
  // the 77 explicitly omitted strings. No restored large field is accumulated.
  const plans = uniqueMap(prepared.reads, 'ordinal', 'Repeated source plan refused'), receipts = uniqueMap(transcript.read_receipts, 'ordinal', 'Repeated source receipt refused'),
    virtual = new WeakMap(), seen = new Set(), fd = fs.openSync(sourceFile, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);
  let sourceFields = 0, envelopeFields = 0, requestFields = 0;
  try {
    ensure(plans.size === 38 && receipts.size === 38 && projection.large_field_replacements.length === 77, 'Exact complete 38-source/77-field projection required');
    for (const item of projection.large_field_replacements) {
      const key = item.record_ordinal + ':' + item.field; ensure(!seen.has(key), 'Duplicate large field replacement refused'); seen.add(key);
      const record = transcript.qualified.client.records[item.record_ordinal]; ensure(record && record.ordinal === item.record_ordinal, 'Original complete record ordinal required');
      if (item.field === 'raw_result.output') {
        const marker = record.raw_result?.output, plan = plans.get(item.source_plan_ordinal), receipt = plan && receipts.get(plan.ordinal);
        ensure(record.kind === 'actual_source_read' && marker && same(Object.keys(marker), ['$compact_eight_lossless', 'source_plan_ordinal']) && marker.$compact_eight_lossless === 'immutable_source_range' && marker.source_plan_ordinal === plan?.ordinal && receipt,
          'Exact removed source output descriptor required');
        const request = JSON.parse(record.request_json);
        ensure(request.tool === 'exec_command' && same(request.arguments, plan.arguments) && receipt.path === plan.path && receipt.offset === plan.offset && receipt.bytes === plan.bytes &&
          receipt.source_sha256 === plan.source_sha256 && receipt.output_sha256 === plan.output_sha256, 'Original source command and receipt metadata must remain unchanged');
        const pin = digest(rangeChunks(fd, plan.offset, plan.bytes)); ensure(pin.bytes === plan.bytes && pin.sha256 === plan.output_sha256, 'Exact regenerated source output pin differs');
        virtual.set(marker, () => rangeChunks(fd, plan.offset, plan.bytes)); sourceFields++;
      } else if (item.field === 'response_json') {
        const marker = record.response_json, plan = plans.get(item.source_plan_ordinal), receipt = plan && receipts.get(plan.ordinal);
        ensure(record.kind === 'actual_source_read' && marker && same(Object.keys(marker), ['$compact_eight_lossless', 'source_plan_ordinal']) && marker.$compact_eight_lossless === 'ordered_source_read_envelope' &&
          marker.source_plan_ordinal === plan?.ordinal && virtual.has(record.raw_result.output) && receipt, 'Exact ordered removed response descriptor required');
        envelopeCheck(record, receipt);
        const pin = digest(jsonChunks(record.raw_result, virtual));
        ensure(pin.bytes === record.response_bytes && pin.sha256 === record.response_sha256 && receipt.envelope_bytes === pin.bytes && receipt.envelope_sha256 === pin.sha256,
          'Exact reconstructed complete source envelope pin differs');
        virtual.set(marker, () => jsonChunks(record.raw_result, virtual)); envelopeFields++;
      } else if (item.field === 'request_json') {
        const marker = record.request_json, view = prepared.request_view;
        ensure(record.kind === 'actual_connector' && record.tool.endsWith('_create_tree') && marker && same(Object.keys(marker), ['$compact_eight_lossless']) && marker.$compact_eight_lossless === 'immutable_create_tree_request_view',
          'Exact removed create_tree request descriptor required');
        const chunks = function* () { yield* textChunks(view.request_prefix); yield* rangeChunks(fd, view.offset, view.bytes); yield* textChunks(view.request_suffix); }, pin = digest(chunks());
        ensure(pin.bytes === record.request_bytes && pin.sha256 === record.request_sha256 && pin.bytes === view.request_bytes && pin.sha256 === view.request_sha256,
          'Exact complete regenerated create_tree request pin differs');
        virtual.set(marker, chunks); requestFields++;
      } else throw Error('Unknown or extra large field replacement refused');
    }
    ensure(sourceFields === 38 && envelopeFields === 38 && requestFields === 1, 'Precisely all 77 original large string fields must be restored');
    const reconstructed = digest(jsonChunks(transcript, virtual), true);
    ensure(reconstructed.bytes === expected.bytes && reconstructed.sha256 === expected.sha256, 'Entire original caller transcript UTF-8 byte count and SHA differ after hash-only reconstruction');
    const audit = { schema: SCHEMA + '-reconstruction-audit', status: 'PASSED', control_case_identity: transcript.control_case_identity,
      projection: projectionPin, recipe: recipePin, reconstruction_helper: shaFile(__filename), original_full_transcript: expected,
      reconstructed_full_transcript: { ...reconstructed, hash_only_sink: true, full_duplicate_file_written: false }, request_source: { ...sourcePin, path: sourceFile },
      deterministic_source: { ...payloadPin, path: payloadFile }, independently_regenerated_for_this_proof: independentlyRegenerated,
      deterministic_recipe_reexecuted_for_this_proof: independentlyRegenerated,
      source_mode: independentlyRegenerated ? 'independently_regenerated_from_frozen_recipe' : 'existing_exact_pinned_fresh_generator_output',
      additional_full_source_copy_written: independentlyRegenerated, additional_full_transcript_copy_written: false,
      restored_source_output_fields: sourceFields, restored_complete_raw_response_json_fields: envelopeFields,
      restored_complete_create_tree_request_fields: requestFields, exact_original_metadata_and_property_order_preserved: true,
      complete_full_file_bytecount_and_sha256_match: true, no_accumulated_reconstructed_large_strings: true, no_reconstructed_full_buffer: true,
      data_reconstruction_only: true, new_case_executions: 0, actual_functions_sdk_calls: 0, actual_connector_calls: 0, network_fetches: 0,
      real_public_github_mutations: 0, native_case_reservations: 0, native_case_executions: 0, scientific_cases_run: 0, rng_draws: 0, telescope_reads: 0,
      automatic_retry: false, execution_authorized: false, scientific_execution_authorized: false, live_transport_qualified: false, elapsed_seconds: (Date.now() - started) / 1000 };
    writeJsonExclusive(auditPath, audit); return audit;
  } finally { fs.closeSync(fd); }
}
module.exports = { SCHEMA, project, verifyProjection, textChunks, quoted, jsonChunks, digest, shaFile, rangeChunks };
if (require.main === module) {
  try {
    const args = process.argv.slice(2); let result;
    ensure(args.length===4&&(args[0]==='--resource-project'||args[0]==='--resource-verify-retained'),'Exact admitted resource helper mode required');
    if (args[0] === '--resource-project' || args[0] === '--resource-verify-retained') {
      ensure(args.length===4,'Exact resource helper argument file and admission required');
      requireNodeWorkerAdmission(args[0]==='--resource-project'?'lossless-project':'lossless-verify-retained',path.dirname(args[1]),args[2],args[3]);
      const options=readJson(args[1]),identityPath=options.identityPath;
      ensure(typeof identityPath==='string'&&path.isAbsolute(identityPath),'Independent observer identity destination required');
      writeJsonExclusive(identityPath,{procfs_pid:Number(fs.readlinkSync('/proc/self')),namespace_pid:process.pid});
      result=args[0]==='--resource-project'?project(options):verifyProjection(options);
    } else if (args[0] === '--project') {
      ensure(args.length === 6, 'Usage: helper.js --project full.json prepared.json recipe.py projection.json recipe-arguments.json');
      result = project({ fullPath: args[1], preparedPath: args[2], recipePath: args[3], projectionPath: args[4], recipeArguments: readJson(args[5]) });
    } else if (args[0] === '--verify-projection') {
      ensure(args.length === 6, 'Usage: helper.js --verify-projection projection.json recipe.py fresh-absolute-root audit.json absolute-python');
      result = verifyProjection({ projectionPath: args[1], recipePath: args[2], freshRoot: args[3], auditPath: args[4], python: args[5] });
    } else if (args[0] === '--verify-retained-source') {
      ensure(args.length === 6 || args.length === 7, 'Usage: helper.js --verify-retained-source projection.json recipe.py original-absolute-source-wire audit.json absolute-python [original-absolute-deterministic-payload]');
      result = verifyProjection({ projectionPath: args[1], recipePath: args[2], retainedSourcePath: args[3], auditPath: args[4], python: args[5], retainedPayloadPath: args[6] });
    } else throw Error('Only --project, --verify-projection, and --verify-retained-source modes are permitted');
    process.stdout.write(JSON.stringify({ status: result.status, schema: result.schema, bytes: result.reconstructed_full_transcript?.bytes ?? result.original_full_transcript.bytes,
      sha256: result.reconstructed_full_transcript?.sha256 ?? result.original_full_transcript.sha256, elapsed_seconds: result.elapsed_seconds }) + '\n');
  } catch (error) { process.stderr.write(String(error) + '\n'); process.exitCode = 1; }
}
