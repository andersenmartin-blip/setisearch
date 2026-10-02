'use strict';

// Node-local, immutable Git metadata verification. This component has no
// connector, ref-update, object-write, network or telescope-data operation.
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { performance } = require('node:perf_hooks');

const SCHEMA = 'radio-native-v2-local-git-metadata-v1';
const REPOSITORY = 'andersenmartin-blip/setisearch';
const MIB = 1024 * 1024;
const MODES = Object.freeze({ '40000':'tree', '100644':'blob', '100755':'blob',
  '120000':'blob', '160000':'commit' });
const CONFIG_ARGS = Object.freeze(['--no-optional-locks', '--no-replace-objects',
  '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
  '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-c', 'credential.helper=',
  '-c', 'protocol.allow=never']);

function assert(ok, message) { if (!ok) throw new Error(message); }
function gitSha(value) {
  assert(typeof value === 'string' && /^[0-9a-f]{40}$/.test(value), 'Full immutable Git SHA required');
  return value;
}
function gitObjectSha(type, payload) {
  assert(['blob','tree','commit','tag'].includes(type) &&
    (Buffer.isBuffer(payload) || typeof payload === 'string'), 'Typed raw Git object required');
  const bytes = Buffer.isBuffer(payload) ? payload.length : Buffer.byteLength(payload, 'utf8');
  return crypto.createHash('sha1').update(type+' '+bytes+'\0', 'ascii').update(payload).digest('hex');
}
function safeAbsolute(value, label) {
  assert(typeof value === 'string' && path.isAbsolute(value) && value !== '/' &&
    path.normalize(value) === value && !/[\0\r\n]/.test(value), 'Canonical absolute '+label+' required');
  return value;
}
function archivePath(value) {
  assert(typeof value === 'string' && value.length <= 1024 && /^[\x20-\x7e]+$/.test(value) &&
    !value.includes('\\') && value.split('/').every(p => p && p !== '.' && p !== '..' && p !== '.git' && p.length <= 255),
    'Safe bounded ASCII archive path required');
  return value;
}
function safeEnvironment(extra) {
  const result = { PATH:'/usr/bin:/bin', LANG:'C', LC_ALL:'C', GIT_CONFIG_NOSYSTEM:'1',
    GIT_CONFIG_SYSTEM:'/dev/null', GIT_CONFIG_GLOBAL:'/dev/null',
    GIT_NO_REPLACE_OBJECTS:'1', GIT_NO_LAZY_FETCH:'1', GIT_TERMINAL_PROMPT:'0',
    GIT_OPTIONAL_LOCKS:'0' };
  if (extra !== undefined) {
    assert(extra && typeof extra === 'object' && !Array.isArray(extra), 'Explicit safe environment map required');
    // No caller-controlled Git, path, credential, loader or object-directory
    // variables cross this metadata boundary. Only a locale can be supplied.
    for (const [key,value] of Object.entries(extra)) {
      assert(['LANG','LC_ALL'].includes(key) && value === 'C', 'Unsafe local Git environment override');
      result[key] = value;
    }
  }
  return Object.freeze(result);
}
function metadataPins(repoPath) {
  const gitDir = path.join(repoPath,'.git'), objects = path.join(gitDir,'objects');
  for (const directory of [gitDir,objects]) assert(fs.existsSync(directory) &&
    fs.realpathSync(directory) === directory && fs.statSync(directory).isDirectory(),
    'Unaliased ordinary repository Git metadata directories required');
  assert(!fs.existsSync(path.join(gitDir,'commondir')), 'External shared Git metadata is unqualified');
  const pins = [];
  for (const name of ['config','config.worktree','objects/info/alternates','objects/info/http-alternates']) {
    const file = path.join(gitDir,name);
    if (!fs.existsSync(file)) { pins.push({path:'.git/'+name,exists:false}); continue; }
    assert(fs.realpathSync(file) === file && fs.statSync(file).isFile() && fs.statSync(file).size <= 65536,
      'Bounded ordinary local Git configuration metadata required');
    const raw = fs.readFileSync(file);
    if (name.startsWith('objects/')) assert(raw.length === 0, 'External Git object alternates are unqualified');
    else {
      const text = new TextDecoder('utf-8',{fatal:true}).decode(raw);
      assert(!/^\s*\[\s*include(?:if)?(?:\s|\])/im.test(text), 'External Git configuration includes are unqualified');
    }
    pins.push({path:'.git/'+name,exists:true,bytes:raw.length,
      sha256:crypto.createHash('sha256').update(raw).digest('hex')});
  }
  return pins;
}
function decodeName(raw) {
  const name = new TextDecoder('utf-8', {fatal:true}).decode(raw);
  assert(name && name !== '.' && name !== '..' && !/[\0/]/.test(name), 'Malformed immutable tree name');
  return name;
}
function parseTree(raw) {
  const entries = new Map();
  let at = 0, previous = null;
  while (at < raw.length) {
    const space = raw.indexOf(32, at), nul = raw.indexOf(0, space+1);
    assert(space > at && nul > space && nul+21 <= raw.length, 'Malformed raw Git tree framing');
    const mode = raw.subarray(at, space).toString('ascii'), nameBytes = raw.subarray(space+1, nul);
    assert(Object.hasOwn(MODES, mode), 'Unsupported immutable tree mode');
    const name = decodeName(nameBytes), sha = raw.subarray(nul+1, nul+21).toString('hex');
    const sortBytes = mode === '40000' ? Buffer.concat([nameBytes, Buffer.from('/')]) : nameBytes;
    assert(!entries.has(name) && (previous === null || Buffer.compare(previous, sortBytes) < 0),
      'Immutable tree duplicate or ordering differs');
    entries.set(name, {name, nameBytes:Buffer.from(nameBytes), mode, type:MODES[mode], sha});
    previous = sortBytes; at = nul+21;
  }
  return entries;
}
function serializeTree(entries) {
  const sorted = [...entries.values()].sort((a,b) => Buffer.compare(
    a.mode === '40000' ? Buffer.concat([a.nameBytes, Buffer.from('/')]) : a.nameBytes,
    b.mode === '40000' ? Buffer.concat([b.nameBytes, Buffer.from('/')]) : b.nameBytes));
  const rows = sorted.map(row => Buffer.concat([Buffer.from(row.mode+' ', 'ascii'), row.nameBytes,
    Buffer.from([0]), Buffer.from(row.sha, 'hex')]));
  return Buffer.concat(rows);
}
function parseCommit(raw, sha) {
  const end = raw.indexOf(Buffer.from('\n\n'));
  assert(end > 0, 'Malformed immutable commit header');
  const headers = new TextDecoder('utf-8', {fatal:true}).decode(raw.subarray(0, end)).split('\n');
  assert(/^tree [0-9a-f]{40}$/.test(headers[0]), 'Immutable commit root tree absent');
  const parents = [];
  let previous = 'tree';
  for (const line of headers.slice(1)) {
    if (line.startsWith(' ')) { assert(previous !== 'tree' && previous !== 'parent', 'Malformed commit continuation'); continue; }
    const match = /^([a-z][a-z0-9-]*) (.*)$/.exec(line);
    assert(match && match[1] !== 'tree', 'Malformed or repeated commit header');
    previous = match[1];
    if (previous === 'parent') parents.push({sha:gitSha(match[2])});
  }
  return {sha, tree:{sha:headers[0].slice(5)}, parents};
}

class LocalGit {
  constructor(options) {
    assert(options && typeof options === 'object' && !Array.isArray(options), 'Local Git options required');
    this.repoPath = safeAbsolute(options.repoPath, 'repository path');
    this.gitPath = safeAbsolute(options.gitPath === undefined ? '/usr/bin/git' : options.gitPath, 'Git executable');
    assert(fs.realpathSync(this.repoPath) === this.repoPath && fs.statSync(this.repoPath).isDirectory(),
      'Repository path must be an existing unaliased directory');
    assert(fs.realpathSync(this.gitPath) === this.gitPath && fs.statSync(this.gitPath).isFile(),
      'Git executable must be an existing unaliased file');
    this.timeoutMs = options.timeoutMs === undefined ? 30000 : options.timeoutMs;
    this.maxObjectBytes = options.maxObjectBytes === undefined ? 8*MIB : options.maxObjectBytes;
    this.maxCacheBytes = options.maxCacheBytes === undefined ? 32*MIB : options.maxCacheBytes;
    assert(Number.isSafeInteger(this.timeoutMs) && this.timeoutMs > 0 && this.timeoutMs <= 120000 &&
      Number.isSafeInteger(this.maxObjectBytes) && this.maxObjectBytes > 0 && this.maxObjectBytes <= 8*MIB &&
      Number.isSafeInteger(this.maxCacheBytes) && this.maxCacheBytes > 0 && this.maxCacheBytes <= 32*MIB,
      'Bounded local Git timeout, metadata and cumulative cache limits required');
    assert(options.deadline === undefined || typeof options.deadline === 'function', 'Local Git deadline callback required');
    this.deadline = options.deadline;
    this.deadlineEnds = [];
    this.env = safeEnvironment(options.envsafe);
    this.metadataPins = metadataPins(this.repoPath);
    this.objects = new Map();
    this.cacheBytes = 0;
    this.usage = {local_read_operations:0, local_read_bytes:0, computed_tree_objects:0,
      computed_blob_bytes:0, elapsed_ms:0};
  }
  _remaining() {
    let value = this.deadline ? this.deadline() : this.timeoutMs;
    assert(Number.isFinite(value) && value > 0, 'Local immutable metadata deadline exhausted');
    const now = performance.now();
    for (const end of this.deadlineEnds) value = Math.min(value,end-now);
    assert(Number.isFinite(value) && value > 0, 'Local immutable metadata deadline exhausted');
    return Math.max(1, Math.min(this.timeoutMs, Math.floor(value)));
  }
  withDeadline(milliseconds, fn) {
    assert(Number.isFinite(milliseconds) && milliseconds > 0 &&
      typeof fn === 'function', 'Finite positive synchronous local metadata deadline required');
    const end = performance.now()+milliseconds;
    assert(Number.isFinite(end), 'Finite local metadata deadline endpoint required');
    this.deadlineEnds.push(end);
    try {
      this._remaining();
      const result = fn();
      assert(!result || typeof result.then !== 'function', 'Synchronous local metadata deadline callback required');
      this._remaining();
      return result;
    } finally { this.deadlineEnds.pop(); }
  }
  _object(sha, expectedType) {
    gitSha(sha); this._remaining();
    assert(JSON.stringify(metadataPins(this.repoPath)) === JSON.stringify(this.metadataPins),
      'Pinned local Git configuration metadata drifted');
    if (this.objects.has(sha)) {
      const found = this.objects.get(sha);
      assert(found.type === expectedType && gitObjectSha(found.type, found.raw) === sha, 'Cached immutable metadata differs');
      return found.raw;
    }
    const started = Date.now();
    this.usage.local_read_operations++;
    const child = spawnSync(this.gitPath, [...CONFIG_ARGS, '-C', this.repoPath, 'cat-file', '--batch'],
      {input:sha+'\n', env:this.env, timeout:this._remaining(), maxBuffer:this.maxObjectBytes+1024, encoding:null});
    this.usage.elapsed_ms += Date.now()-started;
    const output = child.stdout || Buffer.alloc(0);
    this.usage.local_read_bytes += output.length;
    assert(!child.error && child.status === 0 && child.signal === null, 'Local immutable Git read failed or exceeded its bound');
    const newline = output.indexOf(10);
    assert(newline > 0, 'Local immutable Git framing absent');
    const header = output.subarray(0, newline).toString('ascii');
    const match = /^([0-9a-f]{40}) (tree|commit) ([0-9]+)$/.exec(header);
    assert(match && match[1] === sha && match[2] === expectedType, 'Local immutable metadata identity/type absent');
    const bytes = Number(match[3]);
    assert(Number.isSafeInteger(bytes) && bytes <= this.maxObjectBytes &&
      output.length === newline+1+bytes+1 && output[output.length-1] === 10, 'Local immutable metadata size/framing differs');
    const raw = Buffer.from(output.subarray(newline+1, newline+1+bytes));
    assert(gitObjectSha(expectedType, raw) === sha, 'Raw immutable Git object hash differs');
    assert(JSON.stringify(metadataPins(this.repoPath)) === JSON.stringify(this.metadataPins),
      'Pinned local Git configuration metadata drifted');
    this._remaining();
    assert(this.cacheBytes+raw.length <= this.maxCacheBytes, 'Cumulative immutable metadata cache cap exhausted');
    this.objects.set(sha, {type:expectedType, raw}); this.cacheBytes += raw.length;
    return raw;
  }
  immutableRead(url) {
    const match = typeof url === 'string' && new RegExp('^https://api\\.github\\.com/repos/'+REPOSITORY+
      '/git/(commits|trees)/([0-9a-f]{40})$').exec(url);
    assert(match, 'Exact repository immutable commit/tree URL required');
    const sha = match[2];
    if (match[1] === 'commits') return parseCommit(this._object(sha, 'commit'), sha);
    const entries = parseTree(this._object(sha, 'tree'));
    return {sha, tree:[...entries.values()].map(row => ({path:row.name,
      mode:row.mode === '40000' ? '040000' : row.mode, type:row.type, sha:row.sha})), truncated:false};
  }
  expectedTree(parentTree, elements) {
    gitSha(parentTree); this._remaining();
    assert(Array.isArray(elements) && elements.length > 0 && elements.length <= 28, 'Bounded nonempty inline tree delta required');
    const validated = [], seen = new Set();
    let total = 0;
    for (const row of elements) {
      assert(row && typeof row === 'object' && !Array.isArray(row) &&
        Object.keys(row).sort().join(',') === 'content,mode,path,type', 'Exact inline tree fields required');
      archivePath(row.path);
      assert(!seen.has(row.path) && row.mode === '100644' && row.type === 'blob' &&
        typeof row.content === 'string' && /^[\x00-\x7f]*$/.test(row.content), 'Exact ASCII inline blob delta required');
      seen.add(row.path); total += row.content.length;
      assert(total <= 36*MIB, 'Inline tree bytes exceed frozen archive cap');
      validated.push({parts:row.path.split('/'), sha:gitObjectSha('blob', row.content)});
    }
    // A file cannot simultaneously be an ancestor of another supplied file.
    for (const row of validated) for (let n=1;n<row.parts.length;n++)
      assert(!seen.has(row.parts.slice(0,n).join('/')), 'Conflicting inline archive paths');
    const makeNode = sha => ({entries:sha ? parseTree(this._object(sha, 'tree')) : new Map(), children:new Map()});
    const root = makeNode(parentTree);
    for (const row of validated) {
      this._remaining(); let node = root;
      for (const part of row.parts.slice(0,-1)) {
        const old = node.entries.get(part);
        assert(!old || old.type === 'tree', 'Inline path traverses an existing non-tree');
        if (!node.children.has(part)) node.children.set(part, makeNode(old ? old.sha : null));
        node = node.children.get(part);
      }
      const name = row.parts[row.parts.length-1], old = node.entries.get(name);
      assert(!old || old.type !== 'tree', 'Inline blob cannot overwrite an existing subtree');
      node.entries.set(name, {name, nameBytes:Buffer.from(name, 'ascii'), mode:'100644', type:'blob', sha:row.sha});
    }
    const computed = new Map();
    let newCacheBytes = 0;
    const finish = node => {
      this._remaining();
      for (const [name, child] of node.children) node.entries.set(name,
        {name, nameBytes:Buffer.from(name, 'utf8'), mode:'40000', type:'tree', sha:finish(child)});
      const raw = serializeTree(node.entries);
      assert(raw.length <= this.maxObjectBytes, 'Computed immutable tree metadata exceeds cap');
      const sha = gitObjectSha('tree', raw);
      if (!this.objects.has(sha) && !computed.has(sha)) newCacheBytes += raw.length;
      assert(this.cacheBytes+newCacheBytes <= this.maxCacheBytes, 'Cumulative computed metadata cache cap exhausted');
      computed.set(sha, {type:'tree', raw}); return sha;
    };
    const sha = finish(root); this._remaining();
    for (const [key, value] of computed) this.objects.set(key, value);
    this.cacheBytes += newCacheBytes;
    this.usage.computed_tree_objects += computed.size;
    this.usage.computed_blob_bytes += total;
    return sha;
  }
  snapshot() {
    return {schema:SCHEMA, ...this.usage, cache_objects:this.objects.size, cache_bytes:this.cacheBytes,
      cache_limit_bytes:this.maxCacheBytes, object_limit_bytes:this.maxObjectBytes,
      git_metadata_inputs:this.metadataPins.map(pin => ({...pin})),
      local_metadata_only:true, network_reads:0, ref_reads:0, object_writes:0,
      replacement_objects:false, lazy_fetch:false, actual_tool_calls:0};
  }
}

module.exports = {LocalGit, gitObjectSha, SCHEMA};
