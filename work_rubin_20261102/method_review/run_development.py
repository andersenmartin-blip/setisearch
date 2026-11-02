"""Run frozen detector on the separate20-object development sample only."""
from pathlib import Path
import json, hashlib, datetime, sys
import detector
HERE=Path(__file__).resolve().parent
ACCESS=HERE.parent/'access_pilot'

def dump(name,obj):
 (HERE/name).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

def inputs():
 freeze=detector.read(ACCESS/'DEVELOPMENT_FREEZE.json')
 ids=set(freeze['selected_ids'])
 source=detector.merge_supplement(detector.read(ACCESS/'raw/development_sources.json'),detector.read(ACCESS/'metadata/development_quality_supplement.json'))
 forced=detector.read(ACCESS/'raw/development_forced.json')
 assert all(r['r:diaObjectId']in ids for r in source+forced)
 return {'sources':source,'forced':forced}

def main():
 cfg=json.loads((HERE/'CONFIG.json').read_text())
 summaries={}
 for stream,rows in inputs().items():
  normal,duplicates=detector.normalize(rows,stream,cfg)
  scored=detector.score(normal,cfg)
  dump('DEVELOPMENT_'+stream.upper()+'_NORMALIZED.json',normal)
  dump('DEVELOPMENT_'+stream.upper()+'_SCORED.json',scored)
  dump('DEVELOPMENT_'+stream.upper()+'_DUPLICATES.json',duplicates)
  summaries[stream]=detector.summarize(normal,scored,duplicates)
 dump('DEVELOPMENT_SUMMARY.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'DEVELOPMENT_ONLY_ARCHIVAL_BASELINE_SCREEN','main_objects_read':0,'config_sha256':detector.sha(HERE/'CONFIG.json'),'detector_sha256':detector.sha(HERE/'detector.py'),'streams':summaries})
 print(json.dumps(summaries,indent=2))
if __name__=='__main__':main()
