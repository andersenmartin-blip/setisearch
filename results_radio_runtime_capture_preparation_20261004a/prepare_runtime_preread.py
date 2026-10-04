from pathlib import Path
import hashlib,json,os,stat
base=Path('/opt/codex/runtimes/codex-primary-runtime/dependencies/python').resolve()
stdlib=base/'lib/python3.12'
selected={str(base/'bin/python3.12'):'elf'}
for directory,dirs,names in os.walk(stdlib,followlinks=False):
 dirs[:]=sorted(x for x in dirs if x not in ('site-packages','__pycache__') and not Path(directory,x).is_symlink())
 for name in sorted(names):
  p=Path(directory,name)
  if p.is_symlink() or p.suffix in ('.pyc','.pyo') or not p.is_file():continue
  selected[str(p)]='elf' if p.suffix=='.so' else 'runtime'
for name in ('ld-linux-x86-64.so.2','libpthread.so.0','libdl.so.2','libutil.so.1','libm.so.6','librt.so.1','libc.so.6','libgcc_s.so.1','libstdc++.so.6','libz.so.1'):
 p=Path('/usr/lib/x86_64-linux-gnu',name).resolve(strict=True);selected[str(p)]='elf'
metadata=stdlib/'site-packages/numpy-2.3.5.dist-info'
for name in ('METADATA','WHEEL','RECORD'):selected[str(metadata/name)]='runtime'
loaderfiles=[Path('/etc/ld.so.cache'),Path('/etc/ld.so.conf'),Path('/etc/os-release').resolve(strict=True)]
loaderfiles.extend(sorted(Path('/etc/ld.so.conf.d').glob('*.conf')))
for p in loaderfiles:selected[str(p.resolve(strict=True))]='input'
records=[]
for path,role in sorted(selected.items()):
 p=Path(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1
  digest=hashlib.sha256();total=0
  while True:
   raw=os.read(fd,1024*1024)
   if not raw:break
   total+=len(raw);digest.update(raw)
  after=os.fstat(fd);named=p.stat(follow_symlinks=False)
  keys=('st_dev','st_ino','st_mode','st_size','st_nlink','st_mtime_ns','st_ctime_ns')
  assert all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in keys)
  assert total==before.st_size
  permissions=format(before.st_mode&0o7777,'04o');assert permissions in ('0644','0755'),(path,permissions)
  records.append({'path':path,'role':role,'bytes':total,'sha256':digest.hexdigest(),'mode':'100755' if permissions=='0755' else '100644','filesystem_mode':permissions})
 finally:os.close(fd)
missing=[str(stdlib/'site-packages'/x) for x in ('h5py','h5py-3.16.0.dist-info','hdf5plugin','hdf5plugin-7.1.0.dist-info')]
plan=json.loads(Path('results_radio_runtime_materialization_preparation_20261004a/runtime-materialization.plan.json').read_bytes())
missing += [plan['availability']['observation']['candidate_root']]
missing += [row['recorded_download_path'] for row in plan['availability']['observation']['wheels']]
identity=hashlib.sha256(b'radio-runtime-metadata-capture-20261004a:first:2026-10-04').hexdigest()
obj={'schema':'radio-runtime-metadata-prospective-preread-pins-v1','capture_identity':identity,'origin':'new read-only preparation of explicit current regular-file pin cohort; not actual capture or runtime qualification','python_path':str(base/'bin/python3.12'),'selected_files':records,'selected_file_count':len(records),'selected_file_bytes':sum(x['bytes'] for x in records),'stdlib_regular_cohort_count':746,'stdlib_cohort_selection':'all regular non-symlink files outside site-packages/cache/bytecode including four zero-byte files','numpy_scope':'three static distribution metadata files only; no package/native cohort or import','loader_paths':['/usr/lib/x86_64-linux-gnu',str(base/'lib')],'distributions':[{'name':'numpy','metadata_path':str(metadata/'METADATA'),'wheel_path':str(metadata/'WHEEL'),'record_path':str(metadata/'RECORD'),'expected_version':'2.3.5'}],'missing_paths':sorted(set(missing)),'os_release_utf8':Path('/etc/os-release').read_text(),'authority':'preread only; independently supplied expected pins; no scientific or runtime certificate'}
p=Path('results_radio_runtime_capture_preparation_20261004a/runtime-preread-pins.json');raw=(json.dumps(obj,sort_keys=True,separators=(',',':'))+'\n').encode();fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
print(json.dumps({'capture_identity':identity,'files':len(records),'selected_bytes':obj['selected_file_bytes'],'manifest_bytes':len(raw),'manifest_sha256':hashlib.sha256(raw).hexdigest(),'modes':sorted(set(x['filesystem_mode'] for x in records)),'zero_files':sum(x['bytes']==0 for x in records)}))
