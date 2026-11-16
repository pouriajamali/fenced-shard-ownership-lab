"""INERT SDK0 changed-boundary cases; run only after exact source gate."""
import argparse,hashlib,importlib.util,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MODULE_SHA='d8c127b204cb7677925690aac09eaf6cac2d0d0adfba61dce694a77eb30a8528'
SHARED_FIXTURE_SHA='e1f3efa94e1a7acf836f186322734a15738bb69b6c1d3f7208a4fa9efc675216'
FIXTURE_SHA='22f3f4d611d487b310df289047a139ed9a7481cf0c03d5ade6a3bc29d938af51'
def main():
 p=argparse.ArgumentParser();p.add_argument('--suite',choices=['host-fact','shared06'],default='host-fact');p.add_argument('--mode',choices=['normal','O','env1'],required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if sys.flags.optimize!=(0 if a.mode=='normal' else 1):raise RuntimeError('ACTUAL_OPTIMIZATION_MODE')
 if a.mode=='env1' and (os.environ.get('PYTHONOPTIMIZE')!='1' or sys.flags.isolated or sys.flags.ignore_environment):raise RuntimeError('UNMASKED_ENV1')
 source=ROOT/'tools/ci_supported_host06.py';data=ROOT/('fixtures/SDK0-SHARED06-WIRING-CASES.json' if a.suite=='shared06' else 'fixtures/SDK0-BOUNDARY-CASES.json')
 if hashlib.sha256(source.read_bytes()).hexdigest()!=MODULE_SHA or hashlib.sha256(data.read_bytes()).hexdigest()!=(SHARED_FIXTURE_SHA if a.suite=='shared06' else FIXTURE_SHA):raise RuntimeError('EXACT_TEST_SOURCE_INPUT')
 raw=data.read_bytes()
 if len(raw)>524288:raise RuntimeError('FIXTURE_BYTES')
 spec=importlib.util.spec_from_file_location('ci06_sdk0_pure',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 cases=json.loads(raw)['cases'];rows=[]
 if len(cases)!=(7 if a.suite=='shared06' else 29):raise RuntimeError('EXACT_FINITE_CASE_COUNT')
 for case in cases:
  if case.get('testOnly') is not True:raise RuntimeError('SYNTHETIC_TEST_ONLY')
  denied=None
  try:
   if case['target']=='validate_shared_context_values':module.validate_shared_context_values(case['context'])
   elif case['target']=='strict_json':module.strict_json(case['inputRaw'].encode())
   elif case['target']=='fixed_linux_system_starter':module.fixed_linux_system_starter(**case['input'])
   elif case['target']=='validate_documents':
    d=case['input'];module.validate_documents(d['fact'],d['factDigest'],d['admission'],d['current'])
   else:raise RuntimeError('UNDECLARED_CASE_TARGET')
  except (RuntimeError,ValueError) as ex:denied=str(ex)
  if case['expect']=='DENY':
   if denied is None or case['expectedCodePrefix'] not in denied:raise RuntimeError('WRONG_DENIAL:'+case['id']+':'+str(denied))
  elif denied is not None:raise RuntimeError('CONTROL_DENIED:'+case['id']+':'+denied)
  rows.append({'id':case['id'],'status':'EXPECTED_METADATA_OUTCOME'})
 a.out.mkdir(exist_ok=False)
 (a.out/'receipt.json').write_text(json.dumps({'scope':'Selected synthetic SDK0 metadata outcomes only; not actual kernel or SDK admission','mode':a.mode,'cases':rows,'sdkCalls':0,'nativeProbes':0,'caseCount':len(cases),'suite':a.suite})+'\n')
if __name__=='__main__':main()
