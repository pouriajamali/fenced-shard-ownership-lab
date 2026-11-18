"""Own06 P0 read-only Windows P3 input binding. No SDK or product commands."""
import argparse,datetime,hashlib,importlib.util,json,os,secrets,stat,subprocess,sys,time
from pathlib import Path
REPOSITORY='pouriajamali/fenced-shard-ownership-lab'
HELPER_SHA='e14e6feb51d1dfd0ea1865df36a4432ccf397dcd19849038d9b4e69cf7402d1e'
FACADE_SHA='efb3d151725e1ab8dd86d3ac5c2bab2d270f8086eafd576818730e0f44a5a345'
PROTOCOL_SHA='9120ca49a0d46673053aa0ec0cdbbc6f00731d71ea0b57ddab09e8fc3ac3ac8b'
FACT_SHA='841b508658a3a843f7d194b089b355b3e2e572873b4301349f3b545255086339'
MANAGER=Path('E:/Codex WorkSpace/Git Projects/portfolio-management/development-management-20261110')
FACT=MANAGER/'wave4-state/project04-shared-normal-final-20261117/LOCAL-WINDOWS04-HOST-FACT.json'
LEASE=MANAGER/'wave2-state/LOCAL-FIXTURE-LEASE.json'
JOB_PREFIX='Local'+chr(92)+'ownership06-net11-input-'

def need(ok,why):
 if not ok:raise RuntimeError('HOLD_LOCAL_INPUT06_'+why)

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()

def ordinary(p):
 for q in (Path(p),*Path(p).parents):
  if q.exists():
   s=q.lstat();need(not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,'REPARSE_OR_SYMLINK')

def read(p):
 ordinary(p);raw=Path(p).read_bytes();need(len(raw)<=1048576,'JSON_LIMIT')
 def pairs(rows):
  d={}
  for k,v in rows:need(k not in d,'DUPLICATE_JSON_KEY');d[k]=v
  return d
 return json.loads(raw,object_pairs_hook=pairs)

def write(p,v):
 ordinary(Path(p).parent)
 with Path(p).open('xb') as f:f.write((json.dumps(v,indent=2)+chr(10)).encode());f.flush();os.fsync(f.fileno())

def load(root,name,expected):
 p=root/'tools'/(name+'.py');need(digest(p)==expected,'PINNED_'+name)
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def validate_spec(s,now):
 need(s.get('purpose')=='OWN06_P0_WINDOWS_P3_INPUT_ONLY' and s.get('projectId')=='06' and s.get('repository')==REPOSITORY,'OWN_PURPOSE')
 need(type(s.get('startNs')) is int and type(s.get('endNs')) is int and 0<s['startNs']<=now<s['endNs'] and s['endNs']-s['startNs']==60000000000,'ORIGINAL_P0_60_NO_RESET')
 need(type(s.get('workerPID')) is int and s['workerPID']>0 and str(s.get('workerStart','')).startswith('FILETIME:'),'HELD_WORKER_IDENTITY')
 need(type(s.get('supervisorPID')) is int and s['supervisorPID']>0 and s['supervisorPID']!=s['workerPID'] and str(s.get('supervisorStartIdentity','')).startswith('FILETIME:'),'LIVE_PARENT_IDENTITY')
 need(s.get('helperSha256')==HELPER_SHA and s.get('facadeSha256')==FACADE_SHA,'SOURCE_HELPER_PINS')
 need(s.get('beforeResume',{}).get('membership') is True and s['beforeResume'].get('retainedCreationHandles') is True,'RETAINED_HELD_WITNESS')

def validate_lease(h,s):
 need(h.get('projectId')=='06' and h.get('randomToken')==s.get('leaseToken') and h.get('ownerPID')==s.get('supervisorPID') and h.get('ownerProcessStartIdentity')==s.get('supervisorStartIdentity') and h.get('phase')=='P0_WINDOWS_P3_SDK_INPUT_ONLY' and h.get('sourceCommit')==s.get('commit') and h.get('receiptDirectory')==s.get('receiptDirectory'),'EXACT_LIVE_CANONICAL_LEASE')

def release_allowed(holder,current,identity,record):
 cap=record.get('actualCap',{});child=record.get('childBeforeExec',{})
 return current==holder and holder.get('ownerProcessStartIdentity')==identity and cap.get('kind')=='actual-Windows-Job' and type(cap.get('activeProcessesAtTeardown')) is int and cap['activeProcessesAtTeardown']==0 and cap.get('memoryMax')==4294967296 and cap.get('activeProcessMax')==64 and 0<cap.get('effectiveCpuCores',0)<=2 and cap.get('retainedCreationHandles') is True and cap.get('childMembershipBeforeResume') is True and child.get('membershipBeforeResume') is True and type(child.get('pid')) is int and child['pid']>0 and str(child.get('processStartIdentity','')).startswith('FILETIME:')

def worker(root,controller,spec):
 need(os.name=='nt','WINDOWS_ONLY');s=read(spec);validate_spec(s,time.monotonic_ns());need(s['controllerSha256']==digest(controller),'EXACT_CONTROLLER');need(Path(s['checkout']).resolve()==root.resolve(),'EXACT_CHECKOUT')
 out=spec.parent;need(out.parent==root.parents[1]/'state/execution-evidence/net11-local-input06' and s.get('receiptDirectory')==str(out),'OWN_EVIDENCE_DIRECTORY');need(digest(LEASE)==s['leaseSHA256'],'LEASE_BYTES');validate_lease(read(LEASE),s);j=load(root,'windows_qualification_job_local',HELPER_SHA)
 need(os.getpid()==s['workerPID'] and j._start_identity(os.getpid())==s['workerStart'] and os.getppid()==s['supervisorPID'],'ACTUAL_HELD_MAIN');cap=j.current_witness(s['jobName']);held=s['beforeResume']
 who={'pid':os.getpid(),'processStartIdentity':s['workerStart'],'jobName':s['jobName'],'memoryMaxBytes':cap['memoryMax'],'tasksMax':cap['tasksMax'],'cpuRate':cap['cpuRate'],'logicalHostCpu':cap['logicalHostCpu']}
 before={**who,'memoryMaxBytes':held['memoryMax'],'tasksMax':held['activeProcessMax'],'cpuRate':held['cpuRate'],'logicalHostCpu':held['logicalHostCpu'],'state':'SUSPENDED','membershipBeforeRelease':held['membership'],'retainedStartHandle':held['retainedCreationHandles']}
 profile=root/'profiles/local-windows-input06.json';contract=root/'tools/ci06-normal-contract.json';pins=root/'tools/ci06-source-pins.json';boot={'pythonVersion':'.'.join(map(str,sys.version_info[:3])),'pythonExeSha256':digest(sys.executable),'gitSha256':digest('C:/Program Files/Git/cmd/git.exe')}
 proof={'schema':'sdk11-own-current-cap-evidence/v1','projectId':'06','repository':REPOSITORY,'sourceCommit':s['commit'],'sourceTree':s['tree'],'profileSha256':digest(profile),'controllerSha256':digest(controller),'bootstrap':boot,'worker':who,'heldBeforeExec':before,'supervisor':{'pid':s['supervisorPID'],'processStartIdentity':s['supervisorStartIdentity'],'deadlineMonotonicNs':s['endNs']},'rowStartedMonotonicNs':s['startNs'],'deadlineMonotonicNs':s['endNs']}
 cp=out/'own-current-caps.json';ap=out/'local-input-context.json';write(cp,proof);write(ap,{'schema':'sdk11-local-input-current/v1','state':'OWN_CURRENT_INPUT_CONTEXT_BOUND','projectId':'06','repository':REPOSITORY,'rid':'win-x64','qualifiedFactPath':str(FACT),'qualifiedFactSha256':FACT_SHA,'profileSha256':digest(profile),'controllerSha256':digest(controller),'ownCapsEvidenceSha256':digest(cp),'sourcePinTableSha256':hashlib.sha256(canonical(read(pins)['sourcePins'])).hexdigest()})
 ctx={'projectId':'06','repository':REPOSITORY,'checkout':str(root),'controller':str(controller),'contract':str(contract),'profile':str(profile),'sourcePins':str(pins),'admission':str(ap),'capsEvidence':str(cp),'expectedSourceCommit':s['commit'],'expectedSourceTree':s['tree'],'rowStartedMonotonicNs':s['startNs'],'deadlineMonotonicNs':s['endNs'],'supervisorPID':s['supervisorPID'],'supervisorStartIdentity':s['supervisorStartIdentity']}
 need(digest(FACT)==FACT_SHA,'QUALIFIED_BYTE_HISTORY');facade=load(root,'local_sdk11_input',FACADE_SHA);receipt=facade.inspect_sdk('win-x64',Path(read(FACT)['SDKPath']),ctx)
 need(receipt['SDKExecutions']==0 and receipt['projectId']=='06' and receipt['CI'] is False and receipt['productAdmission'] is False,'INPUT_ONLY_RESULT');write(out/'local-sdk-input.json',receipt);need(time.monotonic_ns()<s['endNs'],'ORIGINAL_DEADLINE');need(digest(LEASE)==s['leaseSHA256'],'LEASE_CHANGED_DURING_INPUT');validate_lease(read(LEASE),s)
 write(out/'worker-result.json',{'state':'OWN06_CURRENT_WINDOWS_SDK_INPUT_ONLY_VERIFIED','sourceCommit':s['commit'],'sourceTree':s['tree'],'SDKExecutions':0,'productAdmission':False,'formalDotnet11Support':'NOT_CONFIRMED'})

def main(root,controller,argv):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--local-windows-input',action='store_true');p.add_argument('--local-input-worker',type=Path);p.add_argument('--expected-commit');a=p.parse_args(argv);root=Path(root);controller=Path(controller).resolve()
 if a.local_input_worker:
  need(not a.local_windows_input and a.expected_commit is None,'WORKER_ARGS');return worker(root,controller,a.local_input_worker)
 need(a.local_windows_input and a.expected_commit is not None and os.name=='nt','FINITE_WINDOWS_INPUT_ENTRY');need(not any(os.environ.get(k) for k in ('GITHUB_ACTIONS','GITHUB_RUN_ID','RUNNER_ENVIRONMENT')),'LOCAL_NOT_CI')
 j=load(root,'windows_qualification_job_local',HELPER_SHA);start_ns=time.monotonic_ns();start_tick=j.tick();end_ns=start_ns+60000000000
 def git(*args):return subprocess.check_output(['C:/Program Files/Git/cmd/git.exe','-C',str(root),*args],timeout=10,creationflags=0x08000000).decode().strip()
 head=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}');need(head==a.expected_commit and not git('status','--porcelain=v1','--untracked-files=all'),'CLEAN_EXPECTED_SOURCE');need(digest(FACT)==FACT_SHA,'FACT_IDENTITY')
 need(sys.version_info[:3]==(3,12,10) and digest(sys.executable)==read(FACT)['bootstrap']['pythonExeSha256'],'QUALIFIED_EXISTING_BOOTSTRAP_BYTES')
 protocol=LEASE.with_name('LEASE-PROTOCOL.json');need(digest(protocol)==PROTOCOL_SHA and Path(read(protocol)['canonicalLeaseWindows'])==LEASE,'CANONICAL_PROTOCOL')
 base=root.parents[1]/'state/execution-evidence/net11-local-input06';ordinary(base);base.mkdir(exist_ok=True);out=base/('p0-'+secrets.token_hex(12));out.mkdir();token=secrets.token_hex(32);identity=j._start_identity(os.getpid())
 holder={'projectId':'06','randomToken':token,'ownerOS':'Windows','ownerPID':os.getpid(),'ownerProcessStartIdentity':identity,'phase':'P0_WINDOWS_P3_SDK_INPUT_ONLY','startedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'receiptDirectory':str(out),'timeoutSeconds':60,'sourceCommit':head}
 try:write(LEASE,holder)
 except FileExistsError:write(out/'receipt.json',{'state':'BUSY_NOT_CLAIMED','SDKExecutions':0});print(json.dumps({'state':'BUSY_NOT_CLAIMED','receipt':str(out/'receipt.json')}));return 20
 result={'state':'HOLD','sourceCommit':head,'sourceTree':tree,'SDKExecutions':0,'Actions':0,'productAdmission':False,'released':False};record={};spec=out/'private-spec.json'
 try:
  need(time.monotonic_ns()<end_ns-30000000000,'P0_WORK_AND_TERMINAL_RESERVE');value={'purpose':'OWN06_P0_WINDOWS_P3_INPUT_ONLY','projectId':'06','repository':REPOSITORY,'checkout':str(root),'commit':head,'tree':tree,'controllerSha256':digest(controller),'helperSha256':HELPER_SHA,'facadeSha256':FACADE_SHA,'startNs':start_ns,'endNs':end_ns,'supervisorPID':os.getpid(),'supervisorStartIdentity':identity,'receiptDirectory':str(out),'leaseToken':token,'leaseSHA256':digest(LEASE)}
  env={k:os.environ[k] for k in ('SystemRoot','WINDIR','COMSPEC','PATHEXT','USERPROFILE') if k in os.environ};env.update(PATH='C:/Windows/System32;C:/Windows',PYTHONDONTWRITEBYTECODE='1')
  record=j.run_job([sys.executable,'-I','-S','-B',str(controller),'--local-input-worker',str(spec)],root,env,start_tick+30000,out/'job',job_name=JOB_PREFIX+secrets.token_hex(12),ready_spec={'path':spec,'value':value},local_console_mode='DETACHED_LOCAL_CONSOLE_FREE_V1')
  data=read(out/'worker-result.json');need(data['state']=='OWN06_CURRENT_WINDOWS_SDK_INPUT_ONLY_VERIFIED' and data['sourceCommit']==head,'ACTUAL_CURRENT_INPUT_RESULT');result.update(state=data['state'],currentInput=read(out/'local-sdk-input.json'))
 except Exception as exc:
  result.update(errorType=type(exc).__name__,error=str(exc)[:300])
  if (out/'job/process.json').is_file():record=read(out/'job/process.json')
 finally:
  result['process']=record;result['ownedTerminalVerified']=type(record.get('actualCap',{}).get('activeProcessesAtTeardown')) is int and record['actualCap']['activeProcessesAtTeardown']==0;write(out/'outcome-before-release.json',result)
  try:
   current_identity=j._start_identity(os.getpid());current_holder=read(LEASE)
   if release_allowed(holder,current_holder,current_identity,record):LEASE.unlink();result['released']=True
   else:result['releaseError']='NO_EXACT_OWNERSHIP_OR_POSITIVE_TERMINAL'
  except Exception as exc:result['releaseError']=type(exc).__name__+':'+str(exc)[:150]
  result['elapsedSeconds']=(time.monotonic_ns()-start_ns)/1e9;result['original60SecondEnvelopeMet']=result['elapsedSeconds']<=60;write(out/'receipt.json',result)
 print(json.dumps({'state':result['state'],'released':result['released'],'SDKExecutions':0,'productAdmission':False,'receipt':str(out/'receipt.json')}));need(result['state']=='OWN06_CURRENT_WINDOWS_SDK_INPUT_ONLY_VERIFIED' and result['released'] and result['original60SecondEnvelopeMet'],'CURRENT_INPUT_HOLD');return 0
