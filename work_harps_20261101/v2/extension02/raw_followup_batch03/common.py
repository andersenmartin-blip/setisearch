"""Integrity helpers; only this new follow-up directory is writable."""
from pathlib import Path
import csv,datetime,hashlib,json,re,sys
sys.dont_write_bytecode=True
OUT=Path(__file__).resolve().parent;EXT=OUT.parent;BASE=EXT.parents[1]
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(name,value):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def read(name):return json.loads((OUT/name).read_text())
def csvrows(path):
 with Path(path).open(newline='')as f:return list(csv.DictReader(f))
def csvout(name,rows):
 keys=list(dict.fromkeys(k for r in rows for k in r))or['status']
 with (OUT/name).open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
def require(ok,msg):
 if not ok:raise RuntimeError(msg)
def verify_plan():
 p=read('PLAN.json')
 for name,h in p['immutable_scope_hashes'].items():require(sha(EXT/name)==h,'Changed original scope '+name)
 return p
def verify_freeze():
 f=read('FOLLOWUP_FREEZE.json');require(f['status']=='READY_FOR_ROOT_PUBLICATION_VERIFICATION','Incorrect follow-up freeze state')
 for rel,h in f['source_hashes'].items():require(sha(BASE/rel)==h,'Changed frozen input/code '+rel)
 return f
def publication(commit,digest):
 require(bool(re.fullmatch('[0-9a-f]{40}',commit or'')),'Root must supply full verified published commit')
 require(digest==sha(OUT/'FOLLOWUP_FREEZE.json'),'Published freeze SHA mismatch')
 return dict(verified_utc=now(),commit=commit,freeze_sha256=digest,publication_url='https://github.com/andersenmartin-blip/setisearch/commit/'+commit,responsibility='Root must independently verify remote code, plan and selection before invoking download.')

def verify_native_identity(header,member_name,job,science_header):
 import math
 require(Path(member_name).name==job['raw_id']+'_e2ds_A.fits','Native TAR member raw-parent identity mismatch')
 require(header.get('INSTRUME')=='HARPS','Native instrument mismatch')
 require(header.get('DATE-OBS')==job['source_date_obs'],'Native DATE mismatch')
 normalize=lambda value:re.sub('[^A-Z0-9]','',str(value).upper())
 require(normalize(header.get('OBJECT',''))==normalize(science_header['OBJECT'])and bool(normalize(science_header['OBJECT'])),'Native target mismatch')
 a=float(header['ESO DRS BERV']);b=float(science_header['HIERARCH ESO DRS BERV'])
 require(math.isfinite(a)and math.isfinite(b)and abs(a-b)<1e-8,'Native/science BERV mismatch')
 return True
