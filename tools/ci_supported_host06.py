"""INERT REVIEW POSTIMAGE. Own06 typed supported-CI handshake, SDK calls absent.

This file is not installed in a checkout and is not an admission or producer fact.
qualifiedOn is immutable producer history; currentConsumer is a different job.
"""
import hashlib,json,os,platform,re,sys,time
from pathlib import Path
HOSTS={'win-x64':'GitHubHostedWindowsServer2025x64','linux-x64':'GitHubHostedUbuntu24.04x64'}
CONTRACT='50625c030b8f6c9a875fa67bc4f12e86464a6b89bfb8fa3378437e30aece4875'
DESIGN='9b3e0f376c5381b623f6a0f007bf6a6bb44f3dcbd1c2e4654de949a1eb97eec8'
REPOSITORY='pouriajamali/fenced-shard-ownership-lab'
PRODUCER='pouriajamali/data-admission-gate'
MAX_JSON=1048576

def need(ok,why):
 if not ok:raise RuntimeError('HOLD_CI06_TYPED_HOST_'+why)

def frame(value,length):return type(value) is str and re.fullmatch('[0-9a-f]{'+str(length)+'}',value) is not None

def strict_json(raw):
 need(type(raw) is bytes and len(raw)<=MAX_JSON,'JSON_BYTES_CAP')
 def pairs(items):
  d={}
  for k,v in items:need(k not in d,'DUPLICATE_FIELD');d[k]=v
  return d
 def constant(_):raise ValueError('NONFINITE_JSON')
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)

def read_data(path):
 p=Path(path);need(p.is_absolute() and '..' not in p.parts,'ABSOLUTE_DATA_PATH')
 for q in (p,*p.parents):
  s=q.lstat();need(not q.is_symlink() and not getattr(s,'st_file_attributes',0)&0x400,'DATA_PATH_REDIRECT')
 with p.open('rb') as f:raw=f.read(MAX_JSON+1)
 return strict_json(raw),hashlib.sha256(raw).hexdigest()

CANONICAL_SCHEMA_SHA='63e04fa5d270c87b93e6e1f4c38bfbcf336b950b39fe1854dc4e514f0661f14c'
CATALOG_SOURCE_SHA={'win-x64':'f87ecbf9ffebd4bcb6cd435739a070042e8c20299f63882e0277803478b54c7a','linux-x64':'307d56b0590f5adf8bfdc03ca22d151b987774c2e49934598cfd0ac0700c0571'}
FACT_KIND={'win-x64':'WindowsCIServer2025RID','linux-x64':'LinuxCIUbuntu24RID'}

def canonical_schema():
 p=Path(__file__).resolve().with_name('dotnet11-host-qualification.schema.json')
 raw=p.read_bytes();need(hashlib.sha256(raw).hexdigest()==CANONICAL_SCHEMA_SHA,'FROZEN_PRODUCER_SCHEMA_BYTES')
 return strict_json(raw)

def check_canonical(value,spec,reason):
 """Bounded interpretation of only this exact pinned producer schema subset.
 No jsonschema install, remote references, plugins or executable schema hooks.
 """
 budget=[100000]
 def same(a,b):
  if isinstance(a,bool) or isinstance(b,bool):return type(a) is type(b) and a==b
  return a==b
 def visit(v,n,depth):
  budget[0]-=1;need(depth<=64 and budget[0]>=0,reason+'_COMPLEXITY')
  allowed={'$schema','$id','title','description','$defs','type','required','additionalProperties','properties','const','enum','pattern','maxLength','minLength','maxItems','minItems','items','prefixItems','minimum','maximum','exclusiveMinimum'}
  need(set(n)<=allowed,reason+'_UNSUPPORTED_KEYWORD')
  if 'const' in n:need(same(v,n['const']),reason+'_CONST')
  if 'enum' in n:need(any(same(v,x) for x in n['enum']),reason+'_ENUM')
  types=n.get('type');types=[types] if isinstance(types,str) else types
  if types:
   actual='null' if v is None else ('boolean' if type(v) is bool else ('integer' if type(v) is int else ('number' if type(v) is float else ('string' if type(v) is str else ('array' if type(v) is list else ('object' if type(v) is dict else 'invalid'))))))
   need(actual in types or actual=='integer' and 'number' in types,reason+'_TYPE')
  if type(v) is dict:
   props=n.get('properties',{});need(all(k in v for k in n.get('required',[])),reason+'_REQUIRED')
   if n.get('additionalProperties') is False:need(set(v)<=set(props),reason+'_EXTRA_FIELD')
   for k in set(v)&set(props):visit(v[k],props[k],depth+1)
  if type(v) is list:
   need(len(v)>=n.get('minItems',0) and len(v)<=n.get('maxItems',100000),reason+'_ARRAY_COUNT')
   prefix=n.get('prefixItems',[])
   for i,x in enumerate(v):
    rule=prefix[i] if i<len(prefix) else n.get('items',{})
    need(rule is not False,reason+'_ARRAY_EXTRA')
    if rule is not True:visit(x,rule,depth+1)
  if type(v) is str:
   need(n.get('minLength',0)<=len(v)<=n.get('maxLength',MAX_JSON),reason+'_STRING_LENGTH')
   if 'pattern' in n:need(re.search(n['pattern'],v) is not None,reason+'_PATTERN')
  if type(v) in (int,float):
   if 'minimum' in n:need(v>=n['minimum'],reason+'_MINIMUM')
   if 'maximum' in n:need(v<=n['maximum'],reason+'_MAXIMUM')
   if 'exclusiveMinimum' in n:need(v>n['exclusiveMinimum'],reason+'_EXCLUSIVE_MINIMUM')
 visit(value,spec,0)

def validate_documents(fact,fact_digest,admission,current):
 """Producer canonical fact and #/$defs/consumerAdmission; no06 schema fork."""
 schema=canonical_schema()
 check_canonical(fact,schema,'CANONICAL_FACT_SCHEMA')
 check_canonical(admission,schema['$defs']['consumerAdmission'],'CANONICAL_ADMISSION_SCHEMA')
 need(type(current) is dict and frame(fact_digest,64),'TYPED_CURRENT_AND_DIGEST')
 rid=current.get('rid');host=HOSTS.get(rid);need(host is not None,'NATIVE_RID')
 q=fact['qualifiedOn'];a=admission['admittedFor'];execution=admission['currentExecution']
 need(fact['factType']==FACT_KIND[rid] and q['hostClass']==host and q['rid']==rid,'PRODUCER_HOST_RID_SCOPE')
 need(q['repository']==PRODUCER and q['attempt']=='1' and q['job']=='verify','IMMUTABLE_PRODUCER_HISTORY')
 need(fact['source']['schemaSha256']==CANONICAL_SCHEMA_SHA and fact['source']['catalogSha256']==CATALOG_SOURCE_SHA[rid],'FROZEN_PRODUCER_SOURCE_INTERFACE')
 need(type(fact['archive']['bytes']) is int and 0<fact['archive']['bytes']<=536870912,'SDK_RAW_INPUT_BOUND')
 need(admission['projectId']=='06' and a['contractSha256']==CONTRACT,'OWN_CONTRACT')
 need(admission['producerFactSha256']==fact_digest,'INDEPENDENT_MANAGER_FACT_BINDING')
 need(a['hostClass']==host and a['rid']==rid,'OWN_HOST_RID')
 need(a['memberManifestSha256']==fact['tree']['memberManifestSha256'],'MEMBER_MANIFEST_BINDING')
 need(a['sourcePinTableSha256']==current.get('sourceManifestSha256') and a['controllerSha256']==current.get('controllerSha256') and a['profileSha256']==current.get('profileSha256'),'OWN_SOURCE_PROFILE_BINDING')
 need(current.get('hostClass')==host and current.get('repository')==REPOSITORY and current.get('runnerEnvironment')=='github-hosted' and current.get('container') is False,'OWN_OBSERVED_SUPPORTED_VM')
 need(current.get('osObserved') is True and current.get('cpuV2Observed') is True,'OWN_OS_CPU_OBSERVATION')
 need(type(current.get('attempt')) is int and current['attempt']==1,'OWN_ATTEMPT')
 need(execution['runId']==current.get('runId') and execution['job']==current.get('jobId') and execution['attempt']==str(current['attempt']) and execution['instanceId']==current.get('instanceId'),'OWN_CURRENT_EXECUTION')
 need(execution['ownCapsEvidenceSha256']==current.get('ownCapsEvidenceSha256'),'OWN_CAPS_EVIDENCE_BINDING')
 need(current.get('dirty') is False and frame(current.get('sourceCommit'),40) and frame(current.get('sourceTree'),40),'CLEAN_EXACT_SOURCE')
 need(current.get('kernelObserved') is True and current.get('heldChildMembershipBeforeTarget') is True,'OWN_ACTUAL_KERNEL_HELD_CHILD')
 need(current.get('ownerIdentityObserved') is True and current.get('typedTerminalRequired') is True,'OWN_OWNER_TERMINAL_CONTRACT')
 need(type(current.get('remainingJobSeconds')) in (int,float) and 0<current['remainingJobSeconds']<=900,'ONE_REMAINING_900S_DEADLINE')
 # qualifiedOn.job/runId are historical. Compare currentExecution only to the
 # current consumer; never require producer/consumer instance equality.
 return {'schemaId':schema['$id'],'producerFactSha256':fact_digest,'qualifiedOn':q,'admittedFor':a,'currentExecution':execution,'currentConsumer':current,'sameJobRequired':False,'sdkTargetsExecuted':0}

def observe_host_environment(rid):
 """Own pre-existing OS metadata only. Never a transferable kernel proof."""
 need(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted','NAMED_GITHUB_HOSTED_ONLY')
 need(os.environ.get('GITHUB_REPOSITORY')==REPOSITORY and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','OWN_REPOSITORY_ATTEMPT')
 need(platform.machine().lower() in ('amd64','x86_64'),'X64_REQUIRED')
 image=os.environ.get('ImageOS','');version=os.environ.get('ImageVersion','')
 need(type(version) is str and 0<len(version)<=200,'ACTUAL_IMAGE_VERSION')
 record={'rid':rid,'hostClass':HOSTS.get(rid),'repository':REPOSITORY,'runnerEnvironment':os.environ['RUNNER_ENVIRONMENT'],'runId':os.environ.get('GITHUB_RUN_ID'),'jobId':os.environ.get('GITHUB_JOB'),'attempt':1,'imageOS':image,'imageVersion':version,'instanceId':os.environ.get('RUNNER_NAME'),'container':False}
 if rid=='linux-x64':
  need(sys.platform=='linux' and os.getuid()!=0 and os.getgid()!=0,'ACTUAL_NONROOT_LINUX')
  need(not Path('/.dockerenv').exists() and not Path('/run/.containerenv').exists(),'NO_CONTAINER')
  release=Path('/etc/os-release').read_text();kernel=Path('/proc/sys/kernel/osrelease').read_text().lower()
  need('ID=ubuntu' in release and 'VERSION_ID="24.04"' in release and image=='ubuntu24','ACTUAL_UBUNTU24_IMAGE')
  need('microsoft' not in kernel and 'wsl' not in kernel and Path('/proc/1/comm').read_text().strip()=='systemd','EPHEMERAL_SYSTEM_VM_NOT_WSL')
  cpu=Path('/proc/cpuinfo').read_text();sets=[set(line.split(':',1)[1].split()) for line in cpu.splitlines() if line.startswith('flags')]
  required={'cx16','popcnt','pni','ssse3','sse4_1','sse4_2','lahf_lm'};need(sets and all(required<=s for s in sets),'EVERY_LOGICAL_CPU_V2')
  record.update(uid=os.getuid(),gid=os.getgid(),bootId=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),cpuV2Observed=True,osObserved=True)
 else:
  need(rid=='win-x64' and os.name=='nt' and image=='win25','NAMED_WINDOWS2025_IMAGE')
  import winreg
  with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Windows NT\CurrentVersion') as k:
   values={n:winreg.QueryValueEx(k,n)[0] for n in ('ProductName','InstallationType','CurrentBuildNumber','UBR')}
  need('Server' in values['InstallationType'] and 'Server 2025' in values['ProductName'] and values['CurrentBuildNumber']=='26100','ACTUAL_SERVER2025_NOT_26H2_CLIENT')
  from ci_supported_kernel06 import windows_cpu_v2
  cpu=windows_cpu_v2();record.update(actualWindows=values,osObserved=True,cpuV2Observed=cpu['observed'],cpuObservation=cpu)
 return record

def fixed_linux_system_starter(current,worker_argv,unit,remaining):
 """Produce argv only; no sudo/systemd/worker is executed by this function."""
 need(current.get('hostClass')==HOSTS['linux-x64'] and current.get('osObserved') is True,'OBSERVED_SUPPORTED_HOST')
 need(type(current.get('uid')) is int and current['uid']>0 and type(current.get('gid')) is int and current['gid']>0,'ACTUAL_RUNNER_USER_GROUP')
 need(re.fullmatch('ownershiplab-ci-[0-9a-f]{16}-(verify|prepare|runtime|aggregate)',unit) is not None,'FIXED_OWN_UNIT')
 need(type(remaining) is int and 5<remaining<=900,'SINGLE_OUTER_REMAINING')
 need(type(current.get('python')) is str and Path(current['python']).is_absolute(),'BOUND_EXISTING_PYTHON')
 expected=[current['python'],'-I','-B',str(Path(current['checkout'])/'tools/ci_pipeline.py'),'--worker','--stage',current['stage'],'--rid','linux-x64','--commit',current['sourceCommit'],'--token',current['token'],'--unit',unit]
 need(worker_argv==expected,'EXACT_SOURCE_BOUND06_WORKER_ARGV')
 profile=current['kernelProfile'];need(profile in ('generic64','native-linux-16'),'FIXED_UNPAIRED_CI_PROFILE')
 tasks=128 if profile=='native-linux-16' else 64
 need(profile!='native-linux-16' or unit.endswith('-runtime'),'NO_128_COMPILER_AUDIT_OR_GENERIC')
 return ['/usr/bin/sudo','-n','/usr/bin/systemd-run','--wait','--pipe','--unit='+unit,'--uid='+str(current['uid']),'--gid='+str(current['gid']),'--property=MemoryMax=4294967296','--property=MemorySwapMax=0','--property=CPUQuota=200%','--property=TasksMax='+str(tasks),'--property=RuntimeMaxSec='+str(remaining-5),'--property=TimeoutStopSec=5','--property=KillMode=control-group','--property=SendSIGKILL=yes','--property=FinalKillSignal=SIGKILL','--property=WorkingDirectory='+current['checkout'],*worker_argv]

def validate_shared_context_values(context):
 expected={'admission','capsEvidence','checkout','contract','controller','deadlineMonotonicNs','expectedSourceCommit','expectedSourceTree','profile','projectId','repository','rowStartedMonotonicNs','sourcePins','supervisorPID','supervisorStartIdentity'}
 need(type(context) is dict and set(context)==expected,'SHARED_CONTEXT_EXACT_KEYS')
 need(context['projectId']=='06' and context['repository']==REPOSITORY,'SHARED_OWN06_CONTEXT')
 start=context['rowStartedMonotonicNs'];end=context['deadlineMonotonicNs']
 need(type(start) is int and type(end) is int and 0<start<end and end-start<=900*1000000000,'SHARED_ORIGINAL_DEADLINE')
 need(type(context['supervisorPID']) is int and context['supervisorPID']>0 and re.fullmatch('proc-start:[0-9]+',context['supervisorStartIdentity'] or '') is not None,'SHARED_SUPERVISOR_START')
 return True

def consume_sdk(root,rid,env):
 """Own06 wiring only; exact common transport remains byte-identical."""
 need(rid=='linux-x64','WINDOWS_NORMAL_DENIED_NO_ACCEPTED_PRODUCER_FACT')
 root=Path(root);phase=root/'artifacts/ci-caps/verify'
 record,_=read_data(phase/'sdk11-shared-context.json');context=record['context']
 validate_shared_context_values(context)
 need(Path(context['controller'])==root/'tools/ci_pipeline.py' and Path(context['checkout'])==root,'OWN_TRACKED_MAIN_CONTROLLER')
 common=root/'tools/check_dotnet11.py'
 need(hashlib.sha256(common.read_bytes()).hexdigest()=='d9c690d8c82825b018c04089c279036829d3baf2534c2634bba84910c415a37d','IDENTICAL_COMMON_TRANSPORT_SOURCE')
 from check_dotnet11 import transport
 # No arbitrary output directory; one fresh direct child of this runner.temp.
 import secrets
 directory=Path(os.environ['RUNNER_TEMP'])/('sdk11-normal-06-'+secrets.token_hex(12))
 sdk_path,receipt=transport(rid,directory,context)
 need(receipt['SDKExecutions']==0 and receipt['projectId']=='06','INPUT_ONLY_TYPED_RETURN')
 with (phase/'typed-host-handshake.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=2);f.write('\n')
 env['DOTNET_ROOT']=str(sdk_path);env['DOTNET_MULTILEVEL_LOOKUP']='0'
 return str(sdk_path/'dotnet')
