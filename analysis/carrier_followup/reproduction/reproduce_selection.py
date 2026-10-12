#!/usr/bin/env python3
"""Replay the independent all-carrier check into a new directory.

Requires only Python and NumPy and the original root-relative archive layout.
The authenticated numerical checker is unchanged. No original result is
overwritten. This wrapper changes only its destination for receipt files.
"""
import argparse
import importlib.util
from pathlib import Path
import sys

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--out-dir',type=Path,required=True)
    args=parser.parse_args()
    root=args.root.resolve();out=args.out_dir.resolve()
    if not out.is_relative_to(root):raise ValueError('Choose an output directory inside the unpacked archive root')
    if out.exists():raise ValueError('Choose a new output directory; existing results are preserved')
    source=root/'carrier_followup/qa/selection/independent_selection_qa.py'
    scope=root/'carrier_followup/qa/selection/scope.json'
    go=root/'carrier_followup/qa/selection/ROOT_GO.json'
    for p in (source,scope,go):
        if not p.is_file():raise ValueError('Missing authenticated checker input: '+str(p))
    out.mkdir(parents=True)
    spec=importlib.util.spec_from_file_location('portable_independent_carrier_checker',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.ROOT=root;module.BASE=out
    sys.argv=[str(source),'--scope',str(scope),'--go',str(go)]
    module.main()

if __name__=='__main__':main()
