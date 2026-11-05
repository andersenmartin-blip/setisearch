"""Apply the recorded post-run prose formatting; scientific outputs stay exact."""
from pathlib import Path
import re,json,hashlib
ROOT=Path(__file__).resolve().parents[2];PHASE=Path(__file__).resolve().parent.parent
def format_prose(s):
 s=re.sub(r'(?<=[A-Za-z])(?=\d)',' ',s)
 s=re.sub(r'(?<=\d)(?=[A-Za-z])',' ',s)
 s=re.sub(r'\bC (\d{3})\b',r'C\1',s);s=re.sub(r'\bR (\d{3})\b',r'R\1',s)
 s=s.replace('V 2 E 2-','V2E2-').replace('HD 126093','HD126093').replace('NPZcontainers','NPZ containers').replace('airÅ','air Å')
 s=s.replace('work_harps_ 20261105_c 034_context','work_harps_20261105_c034_context').replace('work_harps_20261105_c 034_context','work_harps_20261105_c034_context')
 s=s.replace('ADP. 2025-','ADP.2025-').replace('T 01:','T01:')
 return re.sub(r'(ADP\.2025-\d\d-\d\d) T01:',r'\1T01:',s)
def main():
 for p in [PHASE/'README.md',PHASE/'analysis/RESULTS_REPORT.md']:
  p.write_text(format_prose(p.read_text()))
 for name in ['README.md','CONTINUE_SETI.md']:
  p=ROOT/name;top,rest=p.read_text().split('\n---\n\n',1);p.write_text(format_prose(top)+'\n---\n\n'+rest)
 p=PHASE/'CONTINUATION_STATE.json';d=json.loads(p.read_text());d['source_hashes']['work_harps_20261105_c034_context/analysis/RESULTS_REPORT.md']=hashlib.sha256((PHASE/'analysis/RESULTS_REPORT.md').read_bytes()).hexdigest();p.write_text(json.dumps(d,indent=2)+'\n')
if __name__=='__main__':main()
