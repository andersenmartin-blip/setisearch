const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { utf8Bytes, runProbe } = require('../scripts/radio_native_v2_live_probe');

function fixture(fault) {
  const raw = fs.readFileSync('results_radio_native_v2_broker_live_2026-09-30/live01/freeze.json', 'utf8');
  const freeze = JSON.parse(raw);
  const pre = { freeze, freeze_utf8: raw, freeze_path: 'frozen.json', identity: 'fixture',
    parent: 'a'.repeat(40), parent_tree: 'b'.repeat(40), expected_tree: 'c'.repeat(40),
    freeze_sha256: 'd'.repeat(64) };
  const candidate = 'e'.repeat(40), methods = [];
  let head = pre.parent;
  const invoke = async (method, params) => {
    methods.push(method);
    let value;
    if (method === 'fetch_file') value = { content: fault === 'freeze' ? 'different' : raw };
    else if (method === 'fetch') {
      if (params.url.includes('/ref/heads/')) value = { object: { sha: head } };
      else if (params.url.endsWith(pre.parent)) value = { sha: pre.parent, tree: { sha: pre.parent_tree } };
      else value = { sha: candidate, tree: { sha: pre.expected_tree }, parents: [{ sha: pre.parent }] };
    } else if (method === 'create_tree') value = { sha: fault === 'tree' ? 'f'.repeat(40) : pre.expected_tree };
    else if (method === 'create_commit') value = { sha: candidate };
    else if (method === 'update_ref') {
      head = candidate;
      if (fault === 'lost_update') throw new Error('lost acknowledgement');
      value = { success: true };
    } else if (method === 'git_fetch') value = { fetched: true };
    else if (method === 'git_cat_file_batch') value = {
      exact_restoration: true, single_cat_file_batch: true, stored_bytes: 785,
      source_bytes: 35, source_sha256: fault === 'readback' ? '0'.repeat(64) : freeze.source.sha256,
      receipts: { a: {}, b: {}, c: {} } };
    else throw new Error('Unknown fixture operation');
    return { ok: true, value, raw: value };
  };
  return { pre, invoke, methods };
}

test('UTF-8 size includes accented, supplementary and JSON escaped characters', () => {
  for (const s of ['', 'abc', 'æøå', 'λ', '🎯', '\ud800', JSON.stringify({ x: 'λ\n🎯' })])
    assert.equal(utf8Bytes(s), Buffer.byteLength(s));
});

test('accounting works in an ECMAScript host without TextEncoder or Buffer', () => {
  const source = fs.readFileSync('scripts/radio_native_v2_live_probe.js', 'utf8');
  const context = vm.createContext({});
  vm.runInContext(source, context);
  assert.equal(vm.runInContext("utf8Bytes('æ🎯')", context), 6);
});

test('one inline tree, commit, update and grouped exact readback', async () => {
  const { pre, invoke, methods } = fixture();
  const { result } = await runProbe(pre, invoke, () => 0);
  assert.equal(result.status, 'PASS');
  assert.equal(result.usage.calls, 12);
  for (const method of ['create_tree', 'create_commit', 'update_ref', 'git_cat_file_batch'])
    assert.equal(methods.filter(x => x === method).length, 1);
  assert.equal(methods.includes('create_blob'), false);
  assert.equal(result.scientific_admission_authorized, false);
});

test('immutable freeze and exact tree conflicts stop before the next mutation', async () => {
  for (const fault of ['freeze', 'tree']) {
    const { pre, invoke, methods } = fixture(fault);
    const { result } = await runProbe(pre, invoke, () => 0);
    assert.equal(result.status, 'CLOSED_FAILED');
    assert.equal(methods.includes('create_commit'), false);
    assert.equal(result.update_may_have_landed, false);
  }
});

test('lost update and corrupt readback stop with no second mutation', async () => {
  for (const fault of ['lost_update', 'readback']) {
    const { pre, invoke, methods } = fixture(fault);
    const { result } = await runProbe(pre, invoke, () => 0);
    assert.equal(result.status, 'CLOSED_FAILED');
    assert.equal(result.update_may_have_landed, true);
    assert.equal(methods.filter(x => x === 'update_ref').length, 1);
    assert.equal(result.automatic_retry, false);
  }
});

test('elapsed ceiling stops before any transport operation', async () => {
  const { pre, invoke, methods } = fixture();
  let tick = 0;
  const { result } = await runProbe(pre, invoke, () => tick++ === 0 ? 0 : 181000);
  assert.equal(result.status, 'CLOSED_FAILED');
  assert.deepEqual(methods, []);
});
