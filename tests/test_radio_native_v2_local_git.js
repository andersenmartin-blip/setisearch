'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const zlib = require('node:zlib');
const {spawnSync} = require('node:child_process');
const {performance} = require('node:perf_hooks');
const {LocalGit, gitObjectSha} = require('../scripts/radio_native_v2_local_git.js');

const BASE = 'https://api.github.com/repos/andersenmartin-blip/setisearch/git/';
function fixture(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'seti-local-git-'));
  t.after(() => fs.rmSync(root, {recursive:true, force:true}));
  const git = (...args) => {
    const run = spawnSync('/usr/bin/git', ['--no-replace-objects', '-C',root,...args],
      {encoding:'utf8', env:{PATH:'/usr/bin:/bin', LANG:'C', GIT_CONFIG_NOSYSTEM:'1',
        GIT_CONFIG_GLOBAL:'/dev/null', GIT_AUTHOR_NAME:'Fixture', GIT_AUTHOR_EMAIL:'fixture@example.invalid',
        GIT_COMMITTER_NAME:'Fixture', GIT_COMMITTER_EMAIL:'fixture@example.invalid'}});
    assert.equal(run.status,0,run.stderr); return run.stdout.trim();
  };
  const write = (name, content) => {const file = path.join(root,name); fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,content);};
  git('init','--quiet');
  write('keep.txt','Unchanged\n'); write('archive/old.txt','Old\n');
  write('archive/sub/item.txt','Existing\n'); write('archive.z','Root ordering\n');
  write('unicode-æ.txt','Preserved UTF8 name\n');
  git('add','.'); git('commit','--quiet','-m','Synthetic metadata fixture');
  return {root,git,write,commit:git('rev-parse','HEAD'),tree:git('rev-parse','HEAD^{tree}')};
}
function row(name, content) {return {path:name,mode:'100644',type:'blob',content};}

test('immutable commit and tree metadata authenticate raw object bytes and cache reads', t => {
  const f = fixture(t), local = new LocalGit({repoPath:f.root});
  const commit = local.immutableRead(BASE+'commits/'+f.commit);
  assert.deepEqual(commit,{sha:f.commit,tree:{sha:f.tree},parents:[]});
  const tree = local.immutableRead(BASE+'trees/'+f.tree);
  assert.equal(tree.sha,f.tree); assert.equal(tree.truncated,false);
  assert.equal(tree.tree.find(x => x.path === 'archive').mode,'040000');
  assert.equal(tree.tree.find(x => x.path === 'unicode-æ.txt').type,'blob');
  tree.tree[0].sha = 'f'.repeat(40);
  assert.notEqual(local.immutableRead(BASE+'trees/'+f.tree).tree[0].sha,'f'.repeat(40));
  assert.equal(local.snapshot().local_read_operations,2);
  assert.equal(local.snapshot().actual_tool_calls,0);
  assert.equal(local.snapshot().object_writes,0);
});

test('independent expected tree retains unrelated entries and exposes computed descendants', t => {
  const f = fixture(t), local = new LocalGit({repoPath:f.root});
  const changes = [row('archive/old.txt','Replaced\n'), row('archive/sub/fresh.txt','New nested\n'),
    row('new/path/value.txt','New directory\n')];
  const actual = local.expectedTree(f.tree,changes);
  for (const x of changes) f.write(x.path,x.content);
  f.git('add','.');
  assert.equal(actual,f.git('write-tree'));
  const root = local.immutableRead(BASE+'trees/'+actual);
  const archive = root.tree.find(x => x.path === 'archive');
  const subtree = local.immutableRead(BASE+'trees/'+archive.sha);
  assert.ok(subtree.tree.some(x => x.path === 'sub' && x.type === 'tree'));
  assert.equal(local.snapshot().local_read_operations,3);
  assert.equal(local.snapshot().computed_tree_objects,5);
  assert.equal(local.snapshot().computed_blob_bytes,changes.reduce((n,x) => n+x.content.length,0));
});

test('unchanged delta produces exact old root without altering Git objects or index', t => {
  const f = fixture(t), local = new LocalGit({repoPath:f.root});
  const before = f.git('write-tree');
  assert.equal(local.expectedTree(f.tree,[row('archive/old.txt','Old\n')]),f.tree);
  assert.equal(f.git('write-tree'),before);
  assert.equal(f.git('status','--porcelain'),'');
});

test('replacement refs do not change authenticated commit metadata', t => {
  const f = fixture(t);
  f.write('keep.txt','Replacement commit content\n'); f.git('add','.');
  f.git('commit','--quiet','-m','Replacement fixture');
  const replacement = f.git('rev-parse','HEAD');
  f.git('replace',f.commit,replacement);
  const local = new LocalGit({repoPath:f.root});
  assert.equal(local.immutableRead(BASE+'commits/'+f.commit).tree.sha,f.tree);
  assert.equal(local.snapshot().replacement_objects,false);
});

test('missing promisor objects fail locally without invoking a remote helper', t => {
  const f = fixture(t), marker = path.join(f.root,'forbidden-network-marker');
  const helper = path.join(f.root,'forbidden-fetch.sh');
  fs.writeFileSync(helper,'#!/bin/sh\ntouch '+marker+'\nexit 1\n',{mode:0o700});
  f.git('config','extensions.partialClone','origin');
  f.git('config','remote.origin.promisor','true');
  f.git('config','remote.origin.url','ext::'+helper);
  const local = new LocalGit({repoPath:f.root});
  assert.throws(() => local.immutableRead(BASE+'trees/'+'f'.repeat(40)),/identity\/type absent|read failed/);
  assert.equal(fs.existsSync(marker),false);
  assert.equal(local.snapshot().lazy_fetch,false);
  assert.equal(local.snapshot().network_reads,0);
});

test('raw tree stored beneath a false SHA is rejected independently of Git framing', t => {
  const f = fixture(t), falseSha = 'a'.repeat(40);
  const blob = f.git('rev-parse','HEAD:keep.txt');
  const raw = Buffer.concat([Buffer.from('100644 fake\0'),Buffer.from(blob,'hex')]);
  const target = path.join(f.root,'.git','objects',falseSha.slice(0,2),falseSha.slice(2));
  fs.mkdirSync(path.dirname(target),{recursive:true});
  fs.writeFileSync(target,zlib.deflateSync(Buffer.concat([Buffer.from('tree '+raw.length+'\0'),raw])));
  const local = new LocalGit({repoPath:f.root});
  assert.throws(() => local.immutableRead(BASE+'trees/'+falseSha),/object hash differs/);
});

test('blob hash matches Git for ASCII data without holding a second full content buffer', t => {
  const f = fixture(t), content = 'line\0with\nbytes\t';
  f.write('hash-fixture',content);
  assert.equal(gitObjectSha('blob',content),f.git('hash-object','hash-fixture'));
  assert.equal(gitObjectSha('blob',Buffer.from(content)),gitObjectSha('blob',content));
});

test('unsafe URLs, SHAs, delta paths, modes, fields and source content are rejected', t => {
  const f = fixture(t), local = new LocalGit({repoPath:f.root});
  for (const url of [BASE+'ref/heads/main',BASE+'trees/HEAD',BASE+'trees/'+f.tree+'?recursive=1',
    BASE.replace('andersenmartin-blip','other')+'trees/'+f.tree])
    assert.throws(() => local.immutableRead(url),/immutable commit\/tree URL/);
  assert.throws(() => local.expectedTree('HEAD',[row('a','b')]),/Full immutable/);
  for (const name of ['../x','a/../x','/x','a//b','a\\b','a/.git/object','bad\nname'])
    assert.throws(() => local.expectedTree(f.tree,[row(name,'x')]),/archive path/);
  for (const change of [{...row('a','x'),mode:'100755'}, {...row('a','x'),type:'tree'},
    {...row('a','x'),sha:'a'.repeat(40)}, row('a','æ')])
    assert.throws(() => local.expectedTree(f.tree,[change]),/fields|ASCII/);
  assert.throws(() => local.expectedTree(f.tree,[row('a','x'),row('a','y')]),/ASCII/);
  assert.throws(() => local.expectedTree(f.tree,[row('a','x'),row('a/b','y')]),/Conflicting/);
  assert.throws(() => local.expectedTree(f.tree,[row('keep.txt/x','y')]),/non-tree/);
  assert.throws(() => local.expectedTree(f.tree,[row('archive','y')]),/subtree/);
});

test('environment, metadata byte limit and monotonic external deadline are bounded', t => {
  const f = fixture(t);
  for (const envsafe of [{PATH:'/tmp'}, {GIT_CONFIG_GLOBAL:'/tmp/config'},
    {GIT_ALTERNATE_OBJECT_DIRECTORIES:'/tmp'}, {LD_PRELOAD:'/tmp/plugin'}])
    assert.throws(() => new LocalGit({repoPath:f.root,envsafe}),/Unsafe/);
  assert.throws(() => new LocalGit({repoPath:f.root,timeoutMs:120001}),/Bounded/);
  assert.throws(() => new LocalGit({repoPath:f.root,maxObjectBytes:8*1024*1024+1}),/Bounded/);
  assert.throws(() => new LocalGit({repoPath:f.root,maxCacheBytes:32*1024*1024+1}),/Bounded/);
  const bounded = new LocalGit({repoPath:f.root,maxObjectBytes:10});
  assert.throws(() => bounded.immutableRead(BASE+'trees/'+f.tree),/size\/framing differs|read failed/);
  let remaining = 1000;
  const timed = new LocalGit({repoPath:f.root,deadline:() => remaining,envsafe:{LANG:'C'}});
  timed.immutableRead(BASE+'trees/'+f.tree); remaining = 0;
  assert.throws(() => timed.immutableRead(BASE+'trees/'+f.tree),/deadline exhausted/);
});

test('cumulative cached raw metadata has a separate finite cap', t => {
  const f = fixture(t), rawBytes = Number(f.git('cat-file','-s',f.tree));
  const local = new LocalGit({repoPath:f.root,maxCacheBytes:rawBytes});
  local.immutableRead(BASE+'trees/'+f.tree);
  assert.equal(local.snapshot().cache_bytes,rawBytes);
  assert.throws(() => local.immutableRead(BASE+'commits/'+f.commit),/cache cap exhausted/);
  assert.equal(local.snapshot().cache_bytes,rawBytes);
  assert.throws(() => local.expectedTree(f.tree,[row('fresh','New file\n')]),/cache cap exhausted/);
  assert.equal(local.snapshot().cache_bytes,rawBytes);
});

test('local configuration inputs are fingerprinted and include, alternate and drift paths refuse', t => {
  const f = fixture(t), local = new LocalGit({repoPath:f.root});
  const pins = local.snapshot().git_metadata_inputs;
  assert.equal(pins.length,4);
  assert.match(pins.find(x => x.path === '.git/config').sha256,/^[0-9a-f]{64}$/);
  pins[0].sha256 = 'f'.repeat(64);
  assert.notEqual(local.snapshot().git_metadata_inputs[0].sha256,'f'.repeat(64));
  f.git('config','core.filemode','false');
  assert.throws(() => local.immutableRead(BASE+'trees/'+f.tree),/metadata drifted/);
  const include = path.join(f.root,'.git','config');
  fs.appendFileSync(include,'\n[includeIf "gitdir:/anything"]\n path = /unqualified/file\n');
  assert.throws(() => new LocalGit({repoPath:f.root}),/configuration includes/);
  fs.writeFileSync(include,'[core]\n repositoryformatversion = 0\n bare = false\n');
  const alternates = path.join(f.root,'.git','objects','info','alternates');
  fs.writeFileSync(alternates,'/unqualified/object/path\n');
  assert.throws(() => new LocalGit({repoPath:f.root}),/object alternates/);
});

test('synchronous nested deadline contexts shorten outer time and restore after failure', t => {
  const f = fixture(t), local = new LocalGit({repoPath:f.root});
  assert.equal(local.withDeadline(1000, () => local.withDeadline(2000,
    () => local.immutableRead(BASE+'trees/'+f.tree).sha)),f.tree);
  assert.throws(() => local.withDeadline(5, () => local.withDeadline(1000, () => {
    const until = performance.now()+10;
    while (performance.now() < until) { /* controlled deadline fixture */ }
    return local.immutableRead(BASE+'trees/'+f.tree);
  })),/deadline exhausted/);
  assert.equal(local.withDeadline(1000, () => local.immutableRead(BASE+'trees/'+f.tree).sha),f.tree);
  for (const milliseconds of [0,-1,Infinity,NaN])
    assert.throws(() => local.withDeadline(milliseconds,()=>null),/Finite positive/);
  assert.throws(() => local.withDeadline(1000,()=>Promise.resolve(null)),/Synchronous/);
});
