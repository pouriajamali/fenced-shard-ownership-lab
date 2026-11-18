"""Read-only local SDK input facade; frozen CI guard/schema remain unchanged.
No download, extraction, target execution, Job/limit/security setter or READY flag.
"""
from __future__ import annotations
import contextlib,hashlib,importlib.util,json,os,pathlib,platform,re,select,subprocess,sys,time,uuid
HERE=pathlib.Path(__file__).resolve().parent
p=HERE/'check_dotnet11.py'
if hashlib.sha256(p.read_bytes()).hexdigest()!='c37e2f48ee21ef1f02e4afb2bb1cd0af397781e487265c31e43fe06ea182befd':raise RuntimeError('FROZEN_INPUT_LIBRARY_IDENTITY')
s=importlib.util.spec_from_file_location('check_dotnet11',p);C=importlib.util.module_from_spec(s);sys.modules[s.name]=C;s.loader.exec_module(C)
FACTS={'linux-x64':'ad63c4ad44af1844e1c937152294b07cdce9faccf2e2e7899cc221f2e485fb3c','win-x64':'841b508658a3a843f7d194b089b355b3e2e572873b4301349f3b545255086339'}
CATALOGS={'linux-x64':('dotnet11-linux-qualification-inputs.lock.json','307d56b0590f5adf8bfdc03ca22d151b987774c2e49934598cfd0ac0700c0571'),'win-x64':('dotnet11-qualification-inputs.lock.json','f87ecbf9ffebd4bcb6cd435739a070042e8c20299f63882e0277803478b54c7a')}
REPOS={'01':'financial-reconciliation-ledger','02':'trading-execution-lab','03':'market-data-integrity-lab','04':'data-admission-gate','05':'point-in-time-reference-lab','06':'fenced-shard-ownership-lab'}
# Independent task authority, never an inherited producer04 admission.
WINDOWS_AUTHORITIES={'04':'call_82e9689938c64cbdb74f7e75b4bef33c+call_923c5d0e47704ebc80ab26e6a4fc3fbf','06':'01a1ea8f-e946-71b0-b4a7-40cd30723b0f'}
MATRIX={'01':(2147483648,64,2),'02':(4294967296,64,2),'03':(4294967296,128,2),'04':(4294967296,64,2),'05':(4294967296,64,1),'06':(4294967296,64,2)}

def policy(profile,project,rid):
 C.need(project in REPOS and profile.get('projectId')==project and profile.get('repository')=='pouriajamali/'+REPOS[project],'LOCAL_OWN_PROJECT_REPOSITORY')
 C.need(profile.get('schema')=='sdk11-own-normal-input-profile/v1' and profile.get('state')=='ADMITTED_SOURCE_PROFILE','LOCAL_OWN_SOURCE_PROFILE')
 route=profile.get('localInputRoute',{});C.need(route.get('rid')==rid and route.get('readOnlyExistingPool') is True,'LOCAL_EXPLICIT_READONLY_INPUT_ROUTE')
 role=route.get('role');limits=MATRIX[project]
 if rid=='win-x64':
  C.need(project in WINDOWS_AUTHORITIES and route.get('authorityId')==WINDOWS_AUTHORITIES[project] and route.get('formalDotnet11Support')=='NOT_CONFIRMED','LOCAL_INDEPENDENT_WINDOWS_TASK_AUTHORITY_REQUIRED')
  if project=='06':C.need(role=='P3_WINDOWS_BUILD' and route.get('phase')=='P3','LOCAL06_P3_BUILD_ONLY_R06_IS_BINARY_PAIRED_SCENARIO')
  else:C.need(role=='generic','LOCAL04_GENERIC_ROLE')
 else:
  C.need(rid=='linux-x64','LOCAL_RID');C.need(role=='generic' or project=='06' and role=='native-linux16','LOCAL_LINUX_RETIRED_OR_UNKNOWN_ROLE')
  if project=='06' and role=='native-linux16':limits=(4294967296,128,2)
 memory,tasks,cpu=limits;C.need(profile.get('memoryMaxBytes')==memory and profile.get('tasksMax')==tasks,'LOCAL_NO_BORROWED_OR_INCREASED_CAPS');C.need(type(profile.get('rowSeconds')) is int and 0<profile['rowSeconds']<=C.BUDGETS[project],'LOCAL_ORIGINAL_ROW_BUDGET')
 if rid=='linux-x64':C.need(profile.get('swapMaxBytes')==0 and profile.get('cpuQuotaMicros')==cpu*100000 and profile.get('cpuPeriodMicros')==100000,'LOCAL_ORIGINAL_LINUX_CAPS')
 else:C.need(profile.get('cpuCores')==cpu and profile.get('swapMaxBytes') is None,'LOCAL_ORIGINAL_WINDOWS_CAPS')
 return limits

def git_prefix(checkout,repository):
 if os.name=='nt':return ['C:/Program Files/Git/cmd/git.exe','-C',str(checkout)]
 args=['/usr/bin/git','-c','safe.directory='+str(checkout)]
 p=checkout/'.git'
 if p.is_file():
  text=p.read_text(encoding='utf-8').strip();m=re.fullmatch(r'gitdir: ([A-Za-z]):/(.+)',text)
  C.need(m is not None and '..' not in pathlib.PurePosixPath(m[2]).parts and repository.split('/')[-1] in pathlib.PurePosixPath(m[2]).parts and '/.git/worktrees/' in '/'+m[2],'LOCAL_EXACT_OWN_WINDOWS_WORKTREE_POINTER')
  args+=['--git-dir=/mnt/'+m[1].lower()+'/'+m[2],'--work-tree='+str(checkout)]
 return [*args,'-C',str(checkout)]

def _windows_source_git(argv,cwd,end,limit=1048576):
 env={k:v for k,v in os.environ.items() if k.upper() in ('SYSTEMROOT','WINDIR','TEMP','TMP')};env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL='NUL',GIT_TERMINAL_PROMPT='0',GCM_INTERACTIVE='Never')
 r=subprocess.run(['C:/Program Files/Git/cmd/git.exe','-C',str(cwd),*argv],capture_output=True,env=env,timeout=min(10,C._remaining(end)),creationflags=0x8|0x400);C.need(r.returncode==0 and len(r.stdout)+len(r.stderr)<=limit,'NORMAL_WINDOWS_SOURCE_TOOL');return r.stdout

def source(ctx,paths,pins,end):
 checkout=pathlib.Path(ctx['checkout']).resolve();argv=git_prefix(checkout,ctx['repository'])
 def run(*args):
  if os.name=='nt':
   return _windows_source_git(args,checkout,end)
  env={**C.SAFE_ENV,'GIT_OPTIONAL_LOCKS':'0'}
  r=subprocess.run([*argv,'--no-optional-locks',*args],cwd=checkout,env=env,capture_output=True,timeout=min(30,C._remaining(end)))
  C.need(len(r.stdout)+len(r.stderr)<=1048576,'LOCAL_SOURCE_OUTPUT_CAP');C.need(r.returncode==0,'LOCAL_SOURCE_TOOL_FAILED');return r.stdout
 head=run('rev-parse','HEAD','HEAD^{tree}').decode().splitlines();C.need(head==[ctx['expectedSourceCommit'],ctx['expectedSourceTree']],'LOCAL_EXACT_CURRENT_SOURCE')
 C.need(not run('status','--porcelain=v1','--untracked-files=all'),'LOCAL_CURRENT_SOURCE_NOT_CLEAN');actual={}
 for row in run('ls-tree','-r','-z','HEAD').split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t',1);mode,kind,blob=meta.decode().split();C.need(kind=='blob' and mode in ('100644','100755'),'LOCAL_SOURCE_MODE');n=name.decode();actual[n]={'path':n,'mode':mode,'gitBlob':blob}
 pinname=paths['sourcePins'].relative_to(checkout).as_posix();C.need(pinname in actual,'LOCAL_PIN_TABLE_TRACKED');actual.pop(pinname);rows=pins.get('sourcePins',[]);C.need(len(rows)==len({x['path'] for x in rows}) and {x['path']:x for x in rows}==actual,'LOCAL_COMPLETE_SOURCE_PINS')
 C.need(pins.get('schema')=='sdk11-own-source-pins/v1' and pins.get('state') in ('EXACT_SOURCE_REVIEWED','EXACT_SOURCE_PINNED') and pins.get('projectId')==ctx['projectId'] and pins.get('repository')==ctx['repository'],'LOCAL_PIN_TABLE_OWNER')
 for key in ('controller','contract','profile'):
  n=paths[key].relative_to(checkout).as_posix();C.need(n in actual,'LOCAL_BINDING_TRACKED');C.validate_source_file(paths[key],actual[n],run('show','HEAD:'+n))
 return {'commit':head[0],'tree':head[1]}

def linux_current(ctx,profile,end):
 C.need(os.name=='posix' and os.getuid()>0 and os.getgid()>0 and platform.machine()=='x86_64' and sys.version_info[:2]==(3,12),'LOCAL_UBUNTU_BOOTSTRAP')
 release=dict(x.split('=',1) for x in pathlib.Path('/etc/os-release').read_text().splitlines() if '=' in x);C.need(release.get('ID')=='ubuntu' and release.get('VERSION_ID','').strip('"')=='24.04' and 'microsoft' in platform.release().lower() and pathlib.Path('/proc/1/comm').read_text().strip()=='systemd','LOCAL_ACTUAL_QUALIFIED_UBUNTU24_WSL2_CLASS')
 raw=pathlib.Path('/proc/cpuinfo').read_bytes();flags=[set(x.split(':',1)[1].split()) for x in raw.decode().splitlines() if x.startswith('flags')];C.need(flags and all({'cx16','popcnt','pni','ssse3','sse4_1','sse4_2','lahf_lm'}<=x for x in flags),'LOCAL_CURRENT_CPU_V2')
 group=next((x[3:] for x in pathlib.Path('/proc/self/cgroup').read_text().splitlines() if x.startswith('0::')),None);C.need(group and re.fullmatch('/system.slice/[A-Za-z0-9_.@-]+[.]service',group),'LOCAL_ACTUAL_OWN_SYSTEM_UNIT_REQUIRED');unit=group.rsplit('/',1)[1];C.need(unit.startswith(profile['ownedUnitPrefix']),'LOCAL_OWN_UNIT_PREFIX')
 root=pathlib.Path('/sys/fs/cgroup')/group.lstrip('/');limits={k:(root/k).read_text().strip() for k in ('memory.max','memory.swap.max','pids.max','cpu.max')};C.need(os.getpid() in [int(x) for x in (root/'cgroup.procs').read_text().split()],'LOCAL_CURRENT_MEMBERSHIP')
 out=C._run(['/usr/bin/systemctl','show',unit,'--property=MainPID,ControlGroup,RuntimeMaxUSec,ActiveEnterTimestampMonotonic,TimeoutStopUSec,KillMode,SendSIGKILL,FinalKillSignal'],ctx['checkout'],end,16384).decode();props=dict(x.split('=',1) for x in out.splitlines() if '=' in x)
 C.need(props.get('MainPID')==str(os.getpid()) and props.get('ControlGroup')==group and props.get('KillMode')=='control-group' and props.get('SendSIGKILL')=='yes' and props.get('FinalKillSignal') in ('9','SIGKILL'),'LOCAL_BLOCKING_OWN_KERNEL_SUPERVISOR')
 entered=int(props['ActiveEnterTimestampMonotonic']);hard=(entered+C._duration_us(props['RuntimeMaxUSec'])+C._duration_us(props['TimeoutStopUSec']))*1000;C.need(entered>0 and time.monotonic_ns()<hard<=end,'LOCAL_ORIGINAL_KERNEL_DEADLINE')
 return {'hostClass':'LocalUbuntu24.04x64','WSL2Observed':True,'kernelBuild':platform.release(),'pid':os.getpid(),'processStartIdentity':C._start(os.getpid()),'uid':os.getuid(),'gid':os.getgid(),'cgroup':group,'kernelLimits':limits,'supervisorPID':ctx['supervisorPID'],'supervisorStartIdentity':C._start(ctx['supervisorPID']),'hardOuterDeadlineNs':hard,'cpuEvidenceSha256':hashlib.sha256(raw).hexdigest(),'bootstrap':{'pythonVersion':platform.python_version(),'pythonExeSha256':C.digest(pathlib.Path(sys.executable).resolve()),'gitSha256':C.digest('/usr/bin/git'),'systemctlSha256':C.digest('/usr/bin/systemctl')}}

def bindings(ctx,profile,caps,admission,hashes,current,pins,rid):
 project=ctx['projectId'];C.need(caps.get('schema')=='sdk11-own-current-cap-evidence/v1' and caps.get('projectId')==project and caps.get('repository')==ctx['repository'],'LOCAL_OWN_CAP_EVIDENCE')
 C.need(caps.get('sourceCommit')==ctx['expectedSourceCommit'] and caps.get('sourceTree')==ctx['expectedSourceTree'] and caps.get('profileSha256')==hashes['profile'] and caps.get('controllerSha256')==hashes['controller'],'LOCAL_CURRENT_SOURCE_CAP_BINDING')
 C.need(caps.get('bootstrap')==current['bootstrap'],'LOCAL_CURRENT_BOOTSTRAP_BYTES');C.need(caps.get('rowStartedMonotonicNs')==ctx['rowStartedMonotonicNs'] and caps.get('deadlineMonotonicNs')==ctx['deadlineMonotonicNs'],'LOCAL_NO_CLOCK_RESET')
 sup=caps.get('supervisor',{});C.need(sup.get('pid')==ctx['supervisorPID']==current['supervisorPID'] and sup.get('processStartIdentity')==ctx['supervisorStartIdentity']==current['supervisorStartIdentity'] and sup.get('deadlineMonotonicNs')==ctx['deadlineMonotonicNs'],'LOCAL_ORIGINAL_LIVE_SUPERVISOR')
 worker=caps.get('worker',{});before=caps.get('beforeExec' if rid=='linux-x64' else 'heldBeforeExec',{})
 keys=('pid','processStartIdentity','uid','gid','cgroup','kernelLimits') if rid=='linux-x64' else ('pid','processStartIdentity','jobName','memoryMaxBytes','tasksMax','cpuRate','logicalHostCpu')
 C.need(all(worker.get(k)==current[k] for k in keys),'LOCAL_ACTUAL_MAINPID_START_CAPS');C.need(all(before.get(k)==current[k] for k in keys if k not in ('uid','gid')) and before.get('membershipBeforeRelease') is True and before.get('retainedStartHandle') is True and before.get('state')==('T' if rid=='linux-x64' else 'SUSPENDED'),'LOCAL_REAL_HELD_BEFORE_EXEC')
 C.need(admission.get('schema')=='sdk11-local-input-current/v1' and admission.get('state')=='OWN_CURRENT_INPUT_CONTEXT_BOUND' and admission.get('projectId')==project and admission.get('repository')==ctx['repository'] and admission.get('rid')==rid,'LOCAL_DISTINCT_NON_CI_CONTEXT_REQUIRED')
 C.need(admission.get('profileSha256')==hashes['profile'] and admission.get('controllerSha256')==hashes['controller'] and admission.get('ownCapsEvidenceSha256')==hashes['capsEvidence'] and admission.get('sourcePinTableSha256')==hashlib.sha256(C.canonical(pins['sourcePins'])).hexdigest(),'LOCAL_CONTEXT_HASH_BINDING')
 C.need(admission.get('qualifiedFactSha256')==FACTS[rid] and profile['localInputRoute'].get('qualifiedFactSha256')==FACTS[rid],'LOCAL_QUALIFIED_BYTE_HISTORY_REQUIRED')


def inspect_sdk(rid,root,context):
 ctx=dict(context);end=C._deadline_values(ctx,time.monotonic_ns());C.need(rid in FACTS,'LOCAL_RID');C.need(not any(os.environ.get(k) for k in ('GITHUB_ACTIONS','GITHUB_RUN_ID','RUNNER_ENVIRONMENT')),'LOCAL_CI_ENVIRONMENT_FORBIDDEN');checkout=pathlib.Path(ctx['checkout']).resolve();a=C._load('qualification_input_guard',C.PINS['guardSha256']);paths={}
 for key in ('controller','contract','profile','sourcePins'):
  paths[key]=a.scoped(ctx[key],checkout);C.need(paths[key].is_file(),'LOCAL_OWN_SOURCE_FILE')
 C.need(pathlib.Path(getattr(sys.modules['__main__'],'__file__','')).resolve()==paths['controller'].resolve(),'LOCAL_REAL_CAPPED_CALLER_CONTROLLER')
 for key in ('admission','capsEvidence'):paths[key]=pathlib.Path(ctx[key]).resolve();C.need(paths[key].is_file(),'LOCAL_OWN_CONTEXT_FILE')
 parent=paths['capsEvidence'].parent;C.need(paths['admission'].parent==parent,'LOCAL_OWN_CONTEXT_DIRECTORY')
 if os.name=='posix':C.need(parent.stat().st_uid==os.getuid() and parent.stat().st_mode&0o777==0o700,'LOCAL_PRIVATE_EVIDENCE_OWNER')
 profile=C._read(paths['profile'],65536);caps=C._read(paths['capsEvidence'],65536);admission=C._read(paths['admission'],65536);pins=C._read(paths['sourcePins'],1048576);hashes={k:C.digest(p) for k,p in paths.items()};memory,tasks,cpu=policy(profile,ctx['projectId'],rid);C.need(end-ctx['rowStartedMonotonicNs']<=profile['rowSeconds']*10**9,'LOCAL_PROFILE_ORIGINAL_DEADLINE')
 factpath=pathlib.Path(admission['qualifiedFactPath']);C.need(C.digest(factpath)==FACTS[rid],'LOCAL_EXACT_PRODUCER_HISTORY_BYTES');fact=C._read(factpath,1048576);names=['version','info','list-sdks','list-runtimes','compiler','restore','build','hello'];C.need([x['name'] for x in fact['commands']]==names and all(x['exitCode']==0 for x in fact['commands']),'LOCAL_COMPLETE_QUALIFICATION_HISTORY')
 root=pathlib.Path(root).resolve();C.need(root==pathlib.Path(fact['SDKPath']).resolve() and root.is_dir() and not root.is_symlink(),'LOCAL_EXISTING_POOL_ONLY_NO_COPY_OR_DOWNLOAD');file,sha=CATALOGS[rid];C.need(C.digest(HERE/file)==sha,'LOCAL_REVIEWED_CATALOG_BYTES');catalog=C._read(HERE/file);C.need(hashlib.sha256(C.canonical(catalog['members'])).hexdigest()==catalog['memberManifestSha256']==fact['memberManifestSha256'],'LOCAL_FULL_MEMBER_IDENTITY')
 own=parentfd=None;guard=C.absolute_deadline(ctx) if rid=='linux-x64' else contextlib.nullcontext(end)
 try:
  with guard:
   if rid=='linux-x64':
    current=linux_current(ctx,profile,end);parentfd=os.pidfd_open(ctx['supervisorPID']);C.need(not select.select([parentfd],[],[],0)[0] and C._start(ctx['supervisorPID'])==ctx['supervisorStartIdentity'],'LOCAL_LIVE_PARENT_PIDFD');expected={'memory.max':str(memory),'memory.swap.max':'0','pids.max':str(tasks),'cpu.max':str(cpu*100000)+' 100000'};C.need(current['kernelLimits']==expected,'LOCAL_ACTUAL_OWN_KERNEL_CAPS')
   else:
    import winreg
    W=C._load('normal_windows_input',C.PINS['windowsNormalHelperSha256']);own=W.OwnJob(C,ctx,caps,end);current=own.observe();v=sys.getwindowsversion()
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Windows NT\CurrentVersion') as key:version=winreg.QueryValueEx(key,'DisplayVersion')[0];build=str(winreg.QueryValueEx(key,'CurrentBuildNumber')[0])+'.'+str(winreg.QueryValueEx(key,'UBR')[0])
    C.need(sys.version_info[:3]==(3,12,10) and platform.machine().lower()=='amd64' and v.product_type==1 and version=='26H2' and build=='26300.9974','LOCAL_EXACT_TESTED_WINDOWS_CLASS');C.need(current['memoryMaxBytes']==memory and current['tasksMax']==tasks and current['cpuRate']==int(10000*cpu/current['logicalHostCpu']),'LOCAL_OWN_WINDOWS_CAPS_NOT_PRODUCER_CAPS');C.need(current['jobName'].startswith(profile['ownedJobPrefix']),'LOCAL_OWN_WINDOWS_JOB_PREFIX');cpudir=parent/('local-input-cpu-'+uuid.uuid4().hex);cpudir.mkdir();W.measure_cpu(C,cpudir);current.update(hostClass='ExperimentalLocalWindows26H2x64',formalDotnet11Support='NOT_CONFIRMED',bootstrap={'pythonVersion':platform.python_version(),'pythonExeSha256':C.digest(pathlib.Path(sys.executable).resolve()),'gitSha256':C.digest('C:/Program Files/Git/cmd/git.exe')})
   current.update(source(ctx,paths,pins,end));bindings(ctx,profile,caps,admission,hashes,current,pins,rid)
   if rid=='linux-x64':lm=C._load('materialize_qualification_linux',C.PINS['materializerSha256']);lm.verify_physical(root,catalog['members'])
   else:a.verify_tree(root,catalog['members'],rid,full=True)
   C._remaining(end)
   if own:own.observe()
   if parentfd is not None:C.need(not select.select([parentfd],[],[],0)[0],'LOCAL_PARENT_TERMINAL_DURING_INPUT')
   return {'schema':'sdk11-shared-local-input-receipt/v1','state':'OWN_CURRENT_REUSED_SDK_BYTES_VERIFIED_NO_TARGETS','projectId':ctx['projectId'],'repository':ctx['repository'],'rid':rid,'sdk':'11.0.100','runtime':'11.0.0','qualifiedByteFactSha256':FACTS[rid],'producerQualifiedOn':fact['qualifiedOn'],'producerSource':fact['source'],'ownCurrent':current,'ownBindingFileHashes':hashes,'memberManifestSha256':catalog['memberManifestSha256'],'SDKPath':str(root),'callerOwnsSDK':False,'readOnlyReuse':True,'absoluteOriginalDeadlineNs':end,'SDKExecutions':0,'networkRequests':0,'downloads':0,'extractions':0,'CI':False,'SDK_READY':False,'productAdmission':False,'scope':'SDK bytes/current input only. This is a distinct local envelope, never frozen63e CI admission, official Windows support, borrowed producer caps, package/graph/lock/native/notices/advisory or product acceptance.'}
 finally:
  if own:own.close()
  if parentfd is not None:os.close(parentfd)

def transport(rid,directory,context):
 # Explicit existing-pool request only. Never silently allocate or return an owned tree.
 receipt=inspect_sdk(rid,directory,context);return pathlib.Path(receipt['SDKPath']),receipt
