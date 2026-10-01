#!/usr/bin/env python3
"""Prospective fresh eight-input OFFLINE resource control, with no authority.

Plan mode only inventories code and fixed identities. Execution additionally
requires an exact complete runtime freeze and a public immutable preread proof.
No historical caller data are inputs. Sources are independently derived from
eight fixed SHA256-counter domains. Connector/controller exchanges remain
explicit mocks; source readers and the legacy durable tail are real local
processes. This never qualifies native execution, HTTP custody or a host join.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import selectors
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import sysconfig
import time

REPO = Path(__file__).resolve().parents[1]
SELF = 'scripts/radio_native_v2_compact_eight_case_resource_fixture.py'
NAMESPACE = 'radio-native-v2-compact-eight-input-control-20261001a'
PREFIX = 'results_radio_native_v2_compact_eight_input_control_20261001a'
SCHEMA = 'radio-native-v2-compact-eight-input-resource-control-v1'
PLAN_SCHEMA = SCHEMA + '-prospective-plan'
PREREAD_SCHEMA = SCHEMA + '-public-preread'
EXECUTION_STATUS = 'BLOCKED_PREPARATION_REVIEW'
EXECUTION_BLOCKERS = (
    'Complete structural and actual expected runtime-freeze closure must be joined to the engineering runtime supplement and exact parent/child environments.',
    'Every source-generating worker must independently enforce the outer public-preread admission and materialized code/derived pins.',
    'An independent measurement harness must cover the material runner through final metadata fsync and process termination; the final authoritative disposition must follow all storage/time checks.',
    'Whole-scope timing and final shared storage reservations must include every preparation, observer, directory and finalization entry under original limits.',
    'Fresh prepared source and terminal identities must be explicitly audited against the frozen source domain, archive prefix and outer ordinal; host/native joins remain unqualified.',
)
MIB = 1024**2
LIMITS = {'case_calls': 64, 'run_calls': 512, 'case_request_bytes': 48*MIB,
    'run_request_bytes': 384*MIB, 'case_response_bytes': 64*MIB,
    'run_response_bytes': 512*MIB, 'case_seconds': 600, 'run_seconds': 4800,
    'rss_bytes': 512*MIB, 'case_storage_bytes': 192*MIB, 'run_storage_bytes': 1536*MIB}
AUTHORITY = {'execution_authorized': False, 'reservation_authorized': False,
    'scientific_execution_authorized': False, 'native_case_reservations': 0,
    'native_case_executions': 0, 'scientific_cases_run': 0, 'rng_draws': 0,
    'telescope_reads': 0, 'actual_functions_sdk_calls': 0, 'actual_connector_calls': 0,
    'network_fetches': 0, 'actual_git_processes': 0, 'real_public_github_mutations': 0,
    'automatic_retry': False, 'native_case_binding_verified': False,
    'host_ledger_join_complete': False, 'hidden_http_bytes_known': False}
CODE_FILES = (
    'scripts/radio_native_v2_qualified_courier_fixture.js',
    'scripts/radio_native_v2_tool_courier_client.js',
    'scripts/radio_native_v2_qualified_tool_courier.js',
    'scripts/radio_native_v2_broker_host.js', 'scripts/radio_native_v2_caller_tail.py',
    'scripts/radio_native_v2_local_transport.js', 'scripts/radio_native_v2_local_courier.js',
    'scripts/radio_native_v2_local_git.js', 'src/seti_repeater/__init__.py',
    'src/seti_repeater/empty_null_radio.py', 'src/seti_repeater/native_v2_transport_contract_radio.py',
    'scripts/radio_native_v2_compact_run_verifier.py', SELF,
    'scripts/radio_native_v2_worker_admission.py',
    'scripts/radio_native_v2_process_tree_supervisor.py',
    'tests/test_radio_native_v2_compact_eight_case_resource_fixture.py',
    'tests/test_radio_native_v2_worker_admission.py',
    'tests/test_radio_native_v2_process_tree_supervisor.py')
LOG_LIMIT = 65536
OBSERVATION_SAMPLE_LIMIT = 2048
CHILD_ENVIRONMENT = {'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'}
LOSSLESS_HELPER = "'use strict';\n// OFFLINE engineering evidence only. No connector, SDK, Git, RNG, scientific\n// case, telescope access, retry, or native reservation is used by this helper.\nconst fs = require('node:fs'), path = require('node:path'), cp = require('node:child_process'), crypto = require('node:crypto');\nconst SCHEMA = 'radio-native-v2-compact-eight-case-lossless-projection-v1';\nconst HASH = /^[a-f0-9]{64}$/;\nconst ensure = (ok, message) => { if (!ok) throw Error(message); };\nconst same = (a, b) => JSON.stringify(a) === JSON.stringify(b);\nfunction* textChunks(value) {\n  ensure(typeof value === 'string', 'Exact string scalar required');\n  for (let offset = 0; offset < value.length;) {\n    let end = Math.min(value.length, offset + 32768);\n    const last = value.charCodeAt(end - 1), next = value.charCodeAt(end);\n    if (end < value.length && last >= 0xd800 && last <= 0xdbff && next >= 0xdc00 && next <= 0xdfff) end--;\n    yield value.slice(offset, end); offset = end;\n  }\n}\nfunction* quoted(chunks) {\n  yield '\"';\n  for (const chunk of chunks) yield JSON.stringify(chunk).slice(1, -1);\n  yield '\"';\n}\nfunction* jsonChunks(value, virtualStrings = new WeakMap()) {\n  if (value && typeof value === 'object' && virtualStrings.has(value)) {\n    yield* quoted(virtualStrings.get(value)());\n  } else if (typeof value === 'string') yield* quoted(textChunks(value));\n  else if (Array.isArray(value)) {\n    yield '['; for (let i = 0; i < value.length; i++) { if (i) yield ','; yield* jsonChunks(value[i], virtualStrings); } yield ']';\n  } else if (value && typeof value === 'object') {\n    yield '{'; const keys = Object.keys(value);\n    for (let i = 0; i < keys.length; i++) { if (i) yield ','; yield* quoted(textChunks(keys[i])); yield ':'; yield* jsonChunks(value[keys[i]], virtualStrings); }\n    yield '}';\n  } else {\n    const literal = JSON.stringify(value); ensure(typeof literal === 'string', 'JSON scalar required'); yield literal;\n  }\n}\nfunction digest(chunks, newline = false) {\n  const hash = crypto.createHash('sha256'); let bytes = 0;\n  for (const chunk of chunks) { const b = Buffer.from(chunk, 'utf8'); bytes += b.length; hash.update(b); }\n  if (newline) { bytes++; hash.update('\\n'); }\n  return { bytes, sha256: hash.digest('hex') };\n}\nfunction shaFile(filename) {\n  const fd = fs.openSync(filename, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK), hash = crypto.createHash('sha256'), buffer = Buffer.alloc(65536); let bytes = 0;\n  try { const before=fs.fstatSync(fd); ensure(before.isFile()&&before.nlink===1,'Sole-link regular hash input required'); while (true) { const n = fs.readSync(fd, buffer, 0, buffer.length, null); if (!n) break; hash.update(buffer.subarray(0, n)); bytes += n; } }\n  finally { fs.closeSync(fd); }\n  return { bytes, sha256: hash.digest('hex') };\n}\nfunction writeJsonExclusive(filename, value) {\n  const fd = fs.openSync(filename, 'wx', 0o600);\n  try { for (const chunk of jsonChunks(value)) fs.writeSync(fd, chunk); fs.writeSync(fd, '\\n'); fs.fsyncSync(fd); }\n  finally { fs.closeSync(fd); }\n  const directory=fs.openSync(path.dirname(filename),fs.constants.O_RDONLY|fs.constants.O_DIRECTORY|fs.constants.O_NOFOLLOW);\n  try{fs.fsyncSync(directory);}finally{fs.closeSync(directory);}\n}\nfunction readJson(filename) {\n  const fd=fs.openSync(filename,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);\n  try { const before=fs.fstatSync(fd); ensure(before.isFile()&&before.nlink===1&&before.size<=192*1024*1024,'Bounded sole-link JSON file required');\n    const result=JSON.parse(fs.readFileSync(fd,'utf8')),after=fs.fstatSync(fd);\n    ensure(before.dev===after.dev&&before.ino===after.ino&&before.size===after.size&&before.mtimeMs===after.mtimeMs,'JSON file changed during parse'); return result;\n  } finally { fs.closeSync(fd); }\n}\nfunction identityCheck(transcript, prepared) {\n  ensure(same(Object.keys(transcript), ['schema', 'control_case_identity', 'qualified', 'seen', 'deliveries', 'read_receipts']), 'Exact fresh eight-case top-level property order required');\n  const id = transcript.control_case_identity;\n  ensure(id && typeof id.namespace === 'string' && id.namespace.length && Number.isInteger(id.case_ordinal) && id.case_ordinal >= 0 && id.case_ordinal < 8 &&\n    typeof id.source_case_id === 'string' && id.source_case_id.length && HASH.test(id.engineering_case_binding_sha256) && HASH.test(id.source_sha256) &&\n    id.native_case_binding_verified === false, 'Distinct engineering identity with native binding false required');\n  ensure(same(id,prepared.control_case_identity),'Exact prepared engineering identity required');\n  ensure(id.source_sha256 === prepared.source_sha256, 'Actual deterministic source must bind the fresh engineering identity');\n  ensure(Array.isArray(transcript.qualified?.client?.records) && Array.isArray(transcript.read_receipts), 'Complete caller records and source read receipts required');\n}\nfunction uniqueMap(rows, key, message) { const result = new Map(); for (const row of rows) { ensure(!result.has(row[key]), message); result.set(row[key], row); } return result; }\nfunction envelopeCheck(record, receipt) {\n  ensure(same(Object.keys(record.raw_result), receipt.envelope_entries.map(row => row[0])), 'Exact original source envelope property order required');\n  for (const [key, value] of receipt.envelope_entries) {\n    if (key === 'output') ensure(value === null, 'Removed source output must use the exact null receipt descriptor');\n    else ensure(same(record.raw_result[key], value), 'Exact retained source envelope metadata required: ' + key);\n  }\n  ensure(record.response_bytes === receipt.envelope_bytes && record.response_sha256 === receipt.envelope_sha256, 'Receipt must bind the complete source envelope');\n}\nfunction project({ fullPath, preparedPath, recipePath, projectionPath, recipeArguments }) {\n  const started = Date.now(), originalPin = shaFile(fullPath), prepared = readJson(preparedPath), recipePin = shaFile(recipePath);\n  let transcript = readJson(fullPath); // This is the only complete full-transcript parse. Parent must independently observe this process.\n  if (global.gc) global.gc();\n  identityCheck(transcript, prepared);\n  ensure(Array.isArray(recipeArguments) && recipeArguments.length === 5 && recipeArguments.every(v => typeof v === 'string') &&\n    recipeArguments[0] === prepared.scope && recipeArguments[1] === prepared.python && recipeArguments[3] === String(transcript.control_case_identity.case_ordinal) &&\n    recipeArguments[2].length && recipeArguments[4].length, 'Exact original root/python/run-id/case-ordinal/archive-prefix recipe arguments required');\n  const plans = uniqueMap(prepared.reads, 'ordinal', 'Repeated preparation read ordinal refused'),\n    commands = uniqueMap(prepared.reads.map(row => ({ ...row, cmd: row.arguments.cmd })), 'cmd', 'Repeated original source reader command refused'),\n    receipts = uniqueMap(transcript.read_receipts, 'ordinal', 'Repeated source receipt ordinal refused'), replacements = [];\n  ensure(plans.size === 38 && receipts.size === 38, 'Exactly 38 frozen maximum source reads required');\n  let sourceCount = 0, requestCount = 0;\n  for (let index = 0; index < transcript.qualified.client.records.length; index++) {\n    const record = transcript.qualified.client.records[index]; ensure(record.ordinal === index, 'Original complete caller ordinal sequence required');\n    if (record.kind === 'actual_source_read') {\n      const request = JSON.parse(record.request_json), plan = commands.get(request.arguments.cmd), receipt = plan && receipts.get(plan.ordinal);\n      ensure(plan && receipt && request.tool === 'exec_command' && same(request.arguments, plan.arguments), 'Exact original source reader request required');\n      ensure(receipt.path === plan.path && receipt.offset === plan.offset && receipt.bytes === plan.bytes && receipt.source_sha256 === plan.source_sha256 && receipt.output_sha256 === plan.output_sha256,\n        'Source read descriptor must bind the frozen source range');\n      envelopeCheck(record, receipt);\n      const outputPin = digest(textChunks(record.raw_result.output)), responsePin = digest(textChunks(record.response_json)), rawPin = digest(jsonChunks(record.raw_result));\n      ensure(outputPin.bytes === plan.bytes && outputPin.sha256 === plan.output_sha256 && responsePin.bytes === record.response_bytes && responsePin.sha256 === record.response_sha256 && same(responsePin, rawPin),\n        'Complete original source output and ordered response bytes must match every retained pin before omission');\n      record.raw_result.output = { $compact_eight_lossless: 'immutable_source_range', source_plan_ordinal: plan.ordinal };\n      record.response_json = { $compact_eight_lossless: 'ordered_source_read_envelope', source_plan_ordinal: plan.ordinal };\n      replacements.push({ record_ordinal: index, field: 'raw_result.output', source_plan_ordinal: plan.ordinal }, { record_ordinal: index, field: 'response_json', source_plan_ordinal: plan.ordinal }); sourceCount++;\n    } else if (record.kind === 'actual_connector' && record.tool.endsWith('_create_tree')) {\n      const requestPin = digest(textChunks(record.request_json)), view = prepared.request_view;\n      ensure(requestPin.bytes === view.request_bytes && requestPin.sha256 === view.request_sha256 && record.request_bytes === requestPin.bytes && record.request_sha256 === requestPin.sha256,\n        'Exact original large create_tree request pin required');\n      record.request_json = { $compact_eight_lossless: 'immutable_create_tree_request_view' };\n      replacements.push({ record_ordinal: index, field: 'request_json', source_request_view: true }); requestCount++;\n    }\n  }\n  ensure(sourceCount === 38 && requestCount === 1 && replacements.length === 77, 'Precisely 77 large fields must be omitted; no other field removal permitted');\n  if (global.gc) global.gc();\n  const relative = path.relative(prepared.scope, prepared.request_view.path);\n  ensure(relative && !path.isAbsolute(relative) && relative.split(path.sep).every(part => part !== '..'), 'Request source must remain inside the original preparation root');\n  const projection = { schema: SCHEMA, fixture_only: true, original_full_transcript: { ...originalPin, original_scratch_path: path.resolve(fullPath) },\n    regeneration: { recipe_file: path.basename(recipePath), recipe_sha256: recipePin.sha256, recipe_bytes: recipePin.bytes,\n      recipe_arguments: recipeArguments, regenerated_relative_source_path: relative, prepared },\n    large_field_replacements: replacements, transcript, execution_authorized: false, scientific_execution_authorized: false,\n    native_case_reservations: 0, native_case_executions: 0, scientific_cases_run: 0, rng_draws: 0, telescope_reads: 0,\n    actual_connector_calls: 0, actual_functions_sdk_calls: 0, network_fetches: 0, automatic_retry: false,\n    limitations: ['Offline lossless evidence projection only; source readers and tail evidence belong to the separately measured caller.',\n      'Projection does not establish native binding, live transport, publication custody, scientific execution, or eight-case resource qualification.'] };\n  writeJsonExclusive(projectionPath, projection);\n  const pin = shaFile(projectionPath); transcript = null; if (global.gc) global.gc();\n  return { schema: SCHEMA + '-project-audit', status: 'PASSED', original_full_transcript: originalPin, projection: pin, omitted_fields: 77,\n    complete_original_envelope_pins_checked_before_omission: true, elapsed_seconds: (Date.now() - started) / 1000 };\n}\nfunction* rangeChunks(fd, offset, bytes) {\n  const buffer = Buffer.alloc(65536); let used = 0;\n  while (used < bytes) {\n    const n = fs.readSync(fd, buffer, 0, Math.min(buffer.length, bytes - used), offset + used); ensure(n > 0, 'Regenerated source range truncated');\n    const part = buffer.subarray(0, n); ensure(part.every(v => v < 128), 'Exact immutable ASCII source range required');\n    yield part.toString('ascii'); used += n;\n  }\n}\nfunction verifyProjection({ projectionPath, recipePath, freshRoot, auditPath, python, retainedSourcePath, retainedPayloadPath }) {\n  const started = Date.now(), projection = readJson(projectionPath), regeneration = projection.regeneration, prepared = regeneration.prepared,\n    transcript = projection.transcript, expected = projection.original_full_transcript, recipePin = shaFile(recipePath), projectionPin = shaFile(projectionPath);\n  ensure(projection.schema === SCHEMA && projection.fixture_only === true && projection.execution_authorized === false && projection.scientific_execution_authorized === false,\n    'Pinned offline engineering projection required');\n  identityCheck(transcript, prepared);\n  ensure(recipePin.sha256 === regeneration.recipe_sha256 && recipePin.bytes === regeneration.recipe_bytes, 'Exact frozen published preparation recipe required');\n  ensure(Array.isArray(regeneration.recipe_arguments) && regeneration.recipe_arguments.length === 5 && regeneration.recipe_arguments[0] === prepared.scope &&\n    regeneration.recipe_arguments[1] === prepared.python && regeneration.recipe_arguments[3] === String(transcript.control_case_identity.case_ordinal), 'Exact retained original recipe identity arguments required');\n  const relative = path.relative(prepared.scope, prepared.request_view.path);\n  ensure(path.isAbsolute(prepared.scope) && path.isAbsolute(prepared.request_view.path) && relative && !path.isAbsolute(relative) &&\n    relative.split(path.sep).every(part => part !== '..') && regeneration.regenerated_relative_source_path === relative,\n    'Exact bounded original-to-regenerated source path mapping required');\n  ensure(typeof python === 'string' && path.isAbsolute(python), 'Absolute independently pinned Python executable required');\n  let data, actualPrepared, sourceFile, payloadFile, independentlyRegenerated;\n  if (retainedSourcePath !== undefined) {\n    ensure(path.isAbsolute(retainedSourcePath) && path.resolve(retainedSourcePath) === path.resolve(prepared.request_view.path), 'Exact original retained source path required');\n    data = prepared.scope; actualPrepared = prepared; sourceFile = retainedSourcePath;\n    payloadFile = retainedPayloadPath || path.join(data, 'deterministic-source.bin');\n    ensure(path.isAbsolute(payloadFile) && path.resolve(payloadFile) === path.resolve(path.join(prepared.scope, 'deterministic-source.bin')), 'Exact original retained deterministic payload path required');\n    independentlyRegenerated = false;\n  } else {\n    ensure(path.isAbsolute(freshRoot) && !fs.existsSync(freshRoot), 'Exclusive fresh absolute regeneration root required; no overwrite or retry');\n    fs.mkdirSync(freshRoot, { mode: 0o700 }); data = path.join(freshRoot, 'regenerated-archive'); fs.mkdirSync(data, { mode: 0o700 });\n    const args = [...regeneration.recipe_arguments]; args[0] = data;\n    const regenerated = cp.spawnSync(python, ['-I', '-S', '-B', recipePath, ...args], { encoding: 'utf8', maxBuffer: 1048576, timeout: 120000,\n      env: { PATH: '/usr/bin:/bin', LANG: 'C', LC_ALL: 'C' } });\n    ensure(!regenerated.error && regenerated.status === 0 && regenerated.stdout === '' && regenerated.stderr === '', 'Exact offline deterministic preparation failed without retry: ' + String(regenerated.error || regenerated.stderr));\n    actualPrepared = readJson(path.join(data, 'prepared.json')); sourceFile = path.join(data, regeneration.regenerated_relative_source_path);\n    payloadFile = path.join(data, 'deterministic-source.bin'); independentlyRegenerated = true;\n  }\n  const sourcePin = shaFile(sourceFile), payloadPin = shaFile(payloadFile);\n  ensure(sourcePin.bytes === prepared.request_view.source_bytes && sourcePin.sha256 === prepared.request_view.source_sha256 &&\n    payloadPin.bytes === prepared.source_bytes && payloadPin.sha256 === prepared.source_sha256 &&\n    actualPrepared.archive_bytes === prepared.archive_bytes && actualPrepared.archive_files === prepared.archive_files && same(actualPrepared.files, prepared.files), 'Exact regenerated source, archive layout, and file pins required');\n  for (const field of ['source_bytes', 'source_sha256', 'offset', 'bytes', 'sha256', 'request_prefix', 'request_suffix', 'request_bytes', 'request_sha256'])\n    ensure(same(actualPrepared.request_view[field], prepared.request_view[field]), 'Regenerated request view differs: ' + field);\n  ensure(actualPrepared.reads.length === prepared.reads.length, 'Exact original read count required');\n  for (let i = 0; i < prepared.reads.length; i++) for (const field of ['ordinal', 'tool', 'offset', 'bytes', 'source_sha256', 'output_sha256', 'response_reserved_bytes'])\n    ensure(same(actualPrepared.reads[i][field], prepared.reads[i][field]), 'Regenerated source read content descriptor differs: ' + field);\n  // Original paths, commands, wall times, envelopes, binding values, and property\n  // order stay in the retained transcript. Only regenerated byte ranges replace\n  // the 77 explicitly omitted strings. No restored large field is accumulated.\n  const plans = uniqueMap(prepared.reads, 'ordinal', 'Repeated source plan refused'), receipts = uniqueMap(transcript.read_receipts, 'ordinal', 'Repeated source receipt refused'),\n    virtual = new WeakMap(), seen = new Set(), fd = fs.openSync(sourceFile, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW | fs.constants.O_NONBLOCK);\n  let sourceFields = 0, envelopeFields = 0, requestFields = 0;\n  try {\n    ensure(plans.size === 38 && receipts.size === 38 && projection.large_field_replacements.length === 77, 'Exact complete 38-source/77-field projection required');\n    for (const item of projection.large_field_replacements) {\n      const key = item.record_ordinal + ':' + item.field; ensure(!seen.has(key), 'Duplicate large field replacement refused'); seen.add(key);\n      const record = transcript.qualified.client.records[item.record_ordinal]; ensure(record && record.ordinal === item.record_ordinal, 'Original complete record ordinal required');\n      if (item.field === 'raw_result.output') {\n        const marker = record.raw_result?.output, plan = plans.get(item.source_plan_ordinal), receipt = plan && receipts.get(plan.ordinal);\n        ensure(record.kind === 'actual_source_read' && marker && same(Object.keys(marker), ['$compact_eight_lossless', 'source_plan_ordinal']) && marker.$compact_eight_lossless === 'immutable_source_range' && marker.source_plan_ordinal === plan?.ordinal && receipt,\n          'Exact removed source output descriptor required');\n        const request = JSON.parse(record.request_json);\n        ensure(request.tool === 'exec_command' && same(request.arguments, plan.arguments) && receipt.path === plan.path && receipt.offset === plan.offset && receipt.bytes === plan.bytes &&\n          receipt.source_sha256 === plan.source_sha256 && receipt.output_sha256 === plan.output_sha256, 'Original source command and receipt metadata must remain unchanged');\n        const pin = digest(rangeChunks(fd, plan.offset, plan.bytes)); ensure(pin.bytes === plan.bytes && pin.sha256 === plan.output_sha256, 'Exact regenerated source output pin differs');\n        virtual.set(marker, () => rangeChunks(fd, plan.offset, plan.bytes)); sourceFields++;\n      } else if (item.field === 'response_json') {\n        const marker = record.response_json, plan = plans.get(item.source_plan_ordinal), receipt = plan && receipts.get(plan.ordinal);\n        ensure(record.kind === 'actual_source_read' && marker && same(Object.keys(marker), ['$compact_eight_lossless', 'source_plan_ordinal']) && marker.$compact_eight_lossless === 'ordered_source_read_envelope' &&\n          marker.source_plan_ordinal === plan?.ordinal && virtual.has(record.raw_result.output) && receipt, 'Exact ordered removed response descriptor required');\n        envelopeCheck(record, receipt);\n        const pin = digest(jsonChunks(record.raw_result, virtual));\n        ensure(pin.bytes === record.response_bytes && pin.sha256 === record.response_sha256 && receipt.envelope_bytes === pin.bytes && receipt.envelope_sha256 === pin.sha256,\n          'Exact reconstructed complete source envelope pin differs');\n        virtual.set(marker, () => jsonChunks(record.raw_result, virtual)); envelopeFields++;\n      } else if (item.field === 'request_json') {\n        const marker = record.request_json, view = prepared.request_view;\n        ensure(record.kind === 'actual_connector' && record.tool.endsWith('_create_tree') && marker && same(Object.keys(marker), ['$compact_eight_lossless']) && marker.$compact_eight_lossless === 'immutable_create_tree_request_view',\n          'Exact removed create_tree request descriptor required');\n        const chunks = function* () { yield* textChunks(view.request_prefix); yield* rangeChunks(fd, view.offset, view.bytes); yield* textChunks(view.request_suffix); }, pin = digest(chunks());\n        ensure(pin.bytes === record.request_bytes && pin.sha256 === record.request_sha256 && pin.bytes === view.request_bytes && pin.sha256 === view.request_sha256,\n          'Exact complete regenerated create_tree request pin differs');\n        virtual.set(marker, chunks); requestFields++;\n      } else throw Error('Unknown or extra large field replacement refused');\n    }\n    ensure(sourceFields === 38 && envelopeFields === 38 && requestFields === 1, 'Precisely all 77 original large string fields must be restored');\n    const reconstructed = digest(jsonChunks(transcript, virtual), true);\n    ensure(reconstructed.bytes === expected.bytes && reconstructed.sha256 === expected.sha256, 'Entire original caller transcript UTF-8 byte count and SHA differ after hash-only reconstruction');\n    const audit = { schema: SCHEMA + '-reconstruction-audit', status: 'PASSED', control_case_identity: transcript.control_case_identity,\n      projection: projectionPin, recipe: recipePin, reconstruction_helper: shaFile(__filename), original_full_transcript: expected,\n      reconstructed_full_transcript: { ...reconstructed, hash_only_sink: true, full_duplicate_file_written: false }, request_source: { ...sourcePin, path: sourceFile },\n      deterministic_source: { ...payloadPin, path: payloadFile }, independently_regenerated_for_this_proof: independentlyRegenerated,\n      deterministic_recipe_reexecuted_for_this_proof: independentlyRegenerated,\n      source_mode: independentlyRegenerated ? 'independently_regenerated_from_frozen_recipe' : 'existing_exact_pinned_fresh_generator_output',\n      additional_full_source_copy_written: independentlyRegenerated, additional_full_transcript_copy_written: false,\n      restored_source_output_fields: sourceFields, restored_complete_raw_response_json_fields: envelopeFields,\n      restored_complete_create_tree_request_fields: requestFields, exact_original_metadata_and_property_order_preserved: true,\n      complete_full_file_bytecount_and_sha256_match: true, no_accumulated_reconstructed_large_strings: true, no_reconstructed_full_buffer: true,\n      data_reconstruction_only: true, new_case_executions: 0, actual_functions_sdk_calls: 0, actual_connector_calls: 0, network_fetches: 0,\n      real_public_github_mutations: 0, native_case_reservations: 0, native_case_executions: 0, scientific_cases_run: 0, rng_draws: 0, telescope_reads: 0,\n      automatic_retry: false, execution_authorized: false, scientific_execution_authorized: false, live_transport_qualified: false, elapsed_seconds: (Date.now() - started) / 1000 };\n    writeJsonExclusive(auditPath, audit); return audit;\n  } finally { fs.closeSync(fd); }\n}\nmodule.exports = { SCHEMA, project, verifyProjection, textChunks, quoted, jsonChunks, digest, shaFile, rangeChunks };\nif (require.main === module) {\n  try {\n    const args = process.argv.slice(2); let result;\n    if (args[0] === '--resource-project' || args[0] === '--resource-verify-retained') {\n      ensure(args.length===2,'Exact resource helper argument file required');\n      const options=readJson(args[1]),identityPath=options.identityPath;\n      ensure(typeof identityPath==='string'&&path.isAbsolute(identityPath),'Independent observer identity destination required');\n      writeJsonExclusive(identityPath,{procfs_pid:Number(fs.readlinkSync('/proc/self')),namespace_pid:process.pid});\n      result=args[0]==='--resource-project'?project(options):verifyProjection(options);\n    } else if (args[0] === '--project') {\n      ensure(args.length === 6, 'Usage: helper.js --project full.json prepared.json recipe.py projection.json recipe-arguments.json');\n      result = project({ fullPath: args[1], preparedPath: args[2], recipePath: args[3], projectionPath: args[4], recipeArguments: readJson(args[5]) });\n    } else if (args[0] === '--verify-projection') {\n      ensure(args.length === 6, 'Usage: helper.js --verify-projection projection.json recipe.py fresh-absolute-root audit.json absolute-python');\n      result = verifyProjection({ projectionPath: args[1], recipePath: args[2], freshRoot: args[3], auditPath: args[4], python: args[5] });\n    } else if (args[0] === '--verify-retained-source') {\n      ensure(args.length === 6 || args.length === 7, 'Usage: helper.js --verify-retained-source projection.json recipe.py original-absolute-source-wire audit.json absolute-python [original-absolute-deterministic-payload]');\n      result = verifyProjection({ projectionPath: args[1], recipePath: args[2], retainedSourcePath: args[3], auditPath: args[4], python: args[5], retainedPayloadPath: args[6] });\n    } else throw Error('Only --project, --verify-projection, and --verify-retained-source modes are permitted');\n    process.stdout.write(JSON.stringify({ status: result.status, schema: result.schema, bytes: result.reconstructed_full_transcript?.bytes ?? result.original_full_transcript.bytes,\n      sha256: result.reconstructed_full_transcript?.sha256 ?? result.original_full_transcript.sha256, elapsed_seconds: result.elapsed_seconds }) + '\\n');\n  } catch (error) { process.stderr.write(String(error) + '\\n'); process.exitCode = 1; }\n}\n"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def pin(path):
    digest = hashlib.sha256(); count = 0
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1:
            raise ValueError('Sole-link regular pinned file required')
        with os.fdopen(os.dup(fd),'rb') as stream:
            for raw in iter(lambda: stream.read(65536), b''):
                count += len(raw); digest.update(raw)
        after = os.fstat(fd)
        if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise ValueError('Pinned file changed during independent hash')
    finally: os.close(fd)
    return {'bytes': count, 'sha256': digest.hexdigest()}


def write(path, value):
    raw = value if isinstance(value, bytes) else canonical(value) + b'\n'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400)
    try:
        view = memoryview(raw)
        while view:
            amount = os.write(fd, view)
            if amount <= 0: raise OSError('Incomplete exclusive evidence write')
            view = view[amount:]
        os.fsync(fd)
        written_identity = os.fstat(fd)
    finally: os.close(fd)
    directory = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(directory)
    finally: os.close(directory)
    if pin(path) != {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}:
        raise ValueError('Independent durable evidence readback differs')
    reopened = os.stat(path,follow_symlinks=False)
    if (reopened.st_dev,reopened.st_ino)!=(written_identity.st_dev,written_identity.st_ino):
        raise ValueError('Durable evidence file identity replaced')


def small_json(path, limit=2*MIB):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
            raise ValueError('Bounded sole-link regular JSON evidence required')
        with os.fdopen(os.dup(fd), 'rb') as stream: raw = stream.read(limit + 1)
        if len(raw) != info.st_size: raise ValueError('JSON evidence changed during read')
        after = os.fstat(fd)
        if (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
            raise ValueError('JSON evidence inode changed during read')
        return json.loads(raw)
    finally: os.close(fd)


def source_domain(ordinal):
    if type(ordinal) is not int or not 0 <= ordinal < 8:
        raise ValueError('Exact fresh outer ordinal0..7 required')
    return b'seti-compact-eight-input-sha256-counter-v1\0' + NAMESPACE.encode() + b'\0' + ordinal.to_bytes(8, 'big')


def replace_once(source, before, after):
    if source.count(before) != 1:
        raise ValueError('Pinned code template drift: ' + before[:100])
    return source.replace(before, after, 1)


def source_worker_guard(repo=REPO):
    """Pin and execute source bytes directly; never load an unchecked pyc."""
    pins = {name: pin(Path(repo)/name) for name in
        ('scripts/radio_native_v2_worker_admission.py', SELF)}
    return '''
import stat
if len(sys.argv)!=8:
 raise ValueError('Exact source worker arguments and retained admission digest required')
if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode):
 raise ValueError('Actual isolated no-site no-bytecode interpreter required')
root=Path(sys.argv[1]); python=sys.argv[2]; namespace=sys.argv[3]; ordinal=int(sys.argv[4]); prefix=sys.argv[5]
def frozen_module(relative):
 path=root/'frozen-code'/relative
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd)
  if (not stat.S_ISREG(before.st_mode) or before.st_nlink!=1
      or before.st_size!=IMPLEMENTATION_PINS[relative]['bytes']):
   raise ValueError('Sole-link regular admission implementation required')
  raw=bytearray()
  while True:
   block=os.read(fd,65536)
   if not block:break
   raw.extend(block)
   if len(raw)>IMPLEMENTATION_PINS[relative]['bytes']:
    raise ValueError('Admission implementation exceeded frozen byte count')
  after=os.fstat(fd); named=path.stat(follow_symlinks=False)
  identity=lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
  if identity(before)!=identity(after) or identity(after)!=identity(named):
   raise ValueError('Admission implementation changed during read')
 finally:os.close(fd)
 if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=IMPLEMENTATION_PINS[relative]:
  raise ValueError('Pinned admission implementation differs')
 module={'__name__':'frozen_source_guard','__file__':str(path)}
 exec(compile(bytes(raw),str(path),'exec'),module)
 return module
IMPLEMENTATION_PINS='''+repr(pins)+'''
admission=frozen_module('scripts/radio_native_v2_worker_admission.py')
admission['validate_worker_admission'](Path(sys.argv[6]),role='prepare',ordinal=ordinal,
 argv=list(sys.orig_argv),
 environment=dict(os.environ),expected_bundle_sha256=sys.argv[7])
frozen_module('''+repr(SELF)+''')['require_execution_ready']()
'''


def templates(source, repo=REPO):
    """Derive fresh code from a pinned code template, never retained old data."""
    match = re.search(r'const PREPARE=String\.raw`(.*?)`;', source, re.S)
    if not match: raise ValueError('Pinned deterministic preparation template absent')
    prepare = match.group(1)
    prepare = replace_once(prepare, 'root=Path(sys.argv[1]); python=sys.argv[2]',
        source_worker_guard(repo)+
        'assert namespace=='+repr(NAMESPACE)+' and 0<=ordinal<8 and prefix=='+repr(PREFIX)+'+f"/case{ordinal:02d}-fixed"\n'
        'case_id=namespace+f"/case{ordinal:02d}"\n'
        'with (root/"preparation-identity.json").open("x") as identity:\n'
        ' json.dump({"procfs_pid":int(os.readlink("/proc/self")),"namespace_pid":os.getpid()},identity); identity.flush(); os.fsync(identity.fileno())')
    prepare = replace_once(prepare, "source_bytes=26*1024*1024;domain=b'seti-local-transport-sha256-counter-v1\\0'+(0).to_bytes(8,'big')",
        "source_bytes=26*1024*1024;domain=b'seti-compact-eight-input-sha256-counter-v1\\0'+namespace.encode()+b'\\0'+ordinal.to_bytes(8,'big')")
    prepare = replace_once(prepare, "prefix='results_radio_native_v2_tail_integration_20261001a/offline_full03/case00-fixed'", '')
    prepare = replace_once(prepare, "'source_sha256':hash(source),'source_mode'", "'source_sha256':hash(source),'source_case_id':case_id,'case_ordinal':ordinal,'namespace':namespace,'native_case_binding_verified':False,'source_mode'")
    prepare = replace_once(prepare, "params_json=canon(params); packet=", "identity={'namespace':namespace,'case_ordinal':ordinal,'source_case_id':case_id,'source_sha256':hash(source),'native_case_binding_verified':False}\nidentity['engineering_case_binding_sha256']=hash(canon(identity))\nparams_json=canon(params); packet=")
    prepare = replace_once(prepare, "'schema':'radio-native-v2-offline-frozen-request-v1','tool'", "'control_case_identity':identity,'schema':'radio-native-v2-offline-frozen-request-v1','tool'")
    prepare = replace_once(prepare, "'source_bytes':len(source),'source_sha256':hash(source),'archive_bytes'", "'control_case_identity':identity,'source_bytes':len(source),'source_sha256':hash(source),'archive_bytes'")
    helper_start = source.index('const ensure=')
    prepare = replace_once(prepare, "'control_case_identity':identity,'source_bytes':len(source)",
        "'control_case_identity':identity,'source_domain_hex':domain.hex(),'source_bytes':len(source)")
    helper_end = source.index('const PREPARE=String.raw`')
    helpers = source[helper_start:helper_end]
    caller_start = source.index('async function caller(scope){')
    caller_end = source.index('async function runOfflineFixture(')
    caller = source[caller_start:caller_end]
    caller = replace_once(caller, "startup={cmd:'offline mock controller maximum source-only fixture'", "startup={cmd:'fresh offline maximum component '+prepared.control_case_identity.source_case_id")
    caller = replace_once(caller, 'session=741;', 'session=742000+prepared.control_case_identity.case_ordinal;')
    caller = replace_once(caller, "message:'Offline maximum-size fixture; no public mutation'", "message:'Fresh offline maximum component '+prepared.control_case_identity.source_case_id")
    caller = replace_once(caller, "status:'SINGLE_CASE_COMPONENT_ONLY',fixture_only:true", "status:'SINGLE_CASE_COMPONENT_ONLY',fixture_only:true,control_case_identity:prepared.control_case_identity")
    caller = replace_once(caller, '_meta:{offline_fixture:true}', '_meta:{offline_fixture:true,control_case_identity:prepared.control_case_identity}')
    caller = replace_once(caller, "cp.execFile('/bin/bash',['--noprofile','--norc','-c',args.cmd]", "cp.execFile(prepared.python,['-I','-S','-B',path.join(code,'"+SELF+"'),'--command-worker',scope,'command-'+String(readByCommand.get(args.cmd)?.ordinal??'tail'),args.cmd]")
    caller = replace_once(caller, '{schema:SCHEMA,qualified,seen,deliveries,read_receipts:readReceipts}', '{schema:SCHEMA,control_case_identity:prepared.control_case_identity,qualified,seen,deliveries,read_receipts:readReceipts}')
    header = "'use strict';\nconst fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),crypto=require('node:crypto');\n"
    caller = replace_once(caller, 'const result={schema:SCHEMA,status:qualified.status',
        'const result={schema:SCHEMA,control_case_identity:prepared.control_case_identity,controller_terminal:qualified.client.controller_terminal,status:qualified.status')
    header += 'const MIB=1024*1024,LIMITS='+json.dumps({'calls':64,'request_bytes':48*MIB,'response_bytes':64*MIB,'seconds':600,'rss_bytes':512*MIB})+',SCHEMA='+json.dumps(SCHEMA)+';\n'
    caller_code = header + helpers + caller + "\nif(process.argv.length!==4||process.argv[2]!=='--caller')throw Error('Exact fresh caller mode required');caller(path.resolve(process.argv[3])).catch(error=>{process.stderr.write(String(error)+'\\n');process.exitCode=1;});\n"
    return {'prepare.py': prepare.encode(), 'fresh-caller.js': caller_code.encode(),
        'lossless-helper.js': LOSSLESS_HELPER.encode()}


def build_plan(repo=REPO):
    repo = Path(repo)
    code = {path: pin(repo/path) for path in CODE_FILES}
    derived = templates((repo/CODE_FILES[0]).read_text(), repo)
    runtime = {}
    for name, executable in (('python', sys.executable), ('node', shutil.which('node'))):
        if not executable: raise ValueError('Required runtime executable absent: '+name)
        path = Path(executable).resolve()
        runtime[name] = {'path': str(path), **pin(path)}
    return {'schema': PLAN_SCHEMA, 'namespace': NAMESPACE, 'mode': 'PROSPECTIVE_NOT_EXECUTED',
        'execution_status':EXECUTION_STATUS,'execution_blockers':list(EXECUTION_BLOCKERS),
        'large_source_generation_admitted':False,'large_inputs_generated':False,'activation_guard_complete':False,
        'complete_resource_measurement_join_qualified':False,
        'code_files': code, 'derived_code': {name: {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()} for name, raw in derived.items()},
        'runtime_executables': runtime, 'engineering_runtime_supplement':runtime_supplement(),
        'child_environment':CHILD_ENVIRONMENT,'complete_runtime_freeze_required': True,
        'public_immutable_preread_required': True, 'original_limits': LIMITS,
        'prospective_shared_storage_allocation_complete':False,
        'cases': [{'ordinal': ordinal, 'source_case_id': NAMESPACE+f'/case{ordinal:02d}',
            'source_domain_hex': source_domain(ordinal).hex(), 'archive_prefix': PREFIX+f'/case{ordinal:02d}-fixed',
            'source_bytes': 26*MIB, 'archive_files': 28, 'archive_bytes': 36875057,
            'source_read_fragments': 38, 'mock_connector_operations': 6,
            'mock_delivery_operations': 6, 'real_legacy_tail_operations': 1,
            'courier_charged_calls_expected': 56, 'case_operation_reservation': 64} for ordinal in range(8)],
        'lossless_evidence_required': True, 'retained_raw_inputs_must_not_be_duplicated': True,
        'scope_reuse_or_retry_permitted': False,
        'timing_allocation':{'case_phase':'generation through lossless proof and evidence fsync',
            'verifier_append':'exact per-case append duration','final_readback':'one eighth to each case',
            'all_other_preparation_observer_and_finalization_gaps':'one eighth to each case'},
        'call_accounting_scope':'visible courier protocol operations plus4declaredGit; internal local process observations counted separately',
        'rss_accounting_scope':'maximum individual process in completely reaped tree; not sum of simultaneous process RSS',
        **AUTHORITY}


def require_execution_ready():
    """A reviewed preparation artifact cannot activate its unfinished runner."""
    if EXECUTION_STATUS!='READY_FOR_EXACT_PUBLIC_PREREAD':
        raise RuntimeError('BLOCKED_PREPARATION_REVIEW: large worker/run execution is closed; '+EXECUTION_BLOCKERS[0])


def verify_fresh_source_domain(path, ordinal, expected_bytes):
    """Read-only domain verification with one 64-KiB window, no admission.

    Production calls this inside the still-closed worker after source creation.
    Preparation tests exercise tiny ranges only, never a maximum input.
    """
    domain = source_domain(ordinal)
    if type(expected_bytes) is not int or not 0 < expected_bytes <= 26*MIB:
        raise ValueError('Exact positive bounded fresh source length required')
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    digest = hashlib.sha256(); offset = 0
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size!=expected_bytes:
            raise ValueError('Exact sole-link fresh source length required')
        while offset < expected_bytes:
            amount = min(65536,expected_bytes-offset)
            raw = os.pread(fd,amount,offset)
            expected = b''.join(hashlib.sha256(domain+counter.to_bytes(8,'big')).digest()
                for counter in range(offset//32,(offset+amount+31)//32))[:amount]
            if raw != expected:
                raise ValueError('Fresh payload differs from fixed ordinal counter domain')
            digest.update(raw); offset += amount
        after = os.fstat(fd); named = os.stat(path,follow_symlinks=False)
        fields = lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_nlink)
        if fields(before)!=fields(after) or fields(after)!=fields(named):
            raise ValueError('Fresh source identity changed during independent domain verification')
    finally: os.close(fd)
    return {'bytes':offset,'sha256':digest.hexdigest(),'source_domain_hex':domain.hex(),
        'case_ordinal':ordinal,'native_case_binding_verified':False}


def audit_fresh_identity(prepared, fixed, source_proof, terminal=None):
    """Bind preparation and terminal to the outer ordinal and domain proof."""
    ordinal = fixed['ordinal']; domain = source_domain(ordinal).hex()
    if (fixed['source_case_id']!=NAMESPACE+f'/case{ordinal:02d}'
            or fixed['archive_prefix']!=PREFIX+f'/case{ordinal:02d}-fixed'
            or fixed['source_domain_hex']!=domain
            or type(fixed['source_bytes']) is not int or fixed['source_bytes']!=26*MIB):
        raise ValueError('Exact fixed outer ordinal, source domain and maximum shape required')
    if (type(source_proof.get('bytes')) is not int or source_proof['bytes']!=fixed['source_bytes']
            or source_proof.get('source_domain_hex')!=domain
            or type(source_proof.get('case_ordinal')) is not int or source_proof['case_ordinal']!=ordinal
            or source_proof.get('native_case_binding_verified') is not False
            or not re.fullmatch('[0-9a-f]{64}',source_proof.get('sha256',''))):
        raise ValueError('Exact independently checked fresh source-domain proof required')
    expected = {'namespace':NAMESPACE,'case_ordinal':ordinal,'source_case_id':fixed['source_case_id'],
        'source_sha256':source_proof['sha256'],'native_case_binding_verified':False}
    expected['engineering_case_binding_sha256'] = hashlib.sha256(canonical(expected)).hexdigest()
    if (canonical(prepared.get('control_case_identity'))!=canonical(expected)
            or prepared.get('source_domain_hex')!=domain
            or type(prepared.get('source_bytes')) is not int or prepared['source_bytes']!=source_proof['bytes']
            or prepared.get('source_sha256')!=source_proof['sha256']):
        raise ValueError('Prepared identity differs from independently checked outer source domain')
    if terminal is not None:
        if (not isinstance(terminal,dict) or terminal.get('kind')!='terminal'
                or terminal.get('status')!='SINGLE_CASE_COMPONENT_ONLY'
                or terminal.get('fixture_only') is not True
                or canonical(terminal.get('control_case_identity'))!=canonical(expected)):
            raise ValueError('Fresh terminal identity differs from fixed outer source domain')
    return expected


def runtime_supplement():
    """Explicitly pin cache/config bytes excluded by the historical freezer."""
    stdlib=Path(sysconfig.get_path('stdlib')); files=set()
    for path in stdlib.rglob('*.pyc'):
        if 'site-packages' not in path.relative_to(stdlib).parts and path.is_file(): files.add(path.resolve())
    for entry in sys.path:
        path=Path(entry)
        if path.suffix=='.zip' and path.is_file(): files.add(path.resolve())
    for value in ('/etc/ssl/openssl.cnf','/usr/lib/ssl/openssl.cnf'):
        path=Path(value)
        if path.is_file(): files.add(path.resolve())
    for folder in ('/usr/lib/x86_64-linux-gnu/ossl-modules','/usr/lib/aarch64-linux-gnu/ossl-modules'):
        root=Path(folder)
        if root.exists(): files.update(path.resolve() for path in root.glob('*.so') if path.is_file())
    return {'schema':SCHEMA+'-engineering-runtime-supplement','files':{str(path):pin(path) for path in sorted(files)},
        'repository_bytecode_copied':False,'child_python_flags':['-I','-S','-B'],
        'child_repository_imports_use_fresh_source_only':True,'scientific_runtime_qualified':False}


def validate_activation(plan, preread, freeze, repo=REPO):
    """Preparation subset checks only; the execution status stays hard closed.

    These checks are intentionally not a substitute for the complete original
    freezer validator plus an independently recomputed expected closure. That
    join is an explicit prospective blocker and cannot admit this component.
    """
    require_execution_ready()
    if plan != build_plan(repo): raise ValueError('Exact current prospective plan/code/runtime executable pins required')
    expected = {'schema': PREREAD_SCHEMA, 'namespace': NAMESPACE,
        'plan_sha256': hashlib.sha256(canonical(plan)).hexdigest(),
        'complete_freeze_sha256': hashlib.sha256(canonical(freeze)).hexdigest(),
        'public_immutable_readback_verified': True, 'engineering_control_admitted': True,
        'code_files_verified': plan['code_files']}
    if not isinstance(preread, dict) or any(preread.get(key) != value for key, value in expected.items()):
        raise ValueError('Exact independently retained immutable public preread required before source generation')
    if not re.fullmatch('[0-9a-f]{40}', preread.get('preparation_commit', '')):
        raise ValueError('Immutable public preparation commit required')
    if any(preread.get(key) != value for key, value in AUTHORITY.items()):
        raise ValueError('Preread cannot grant native or scientific authority')
    if (freeze.get('schema') != 'radio-native-v2-runner-broker-runtime-freeze-v1'
            or freeze.get('freeze_kind') != 'COMPLETE_RUNNER_BROKER_RUNTIME'
            or freeze.get('mode') != 'PROSPECTIVE_ENGINEERING_ONLY'
            or any(freeze.get(key) is not False for key in ('execution_authorized','reservation_authorized','scientific_execution_authorized','restart_authorized','rng_authorized','transport_integration_qualified'))
            or freeze.get('transport_qualification') is not None):
        raise ValueError('Complete non-authorizing runner runtime freeze required')
    for path, wanted in plan['code_files'].items():
        if path.startswith('tests/'): continue
        if freeze.get('code_sha256s', {}).get(path) != wanted['sha256']:
            raise ValueError('Complete freeze does not bind material code: '+path)
    for inventory, hashes, prefix in (('repository_code_inventory','code_sha256s',Path(repo)),
            ('input_file_inventory','input_sha256s',Path(repo)),('runtime_file_inventory','runtime_sha256s',None)):
        files = freeze.get(inventory); pins = freeze.get(hashes)
        if not isinstance(files, list) or not isinstance(pins, dict) or files != sorted(pins):
            raise ValueError('Exact complete freeze inventory required: '+inventory)
        for path, digest in pins.items():
            if not re.fullmatch('[0-9a-f]{64}', digest) or pin(Path(path) if prefix is None else prefix/path)['sha256'] != digest:
                raise ValueError('Complete frozen file identity drift: '+path)
    for runtime in plan['runtime_executables'].values():
        if freeze['runtime_sha256s'].get(runtime['path']) != runtime['sha256']:
            raise ValueError('Runtime executable omitted from complete freeze')
    # The external freeze's hashed parent environment is checked without
    # publishing any configured values. Children always use the fixed allowlist.
    environments=freeze.get('environment_fingerprints')
    if not isinstance(environments,dict) or not environments:
        raise ValueError('Complete freeze environment fingerprints required')
    observed={name:hashlib.sha256(os.environ[name].encode()).hexdigest() if name in os.environ else None for name in environments}
    if observed!=environments: raise ValueError('Complete frozen parent environment drift')
    return expected


def proc_memory(pid):
    fields = {}
    for line in (Path('/proc')/str(pid)/'status').read_text().splitlines():
        if ':' in line:
            key, value = line.split(':', 1); fields[key] = value.strip()
    return {'at_epoch_ms': time.time_ns()//1000000,
        'rss_bytes': int(fields.get('VmRSS','0 kB').split()[0])*1024,
        'kernel_vm_hwm_bytes': int(fields.get('VmHWM','0 kB').split()[0])*1024}


def inventory(root):
    rows = []
    for path in [Path(root)]+sorted(Path(root).rglob('*')):
        info = path.lstat()
        is_directory=stat.S_ISDIR(info.st_mode)
        if not is_directory and (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1):
            raise ValueError('Ordinary sole-link retained control files required')
        rows.append({'path': str(path.relative_to(root)), 'kind':'directory' if is_directory else 'file',
            'bytes': info.st_size, 'allocated_bytes': info.st_blocks*512})
    return {'files': rows, 'logical_bytes': sum(row['bytes'] for row in rows),
        'allocated_bytes': sum(row['allocated_bytes'] for row in rows)}


def launched_child_identity(namespace_pid):
    """Map the launched PID through independently read procfs membership.

    The procfs mount can show a containing PID namespace, so Popen.pid is not
    necessarily a usable /proc path. A child report is not an independent map.
    Zombies stay discoverable here until this observer's sole wait4 reaps them.
    """
    observer = int(os.readlink('/proc/self'))
    candidates = []
    # Some kernels omit task/children. PPid + NSpid form the independent
    # direct-child mapping even when procfs shows a containing namespace.
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            text = (Path('/proc')/str(pid)/'status').read_text()
            parent = re.search(r'^PPid:\s+(\d+)', text, re.M)
            namespace = re.search(r'^NSpid:\s+([0-9 \t]+)$', text, re.M)
            if not parent or not namespace:
                continue
            namespace_ids = [int(item) for item in namespace.group(1).split()]
            if int(parent.group(1)) != observer or namespace_ids[-1] != namespace_pid:
                continue
            ticks = (Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19]
            candidates.append({'procfs_pid':pid,'namespace_pid':namespace_pid,
                'procfs_start_ticks':ticks,'namespace_pid_chain':namespace_ids})
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    if len(candidates) != 1:
        raise ValueError('Exactly one independently mapped launched direct child required')
    return candidates[0]


def observe_process(argv, root, label, identity_path, *, deadline, on_tick=None, output_cap=LOG_LIMIT, pipe_output=False,new_session=False):
    """Bounded direct-child observation; descendant reap coverage stays unknown."""
    root = Path(root); start = time.time_ns()//1000000
    stdout_path = root/(label+'-stdout.log'); stderr_path = root/(label+'-stderr.log')
    stdout_file = stdout_path.open('xb'); stderr_file = stderr_path.open('xb')
    child = subprocess.Popen(argv, stdout=subprocess.PIPE if pipe_output else stdout_file,
        stderr=subprocess.PIPE if pipe_output else stderr_file, env=CHILD_ENVIRONMENT,start_new_session=new_session)
    selector = selectors.DefaultSelector(); buffers = {'stdout':bytearray(),'stderr':bytearray()}
    if pipe_output:
        for name, stream in (('stdout',child.stdout),('stderr',child.stderr)):
            os.set_blocking(stream.fileno(),False); selector.register(stream,selectors.EVENT_READ,name)
    samples = []; proc_pid = None; reason = None; status = usage = None; peak=0; bound_identity=None
    sample_count = 0; reported_identity_verified = False
    observed_output_bytes = {'stdout':0,'stderr':0}
    try:
        bound_identity = launched_child_identity(child.pid)
        proc_pid = bound_identity['procfs_pid']
        while status is None or (pipe_output and selector.get_map()):
            if not reported_identity_verified and Path(identity_path).exists():
                try:
                    reported = small_json(identity_path)
                    reported_pid = reported.get('procfs_pid',reported.get('proc_pid'))
                    namespace_pid=reported.get('namespace_pid',reported.get('pid'))
                    if (type(reported_pid) is not int or type(namespace_pid) is not int
                            or reported_pid!=proc_pid or namespace_pid!=child.pid):
                        raise ValueError('Reported identity differs from independently launched direct child')
                    reported_identity_verified = True
                except json.JSONDecodeError: pass
            if proc_pid is not None:
                try:
                    ticks=(Path('/proc')/str(proc_pid)/'stat').read_text().rsplit(')',1)[1].split()[19]
                    if ticks!=bound_identity['procfs_start_ticks']: raise ValueError('Child procfs identity recycled')
                    sample=proc_memory(proc_pid); sample_count += 1
                    if len(samples)<OBSERVATION_SAMPLE_LIMIT:
                        samples.append(sample)
                    else:
                        samples[-1] = sample
                    peak=max(peak,sample['rss_bytes'],sample['kernel_vm_hwm_bytes'])
                except (FileNotFoundError,ProcessLookupError): pass
            if pipe_output:
                for key,_ in selector.select(0.005):
                    raw = os.read(key.fileobj.fileno(),65536)
                    if not raw: selector.unregister(key.fileobj); key.fileobj.close(); continue
                    observed_output_bytes[key.data] += len(raw)
                    remaining = max(0,output_cap-len(buffers[key.data]))
                    buffers[key.data].extend(raw[:remaining])
                    if observed_output_bytes[key.data]>output_cap: reason = 'Bounded child output cap exceeded'
            else:
                if stdout_path.stat().st_size>output_cap or stderr_path.stat().st_size>output_cap:
                    reason = 'Bounded child log cap exceeded'
            if time.monotonic()>deadline: reason = 'Fixed control phase deadline exceeded'
            if peak>LIMITS['rss_bytes']: reason = 'Original512MiB material process cap exceeded'
            if on_tick: on_tick({'procfs_pid':proc_pid,'peak_rss_bytes':peak,'start_epoch_ms':start,'samples':samples,
                'sample_count':sample_count})
            if reason and status is None:
                # Popen.kill() polls and can reap before our sole wait4 owner.
                # The unreaped child PID cannot yet be recycled.
                try:
                    if new_session: os.killpg(child.pid,signal.SIGKILL)
                    else: os.kill(child.pid,signal.SIGKILL)
                except ProcessLookupError: pass
            # Keep an exited root unreaped while descendants can retain pipes.
            # Its PID/PGID then cannot be recycled before bounded cancellation.
            if status is None and (not pipe_output or not selector.get_map() or reason):
                waited, wait_status, waited_usage = os.wait4(child.pid,os.WNOHANG)
                if waited:
                    status = os.waitstatus_to_exitcode(wait_status); usage = waited_usage; child.returncode = status
            if reason and status is not None:
                # A descendant can retain inherited pipes after the direct
                # child exits. The fixed deadline still closes this observer.
                for key in list(selector.get_map().values()):
                    selector.unregister(key.fileobj); key.fileobj.close()
                break
            if not pipe_output: time.sleep(0.005)
        if not reported_identity_verified:
            reason = reason or 'Required direct-child identity was never verified'
        if pipe_output:
            # Source bytes already live in the authoritative caller transcript.
            # Persisting them again here would add37MB and break192MiB custody.
            stderr_file.write(buffers['stderr'][:LOG_LIMIT])
        stdout_file.flush(); stderr_file.flush(); os.fsync(stdout_file.fileno()); os.fsync(stderr_file.fileno())
    except BaseException as error:
        reason='Observer/child phase failed: '+repr(error)
    finally:
        for key in list(selector.get_map().values()):
            selector.unregister(key.fileobj); key.fileobj.close()
        selector.close(); stdout_file.close(); stderr_file.close()
        if status is None:
            try:
                if new_session: os.killpg(child.pid,signal.SIGKILL)
                else: os.kill(child.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            _,wait_status,usage=os.wait4(child.pid,0); child.returncode=os.waitstatus_to_exitcode(wait_status); status=child.returncode
    end = time.time_ns()//1000000
    measured = max([usage.ru_maxrss*1024]+[max(row['rss_bytes'],row['kernel_vm_hwm_bytes']) for row in samples])
    if measured>LIMITS['rss_bytes']: reason = 'Original512MiB complete material process lifetime cap exceeded'
    result = {'schema':SCHEMA+'-process-observation','label':label,
        'observer_source':'independent_parent_procfs_and_kernel_wait4','observer_procfs_pid':int(os.readlink('/proc/self')),
        'child_procfs_pid':proc_pid,'interval_start_epoch_ms':start,'interval_end_epoch_ms':end,
        'elapsed_seconds':(end-start)/1000,'wait4_ru_maxrss_bytes':usage.ru_maxrss*1024,
        'peak_rss_bytes':measured,'sample_count':sample_count,'exit_code':status,'reason':reason,
        'bound_child_identity':bound_identity,'includes_entire_child_lifetime':True,
        'reported_identity_verified':reported_identity_verified,
        'direct_child_reaped':True,
        'wait4_maximum_includes_completely_reaped_descendants':False,
        'tree_termination_coverage':'NOT_INDEPENDENTLY_VERIFIED',
        'complete_descendant_wait_chain_verified':False,
        'retained_sample_count':len(samples),'sample_retention_limit':OBSERVATION_SAMPLE_LIMIT,
        'observed_output_bytes':observed_output_bytes,'complete_pipe_output':pipe_output and reason is None,
        'aggregate_concurrent_rss_measured':False,'raw_stdout_duplicate_written':False if pipe_output else None,
        'samples':samples,**AUTHORITY}
    write(root/(label+'-observation.json'),result)
    if status!=0 or reason: raise RuntimeError('Fixed child/control scope closed: '+label+': '+str(reason or status))
    return result, bytes(buffers['stdout']), bytes(buffers['stderr'])


def identity(path):
    write(path, {'procfs_pid':int(os.readlink('/proc/self')),'namespace_pid':os.getpid(),
        'started_at_epoch_ms':time.time_ns()//1000000})


def command_worker(case_root, label, command):
    require_execution_ready()
    if not re.fullmatch('command-(?:[0-9]{1,2}|tail)',label) or len(command.encode())>96*1024:
        raise ValueError('Bounded pinned local command required')
    root = Path(case_root)/'command-observations'; root.mkdir(exist_ok=True)
    identity(root/(label+'-supervisor-identity.json'))
    _,stdout,stderr = observe_process([sys.executable,'-I','-S','-B',str(Path(__file__).resolve()),
        '--exec-command-child',str(root),label,command],root,label,root/(label+'-identity.json'),
        deadline=time.monotonic()+120,output_cap=2*MIB,pipe_output=True)
    # Exact source/tail output returns to the unchanged portable caller.
    sys.stdout.buffer.write(stdout); sys.stdout.buffer.flush()
    sys.stderr.buffer.write(stderr); sys.stderr.buffer.flush()


def exec_command_child(root,label,command):
    require_execution_ready()
    identity(Path(root)/(label+'-identity.json'))
    arguments=shlex.split(command)
    if len(arguments)<6 or Path(arguments[0]).resolve()!=Path(sys.executable).resolve() or arguments[1:4]!=['-I','-S','-B']:
        raise ValueError('One exact pinned isolated Python argv required; shell syntax is not executed')
    os.execve(arguments[0],arguments,CHILD_ENVIRONMENT)


def copy_code(source_root, destination, expected=None):
    for relative in CODE_FILES:
        raw=(Path(source_root)/relative).read_bytes()
        if expected is not None and {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=expected[relative]:
            raise ValueError('Prospectively frozen source changed before materialization: '+relative)
        path = Path(destination)/relative; path.parent.mkdir(parents=True,exist_ok=True)
        write(path,raw)
        if expected is not None and pin(path)!=expected[relative]:
            raise ValueError('Materialized frozen source identity differs: '+relative)


def pinned_component(code_root, relative, expected):
    """Load a verified material source buffer, without an import-cache read."""
    path = Path(code_root)/relative
    wanted = expected[relative]
    if type(wanted.get('bytes')) is not int or not 0 < wanted['bytes'] <= 2*MIB:
        raise ValueError('Bounded positive material source pin required')
    fd = os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size!=wanted['bytes']:
            raise ValueError('Exact sole-link regular material source required')
        raw = bytearray()
        while True:
            block = os.read(fd,65536)
            if not block: break
            raw.extend(block)
            if len(raw)>wanted['bytes']: raise ValueError('Material source exceeded frozen byte count')
        after = os.fstat(fd); named = path.stat(follow_symlinks=False)
        stable = lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
        if stable(before)!=stable(after) or stable(after)!=stable(named):
            raise ValueError('Material source changed during descriptor read')
    finally: os.close(fd)
    if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=wanted:
        raise ValueError('Materialized component differs from the prospective pin: '+relative)
    module = {'__name__':'frozen_engineering_component','__file__':str(path)}
    exec(compile(bytes(raw),str(path),'exec'),module)
    return module


def check_storage(scope):
    scope = Path(scope); result = inventory(scope)
    if max(result['logical_bytes'],result['allocated_bytes'])>LIMITS['run_storage_bytes']:
        raise ValueError('Original1536MiB retained whole control storage cap exceeded')
    cases = []
    for root in sorted((scope/'cases').glob('case[0-9][0-9]')) if (scope/'cases').exists() else []:
        row = inventory(root)
        if max(row['logical_bytes'],row['allocated_bytes'])>LIMITS['case_storage_bytes']:
            raise ValueError('Original192MiB retained case storage cap exceeded')
        cases.append({'ordinal':int(root.name[-2:]),**row})
    return {'whole':result,'cases':cases}


def verifier_worker(scope):
    require_execution_ready()
    scope = Path(scope); identity(scope/'verifier-identity.json')
    spec = importlib.util.spec_from_file_location('frozen_compact_verifier',REPO/'scripts/radio_native_v2_compact_run_verifier.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    verifier = module.CompactRunVerifier(scope/'compact-receipt',small_json(scope/'compact-input-plan.json'))
    phases = []
    for ordinal in range(8):
        start = time.monotonic(); verifier.append(ordinal)
        phases.append({'ordinal':ordinal,'append_seconds':time.monotonic()-start})
    start = time.monotonic(); receipt = verifier.finish()
    write(scope/'verifier-timing.json', {'append_phases':phases,'final_independent_readback_seconds':time.monotonic()-start,
        'case_count':receipt['case_count'],'status':receipt['status'],**AUTHORITY})


def control_worker(scope):
    """Fresh full scope; raw source generation occurs only inside this worker."""
    require_execution_ready()
    scope = Path(scope); identity(scope/'control-worker-identity.json')
    plan = small_json(scope/'plan.json'); started = time.monotonic(); rows = []; compact_inputs = []
    preread = small_json(scope/'public-preread.json'); freeze = small_json(scope/'complete-freeze.json')
    frozen = scope/'frozen-code'; runtime = plan['runtime_executables']; python = runtime['python']['path']; node = runtime['node']['path']
    sources = templates((frozen/CODE_FILES[0]).read_text(), frozen)
    for name,raw in sources.items():
        if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=plan['derived_code'][name]:
            raise ValueError('Prospective derived source changed before generation: '+name)
    cases_root = scope/'cases'; cases_root.mkdir()
    try:
        for fixed in plan['cases']:
            ordinal = fixed['ordinal']; root = cases_root/f'case{ordinal:02d}'; root.mkdir(mode=0o700)
            phase_start = time.monotonic(); deadline = phase_start+LIMITS['case_seconds']
            copy_code(frozen,root/'frozen-code',plan['code_files'])
            (root/'derived').mkdir()
            for name,raw in sources.items(): write(root/'derived'/name,raw)
            write(root/'prospective-case-pins.json', {'fixed_input':fixed,'plan_sha256':hashlib.sha256(canonical(plan)).hexdigest(),
                'code_files':plan['code_files'],'derived_code':plan['derived_code'],**AUTHORITY})
            admission = pinned_component(root/'frozen-code','scripts/radio_native_v2_worker_admission.py',plan['code_files'])
            bundle = admission['build_admission_bundle'](plan,freeze,preread,execution_scope=scope,ordinal=ordinal)
            bundle_path = root/'worker-admission.json'; write(bundle_path,bundle)
            bundle_sha256 = pin(bundle_path)['sha256']
            supervisor_scope = root/'preparation-supervisor'
            # This dispatch is still behind the global preparation gate. The
            # dedicated process repeats admission before mkdir/Popen; the
            # derived source worker repeats it before its first data write.
            observe_process([python,'-I','-S','-B',str(root/'frozen-code'/'scripts/radio_native_v2_process_tree_supervisor.py'),
                '--admitted-prepare-worker','--admission-bundle',str(bundle_path),'--bundle-sha256',bundle_sha256,
                '--ordinal',str(ordinal),'--scope',str(supervisor_scope),
                '--seconds',str(max(0,deadline-time.monotonic()))],
                root,'preparation',supervisor_scope/'supervisor-identity.json',deadline=deadline)
            preparation_receipt = small_json(supervisor_scope/'subreaper-receipt.json')
            if (preparation_receipt.get('status')!='ENGINEERING_SUBREAPER_SCOPE_COMPLETE'
                    or preparation_receipt.get('subreaper_scope_reaped_to_echild') is not True
                    or preparation_receipt.get('maximum_individual_process_rss_bytes',LIMITS['rss_bytes']+1)>LIMITS['rss_bytes']):
                raise ValueError('Dedicated admitted preparation did not close within the fixed process scope')
            prepared = small_json(root/'prepared.json')
            source_proof = verify_fresh_source_domain(root/'deterministic-source.bin',ordinal,fixed['source_bytes'])
            expected_identity = audit_fresh_identity(prepared,fixed,source_proof)
            if (prepared['control_case_identity']!=expected_identity or prepared['archive_bytes']!=36875057
                    or prepared['archive_files']!=28 or len(prepared['reads'])!=38 or prepared['source_bytes']!=26*MIB):
                raise ValueError('Fresh prepared source/identity/maximum shape differs')
            if not all(path.startswith(fixed['archive_prefix']+'/') for path in prepared['files']):
                raise ValueError('Fresh archive paths do not bind the fixed outer ordinal')
            observation_written = False
            def observe_caller(context):
                nonlocal observation_written
                request_path = root/'rss-observation-request.json'
                if not observation_written and request_path.exists():
                    request = small_json(request_path)
                    if context['procfs_pid'] is None or context['peak_rss_bytes']<=0:
                        raise ValueError('Caller runtime identity was not independently observed')
                    write(root/'rss-observation.json', {'schema':'radio-native-v2-independent-client-rss-v1','measured':True,
                        'client_peak_rss_bytes':context['peak_rss_bytes'],'observer_source':'independent_procfs',
                        'caller_runtime_identity':'node-proc:'+str(context['procfs_pid']),
                        'observer_runtime_identity':'python-proc:'+os.readlink('/proc/self'),
                        'interval_start_epoch_ms':context['start_epoch_ms'],'interval_end_epoch_ms':time.time_ns()//1000000,
                        'procfs_sample_count':context['sample_count'],'client_sha256':request['client_sha256']})
                    observation_written = True
            observed,_,_ = observe_process([node,str(root/'derived'/'fresh-caller.js'),'--caller',str(root)],root,'caller',root/'caller-start.json',
                deadline=deadline,on_tick=observe_caller)
            caller = small_json(root/'caller-summary.json')
            if canonical(caller.get('control_case_identity'))!=canonical(expected_identity):
                raise ValueError('Caller summary does not bind the checked fresh source domain')
            audit_fresh_identity(prepared,fixed,source_proof,caller.get('controller_terminal',{}))
            if (caller['status']!='SINGLE_CASE_TRANSPORT_COMPONENT_COMPLETE' or caller['source_reads']!=38
                    or caller['mock_connector_operations']!=6 or caller['mock_delivery_operations']!=6
                    or caller['real_local_tail_saver_calls']!=1):
                raise ValueError('Exact fresh maximum caller/component did not complete')
            commands = sorted((root/'command-observations').glob('command-*-observation.json'))
            if len(commands)!=39 or any(small_json(path)['reason'] is not None for path in commands):
                raise ValueError('Every real source reader and tail needs independent complete process observation')
            # Projector integration is deliberately mandatory before activation.
            # The helper operates on the freshly generated retained source, and
            # emits exact small envelopes + lazy regeneration descriptors only.
            helper = scope/'lossless-helper.js'
            if not helper.is_file(): raise ValueError('Frozen lossless helper integration absent')
            evidence = root/'public-evidence'; evidence.mkdir()
            recipe_args = [str(root),python,NAMESPACE,str(ordinal),fixed['archive_prefix'],str(bundle_path),bundle_sha256]
            project_args = {'fullPath':str(root/'caller-result.json'),'preparedPath':str(root/'prepared.json'),
                'recipePath':str(root/'derived'/'prepare.py'),'projectionPath':str(evidence/'caller-transcript-compact-lossless.json'),
                'recipeArguments':recipe_args,'identityPath':str(root/'lossless-project-identity.json')}
            write(root/'project-arguments.json',project_args)
            observe_process([node,str(helper),'--resource-project',str(root/'project-arguments.json')],root,'lossless-project',root/'lossless-project-identity.json',deadline=deadline)
            verify_args = {'projectionPath':project_args['projectionPath'],'recipePath':project_args['recipePath'],
                'retainedSourcePath':prepared['request_view']['path'],'retainedPayloadPath':str(root/'deterministic-source.bin'),
                'auditPath':str(evidence/'reconstruction-audit.json'),'python':python,'identityPath':str(root/'lossless-verify-identity.json')}
            write(root/'projection-verify-arguments.json',verify_args)
            observe_process([node,str(helper),'--resource-verify-retained',str(root/'projection-verify-arguments.json')],root,'lossless-verify',root/'lossless-verify-identity.json',deadline=deadline)
            write(evidence/'fresh-prepare.py',(root/'derived'/'prepare.py').read_bytes())
            write(evidence/'preparation-subreaper-receipt.json',canonical(preparation_receipt))
            for path in ('prepared.json','prospective-case-pins.json','caller-summary.json','caller-observation.json','preparation-observation.json'):
                write(evidence/path,(root/path).read_bytes())
            write(evidence/'independent-command-observations.json',[small_json(path) for path in commands])
            storage = check_storage(scope); case_storage = next(row for row in storage['cases'] if row['ordinal']==ordinal)
            raw_pin = pin(root/'caller-result.json'); raw_stat = (root/'caller-result.json').stat()
            compact_inputs.append({'ordinal':ordinal,'source_case_id':fixed['source_case_id'],'source_path':str(root/'caller-result.json'),
                **raw_pin,'client_peak_rss_bytes':observed['peak_rss_bytes'],
                'other_host_receipt_bytes':case_storage['logical_bytes']-raw_pin['bytes'],
                'other_host_receipt_allocated_bytes':case_storage['allocated_bytes']-raw_stat.st_blocks*512})
            usage = caller['combined_usage']
            if usage['calls']>64 or usage['request_bytes']>48*MIB or usage['response_bytes']>64*MIB:
                raise ValueError('Original64/48/64 caller case allocation exceeded')
            rows.append({'ordinal':ordinal,'source_case_id':fixed['source_case_id'],'engineering_case_binding_sha256':expected_identity['engineering_case_binding_sha256'],
                'source_sha256':prepared['source_sha256'],'raw_transcript':raw_pin,'caller_peak_rss_bytes':observed['peak_rss_bytes'],
                'calls':usage['calls'],'request_bytes':usage['request_bytes'],'response_bytes':usage['response_bytes'],
                'preparation_through_lossless_seconds':time.monotonic()-phase_start,'component_shared_seconds':usage['elapsed_seconds']})
            write(scope/f'case{ordinal:02d}-closed.json', {'case':rows[-1],**AUTHORITY})
        if len({row['source_sha256'] for row in rows})!=8 or len({row['raw_transcript']['sha256'] for row in rows})!=8:
            raise ValueError('Eight independently derived fresh source/transcript identities required')
        write(scope/'compact-input-plan.json', {'schema':'radio-native-v2-compact-retained-run-plan-v1','run_id':NAMESPACE,'cases':compact_inputs})
        verifier_start = time.monotonic()
        observed,_,_ = observe_process([python,'-I','-S','-B',str(frozen/SELF),'--verifier-worker',str(scope)],scope,'verifier',scope/'verifier-identity.json',deadline=started+4800)
        verifier_seconds = time.monotonic()-verifier_start
        timing = small_json(scope/'verifier-timing.json'); wall_seconds = time.monotonic()-started
        prior_seconds = sum(row['preparation_through_lossless_seconds'] for row in rows)
        unattributed = wall_seconds-prior_seconds-verifier_seconds
        append_seconds = sum(row['append_seconds'] for row in timing['append_phases'])
        final_seconds = timing['final_independent_readback_seconds']
        observed_verifier_gap = max(0,verifier_seconds-append_seconds-final_seconds)
        for row,phase in zip(rows,timing['append_phases']):
            row['continuous_verifier_append_seconds'] = phase['append_seconds']
            row['final_readback_seconds_attributed'] = final_seconds/8
            row['observer_and_control_gap_seconds_attributed'] = (unattributed+observed_verifier_gap)/8
            row['complete_engineering_case_seconds'] = row['preparation_through_lossless_seconds']+phase['append_seconds']+final_seconds/8+(unattributed+observed_verifier_gap)/8
            if row['complete_engineering_case_seconds']>600: raise ValueError('Original600-second complete engineering case allocation exceeded')
        if wall_seconds>4800: raise ValueError('Original4800-second complete engineering run allocation exceeded')
        if sum(row['calls'] for row in rows)>512 or sum(row['request_bytes'] for row in rows)>384*MIB or sum(row['response_bytes'] for row in rows)>512*MIB:
            raise ValueError('Original cumulative caller transport allocation exceeded')
        storage = check_storage(scope)
        write(scope/'worker-result.json', {'schema':SCHEMA,'status':'OFFLINE_EIGHT_INPUT_RESOURCE_COMPONENT_PASSED',
            'cases':rows,'continuous_verifier_peak_rss_bytes':observed['peak_rss_bytes'],
            'continuous_verifier_observed_seconds':verifier_seconds,'complete_engineering_run_seconds':wall_seconds,
            'storage_before_final_summary':storage,'exact_native_or_http_host_join_qualified':False,
            'projection_proof_uses_freshly_generated_retained_source':True,
            'public_recipe_identity_verified':True,
            'public_recipe_regeneration_requires_independent_worker_admission':True,
            'public_recipe_can_independently_regenerate_fresh_sources':False,**AUTHORITY})
    except BaseException as failure:
        write(scope/'closed-failure.json', {'schema':SCHEMA,'status':'CLOSED_FAILED','completed_cases':rows,
            'error':repr(failure),'elapsed_seconds':time.monotonic()-started,**AUTHORITY})
        raise


def run_control(scope,plan,preread,freeze,lossless_helper):
    require_execution_ready()
    preparation_started=time.monotonic()
    validate_activation(plan,preread,freeze)
    scope = Path(scope).absolute()
    if scope.exists(): raise RuntimeError('Fresh exclusive whole control scope required; no retry or resume')
    if lossless_helper is None or lossless_helper!=templates((REPO/CODE_FILES[0]).read_text())['lossless-helper.js']:
        raise ValueError('Exact prospectively pinned lossless helper required before source generation')
    scope.mkdir(mode=0o700,parents=True,exist_ok=False)
    write(scope/'plan.json',plan); write(scope/'public-preread.json',preread); write(scope/'complete-freeze.json',freeze)
    copy_code(REPO,scope/'frozen-code',plan['code_files'])
    write(scope/'lossless-helper.js',lossless_helper)
    started = time.monotonic()
    try:
        observed,_,_ = observe_process([plan['runtime_executables']['python']['path'],'-I','-S','-B',str(scope/'frozen-code'/SELF),
            '--control-worker',str(scope)],scope,'whole-control',scope/'control-worker-identity.json',deadline=preparation_started+4800,new_session=True)
        result = small_json(scope/'worker-result.json')
        storage = check_storage(scope)
        summary = {'schema':SCHEMA,'status':'PENDING_FINAL_MEASUREMENT_JOIN','worker_result':result,
            'whole_control_process_peak_rss_bytes':observed['peak_rss_bytes'],
            'whole_control_child_lifetime_seconds':observed['elapsed_seconds'],
            'outer_observer_self_ru_maxrss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'storage_before_summary':storage,'summary_and_inventory_storage_reserved_bytes':65536,
            'engineering_memory_control_only':True,**AUTHORITY}
        if summary['outer_observer_self_ru_maxrss_bytes']>LIMITS['rss_bytes']:
            raise ValueError('Original512MiB outer observer process cap exceeded')
        summary['public_preread_validation_and_freeze_preparation_seconds']=started-preparation_started
        summary['outer_observer_process_termination_covered']=False
        write(scope/'measured-summary.json',summary)
        final = check_storage(scope)
        write(scope/'storage-inventory.json',{'storage_before_inventory_itself':final,'inventory_itself_reserved_bytes':65536,**AUTHORITY})
        check_storage(scope)
        write(scope/'finalization-timing.json',{'complete_preparation_through_final_inventory_seconds':time.monotonic()-preparation_started,
            'shared_work_allocation':'one eighth of outer preparation/finalization to each fixed case',
            'parent_termination_and_this_final_timing_file_itself_excluded':True,**AUTHORITY})
        total=time.monotonic()-preparation_started
        if total>4800 or any(row['complete_engineering_case_seconds']+(total-result['complete_engineering_run_seconds'])/8>600 for row in result['cases']):
            raise ValueError('Original fixed full-scope time allocation exceeded including outer shared work')
        return summary
    except BaseException as failure:
        if not (scope/'outer-closed-failure.json').exists():
            write(scope/'outer-closed-failure.json',{'schema':SCHEMA,'status':'CLOSED_FAILED','error':repr(failure),**AUTHORITY})
        raise


def main():
    if len(sys.argv)>1 and sys.argv[1] in ('--command-worker','--exec-command-child','--verifier-worker','--control-worker'):
        require_execution_ready()
        mode=sys.argv[1]; args=sys.argv[2:]
        if mode=='--command-worker' and len(args)==3: return command_worker(*args)
        if mode=='--exec-command-child' and len(args)==3: return exec_command_child(*args)
        if mode=='--verifier-worker' and len(args)==1: return verifier_worker(*args)
        if mode=='--control-worker' and len(args)==1: return control_worker(*args)
        raise ValueError('Exact closed worker arguments required')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-plan',action='store_true')
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--scope',type=Path); parser.add_argument('--plan',type=Path)
    parser.add_argument('--preread',type=Path); parser.add_argument('--complete-freeze',type=Path)
    args=parser.parse_args()
    if args.run:
        require_execution_ready()
    if args.prepare_plan and not args.run:
        print(canonical(build_plan()).decode()); return
    if not args.run or args.prepare_plan or any(value is None for value in (args.scope,args.plan,args.preread,args.complete_freeze)):
        raise ValueError('Plan-only preparation or exact preread-bound fresh control invocation required')
    require_execution_ready()
    raise RuntimeError('Complete execution-admission integration must be reviewed before enabling this branch')


if __name__=='__main__':
    main()
