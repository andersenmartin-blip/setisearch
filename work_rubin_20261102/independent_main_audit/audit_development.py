#!/usr/bin/env python3
"""Verify final DEV outputs with the independent scalar implementation."""
import datetime
import json
from pathlib import Path
import independent_science as audit


def main():
    base=Path(__file__).resolve().parent.parent
    method=base/'method_review'
    cfg=audit.load(method/'CONFIG.json')
    checks=audit.Checks()
    streams={}
    for stream,filename in [('sources','development_sources.json'),('forced','development_forced.json')]:
        rows=audit.load(base/'access_pilot/raw'/filename,raw=True)
        if stream=='sources':
            supplement={r['r:diaSourceId']:r for r in audit.load(base/'access_pilot/metadata/development_quality_supplement.json',raw=True)}
            rows=[dict(r,**supplement.get(r['r:diaSourceId'],{}))for r in rows]
        normal,scored,duplicates=audit.calculate(rows,stream,cfg)
        for kind,expected in [('NORMALIZED',normal),('SCORED',scored),('DUPLICATES',duplicates)]:
            checks.equal(audit.load(method/f'DEVELOPMENT_{stream.upper()}_{kind}.json'),expected,stream+'/'+kind)
        streams[stream]={'rows':len(normal),'scored':len(scored),
                         'evaluable':sum(r['status']=='NUMERICALLY_EVALUABLE'for r in scored),
                         'hits':sum(r['hit']for r in scored)}
    report={'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'scope':'Final technically corrected development method, before main flux; not main audit',
            'status':'PASS'if not checks.failures else'FAIL','comparisons':checks.count,
            'floating_comparisons':checks.numeric,'maximum_absolute_numeric_difference':checks.max_abs,
            'failures':checks.failures,'streams':streams,
            'config_sha256':audit.digest(method/'CONFIG.json'),'detector_sha256':audit.digest(method/'detector.py'),
            'audit_script_sha256':audit.digest(Path(__file__)),'scalar_detector_sha256':audit.digest(Path(audit.__file__))}
    (Path(__file__).resolve().parent/'DEV_CROSSCHECK.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if checks.failures:
        raise SystemExit(1)


if __name__=='__main__':
    main()
