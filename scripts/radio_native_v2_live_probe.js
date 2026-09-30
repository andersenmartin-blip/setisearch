// A bounded one-shot probe. The host supplies GitHub and grouped Git adapters.
// Byte accounting uses only standard ECMAScript; no TextEncoder is required.
function utf8Bytes(value) {
  const text = typeof value === 'string' ? value : JSON.stringify(value);
  let size = 0;
  for (const char of text) {
    const cp = char.codePointAt(0);
    size += cp <= 0x7f ? 1 : cp <= 0x7ff ? 2 : cp <= 0xffff ? 3 : 4;
  }
  return size;
}

async function runProbe(pre, invoke, clock = Date.now) {
  const f = pre.freeze, repo = f.repository, branch = f.branch;
  const started = clock(), events = [];
  let calls = 0, requestBytes = 0, responseBytes = 0;
  let updateAttempted = false, candidate = null;
  const assert = (ok, reason) => { if (!ok) throw new Error(reason); };
  const usage = () => ({ calls, request_bytes: requestBytes,
    response_bytes: responseBytes, elapsed_seconds: (clock() - started) / 1000 });
  const check = () => {
    assert(calls <= f.limits.calls && requestBytes <= f.limits.request_bytes &&
      responseBytes <= f.limits.response_bytes &&
      usage().elapsed_seconds <= f.limits.seconds, 'Frozen probe limit exhausted');
  };
  async function call(method, params) {
    check();
    const request = utf8Bytes(params);
    assert(calls < f.limits.calls && requestBytes + request <= f.limits.request_bytes,
      'Prospective call/request reservation failed');
    calls++; requestBytes += request;
    const begin = clock();
    try {
      const reply = await invoke(method, params);
      responseBytes += utf8Bytes(reply.raw);
      events.push({ sequence: calls, method, params, raw_result: reply.raw,
        seconds: (clock() - begin) / 1000 });
      check();
      assert(reply.ok === true && reply.value && typeof reply.value === 'object',
        'Transport response unconfirmed');
      return reply.value;
    } catch (error) {
      events.push({ sequence: calls, method, error: String(error) });
      throw error;
    }
  }
  const get = path => call('fetch', {
    url: 'https://api.github.com/repos/' + repo + '/git/' + path });
  try {
    assert(repo === 'andersenmartin-blip/setisearch' && branch === 'm43-support-qualification',
      'Destination differs');
    assert(f.automatic_retry === false && f.force === false && f.rng_authorized === false &&
      f.case_reservation_authorized === false && f.scientific_admission_authorized === false,
      'Exact engineering-only permissions required');
    assert(Object.keys(f.files).length === 3 && f.limits.calls === 16 &&
      f.limits.request_bytes === 65536 && f.limits.response_bytes === 1048576 &&
      f.limits.seconds === 180 && f.limits.files === 3 &&
      f.limits.mutation_commits === 1 && f.limits.ref_updates === 1 &&
      f.limits.stored_bytes === 4096, 'Exact prospective limits required');
    const frozen = await call('fetch_file', { repository_full_name: repo,
      ref: pre.parent, path: pre.freeze_path, encoding: 'utf-8' });
    assert(frozen.content === pre.freeze_utf8, 'Independent immutable freeze differs');
    const parent = await get('commits/' + pre.parent);
    assert(parent.sha === pre.parent && parent.tree.sha === pre.parent_tree,
      'Parent commit/tree differs');
    const head = await get('ref/heads/' + branch);
    assert(head.object.sha === pre.parent, 'Initial head conflict');
    const elements = Object.entries(f.files).sort().map(([path, row]) => ({ path,
      mode: '100644', type: 'blob', content: row.content_utf8 }));
    const tree = await call('create_tree', { repository_full_name: repo,
      base_tree_sha: pre.parent_tree, tree_elements: elements });
    assert(tree.sha === pre.expected_tree, 'Candidate exact tree delta differs');
    const made = await call('create_commit', { repository_full_name: repo,
      parent_sha: pre.parent, tree_sha: tree.sha,
      message: 'Native v2 broker ' + pre.identity + ': frozen inline-tree probe' });
    candidate = made.sha;
    assert(/^[0-9a-f]{40}$/.test(candidate), 'Candidate SHA missing');
    const candidateCommit = await get('commits/' + candidate);
    const correctCommit = row => row.tree.sha === tree.sha &&
      row.parents.length === 1 && row.parents[0].sha === pre.parent;
    assert(correctCommit(candidateCommit), 'Candidate commit parent/tree differs');
    const late = await get('ref/heads/' + branch);
    assert(late.object.sha === pre.parent, 'Late head conflict');
    updateAttempted = true;
    const updated = await call('update_ref', { repository_full_name: repo,
      branch_name: branch, sha: candidate, force: false });
    assert(updated.success === true, 'Unconfirmed update result');
    const landed = await get('commits/' + candidate);
    assert(correctCommit(landed), 'Landed immutable commit differs');
    await call('git_fetch', { commit: candidate });
    const verification = await call('git_cat_file_batch', { commit: candidate,
      freeze_path: pre.freeze_path, paths: Object.keys(f.files).sort() });
    assert(verification.exact_restoration === true && verification.single_cat_file_batch === true &&
      verification.source_sha256 === f.source.sha256 && verification.source_bytes === f.source.bytes &&
      verification.stored_bytes <= f.limits.stored_bytes &&
      Object.keys(verification.receipts).length === 3, 'Grouped restoration differs');
    const finalHead = await get('ref/heads/' + branch);
    assert(finalHead.object.sha === candidate, 'Post-publication head differs');
    check();
    return { result: { schema: 'radio-native-v2-inline-live-probe-result-v1', status: 'PASS',
      identity: pre.identity, parent: pre.parent, parent_tree: pre.parent_tree,
      freeze_sha256: pre.freeze_sha256, commit: candidate, tree: tree.sha,
      exact_tree_delta_verified: true, files: 3, create_blob_calls: 0,
      inline_tree_calls: 1, mutation_commits: 1, ref_updates: 1,
      ...verification, usage: usage(), limits: f.limits, rng_draws: 0,
      telescope_reads: 0, case_reservations: 0, automatic_retry: false,
      scientific_admission_authorized: false }, events };
  } catch (error) {
    return { result: { schema: 'radio-native-v2-inline-live-probe-result-v1',
      status: 'CLOSED_FAILED', identity: pre.identity, error: String(error),
      parent: pre.parent, candidate, update_may_have_landed: updateAttempted,
      usage: usage(), limits: f.limits, automatic_retry: false,
      scientific_admission_authorized: false }, events };
  }
}

if (typeof module !== 'undefined') module.exports = { utf8Bytes, runProbe };
