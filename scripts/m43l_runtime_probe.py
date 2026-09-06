#!/usr/bin/env python3
"""No-spectra preflight for ordinary subprocesses and cooperative file stops."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from m43l_wider_integrated import FileAbort


def run_probe():
    with tempfile.TemporaryDirectory(prefix='m43l-probe-') as d:
        directory=Path(d);stop=directory/'abort'
        def child(i):
            script="from pathlib import Path; import sys; p=Path(sys.argv[1]); p.write_text('stopped' if Path(sys.argv[2]).exists() else 'ready')"
            subprocess.run([sys.executable,'-c',script,str(directory/f'child{i}'),str(stop)],check=True)
        with ThreadPoolExecutor(max_workers=7) as pool:list(pool.map(child,range(7)))
        assert all((directory/f'child{i}').read_text()=='ready' for i in range(7))
        flag=FileAbort(stop);assert not flag.is_set();flag.set();assert flag.is_set()
        with ThreadPoolExecutor(max_workers=7) as pool:list(pool.map(child,range(7)))
        assert all((directory/f'child{i}').read_text()=='stopped' for i in range(7))
    return {'ordinary_subprocesses':7,'initial_markers_exact':True,'file_stop_seen_by_all_children':True,
        'socket_service_used':False,'telescope_source_loads':0,'telescope_score_cells':0}


if __name__=='__main__':print(json.dumps(run_probe(),indent=2))
