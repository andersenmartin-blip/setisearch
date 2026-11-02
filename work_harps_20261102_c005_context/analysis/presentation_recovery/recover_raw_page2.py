"""Recover one damaged presentation artifact using the exact frozen loop body.
No numerical recomputation, scale change, original overwrite or method edit.
"""
import ast,copy,hashlib,importlib.util,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;A=HERE.parent;OUT=A/'results'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def main():
    plan=read(A/'PLAN.json');code=A/'plot_group.py';index=read(OUT/'PLOT_INDEX.json');name='PRESERVED_RAW_ORDER_CONTEXT_2.png'
    assert sha(code)==plan['plot_script_sha256']
    numeric=read(OUT/'OUTPUT_HASHES.json')
    for p,h in numeric.items():assert sha(OUT/p)==h,p
    original=OUT/'figures'/name;record=next(r for r in index['files']if Path(r['path']).name==name)
    damaged=HERE/'DAMAGED_RAW_PAGE2.png'
    with damaged.open('xb')as f:f.write(original.read_bytes())
    dest=HERE/'figures';dest.mkdir(exist_ok=False)
    spec=importlib.util.spec_from_file_location('frozen_c005_plot_only',code);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    tree=ast.parse(code.read_text());body=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='main').body
    start=next(i for i,n in enumerate(body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='evidence'for t in n.targets))
    statements=copy.deepcopy(body[start:start+3]);assert isinstance(statements[-1],ast.For)
    loop=statements[-1];assert ast.unparse(loop.target)=='page'and ast.unparse(loop.iter)=='range(3)'
    loop.iter=ast.List(elts=[ast.Constant(value=1)],ctx=ast.Load())
    node=ast.fix_missing_locations(ast.Module(body=statements,type_ignores=[]));env=dict(vars(m));env['OUT']=OUT;env['figs']=dest
    exec(compile(node,str(code)+'::raw_page2_exact_body','exec'),env)
    recovered=dest/name
    for p,h in numeric.items():assert sha(OUT/p)==h,p
    result={'status':'EXACT_INDEXED_BYTES_RECOVERED'if sha(recovered)==record['sha256']else'RENDERED_PRESENTATION_REQUIRES_REVIEW','frozen_plot_sha256':sha(code),'recovery_script_sha256':sha(Path(__file__)),'selected_operation':'Exact frozen raw plotting loop, iteration page=1 only. Same arrays, dimensions, scales, labels and save options.','damaged_original_path':str(original.relative_to(A)),'damaged_preserved_path':str(damaged.relative_to(A)),'damaged_sha256':sha(damaged),'damaged_bytes':damaged.stat().st_size,'expected_indexed_sha256':record['sha256'],'expected_indexed_bytes':record['bytes'],'recovered_path':str(recovered.relative_to(A)),'recovered_sha256':sha(recovered),'recovered_bytes':recovered.stat().st_size,'numeric_outputs_unchanged':True,'original_file_overwritten':False,'frozen_sources_modified':False}
    (HERE/'RECOVERY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
