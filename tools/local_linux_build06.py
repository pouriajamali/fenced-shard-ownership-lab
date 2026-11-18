"""Own06 existing-root systemd starter plus held nonroot local Linux verify worker."""
import argparse,datetime,hashlib,json,os,re,secrets,select,signal,subprocess,sys,time
from pathlib import Path
import local_input06 as I
import local_build06 as B
need=I.need
FACT_SHA='ad63c4ad44af1844e1c937152294b07cdce9faccf2e2e7899cc221f2e485fb3c'
OS_ENV={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}
BUDGET=900

def start(pid):
 text=Path('/proc',str(pid),'stat').read_text();return 'proc-start:'+text[text.rfind(')')+2:].split()[19]

def kernel(unit):
 from ci_supported_kernel06 import system_caps
 return system_caps(unit,'generic64')

def show(unit):
 need(re.fullmatch('ownershiplab-ci-[0-9a-f]{16}-verify',unit) is not None,'LOCAL_FIXED_OWN_VERIFY_UNIT')
 r=subprocess.run(['/usr/bin/systemctl','show',unit,'--property=LoadState,MainPID,ControlPID,InvocationID,ControlGroup,ActiveState,SubState,Description'],capture_output=True,text=True,env=OS_ENV,timeout=5);need(len(r.stdout)+len(r.stderr)<=16384,'LOCAL_UNIT_METADATA_BOUND');return dict(x.split('=',1) for x in r.stdout.splitlines() if '=' in x)

def stopped(text):
 return text[text.rfind(')')+2:].split()[0] in ('T','t')

def actual_nonroot_status(text):
 fields=dict(x.split(':',1) for x in text.splitlines() if ':' in x)
 need(all(fields.get(k,'').split()==['1000']*4 for k in ('Uid','Gid')),'ACTUAL_ALL_NONROOT_UID_GID_IDS')

def population(group):
 try:
  fields=dict(x.split() for x in (group/'cgroup.events').read_text().splitlines());need(fields.get('populated') in ('0','1'),'ACTUAL_CGROUP_POPULATED_FIELD');return int(fields['populated'])
 except FileNotFoundError:
  need(not group.exists(),'LIVE_CGROUP_WITHOUT_EVENTS');return 0

def ledger(s,now):
 need(s.get('purpose')=='OWN06_LOCAL_LINUX_VERIFY' and s.get('projectId')=='06' and s.get('repository')==I.REPOSITORY,'OWN_LINUX_PURPOSE')
 need(type(s.get('startNs')) is int and type(s.get('endNs')) is int and 0<s['startNs']<=now<s['endNs'] and s['endNs']-s['startNs']==900*10**9,'ORIGINAL_AFTER_CLAIM_LINUX900')
 need(type(s.get('supervisorPID')) is int and s['supervisorPID']>0 and str(s.get('supervisorStartIdentity','')).startswith('proc-start:') and re.fullmatch('ownershiplab-ci-[0-9a-f]{16}-verify',s.get('unit','')) is not None,'OWN_LINUX_PARENT_UNIT_IDENTITY')

def exact_lease(s):
 path=B.input_path(I.LEASE);need(I.digest(path)==s['leaseSha256'],'EXACT_LINUX_CANONICAL_BYTES');h=I.read(path)
 need(h.get('projectId')=='06' and h.get('phase')=='LOCAL_LINUX_VERIFY' and h.get('ownerPID')==s['supervisorPID'] and h.get('ownerProcessStartIdentity')==s['supervisorStartIdentity'] and h.get('randomToken')==s['token'] and h.get('sourceCommit')==s['commit'] and h.get('receiptDirectory')==s['out'],'EXACT_LINUX_OWN_LIVE_LEASE')

def context(root,controller,out,s,caps,held):
 profile=root/'profiles/local-linux-build06.json';pins=root/'tools/ci06-source-pins.json';fact=B.input_path(I.FACT.parent/'LOCAL-LINUX-HOST-FACT.json');need(I.digest(fact)==FACT_SHA,'EXACT_LINUX_QUALIFIED_BYTES_HISTORY')
 boot={'pythonVersion':'.'.join(map(str,sys.version_info[:3])),'pythonExeSha256':I.digest(Path(sys.executable).resolve()),'gitSha256':I.digest('/usr/bin/git'),'systemctlSha256':I.digest('/usr/bin/systemctl')};pid=os.getpid();identity=start(pid);who={'pid':pid,'processStartIdentity':identity,'uid':os.getuid(),'gid':os.getgid(),'cgroup':caps['membership'].strip()[3:],'kernelLimits':caps['kernel']}
 proof={'schema':'sdk11-own-current-cap-evidence/v1','projectId':'06','repository':I.REPOSITORY,'sourceCommit':s['commit'],'sourceTree':s['tree'],'profileSha256':I.digest(profile),'controllerSha256':I.digest(controller),'bootstrap':boot,'worker':who,'beforeExec':{'pid':held['pid'],'processStartIdentity':held['processStartIdentity'],'cgroup':held['cgroup'],'kernelLimits':held['kernelLimits'],'state':'T','membershipBeforeRelease':held['membershipBeforeRelease'],'retainedStartHandle':held['retainedStartHandle']},'supervisor':{'pid':s['supervisorPID'],'processStartIdentity':s['supervisorStartIdentity'],'deadlineMonotonicNs':s['endNs']},'rowStartedMonotonicNs':s['startNs'],'deadlineMonotonicNs':s['endNs']}
 cp=out/'own-current-caps.json';ap=out/'local-input-context.json';I.write(cp,proof);I.write(ap,{'schema':'sdk11-local-input-current/v1','state':'OWN_CURRENT_INPUT_CONTEXT_BOUND','projectId':'06','repository':I.REPOSITORY,'rid':'linux-x64','qualifiedFactPath':str(fact),'qualifiedFactSha256':FACT_SHA,'profileSha256':I.digest(profile),'controllerSha256':I.digest(controller),'ownCapsEvidenceSha256':I.digest(cp),'sourcePinTableSha256':hashlib.sha256(I.canonical(I.read(pins)['sourcePins'])).hexdigest()})
 return {'projectId':'06','repository':I.REPOSITORY,'checkout':str(root),'controller':str(controller),'contract':str(root/'tools/ci06-normal-contract.json'),'profile':str(profile),'sourcePins':str(pins),'admission':str(ap),'capsEvidence':str(cp),'expectedSourceCommit':s['commit'],'expectedSourceTree':s['tree'],'rowStartedMonotonicNs':s['startNs'],'deadlineMonotonicNs':s['endNs'],'supervisorPID':s['supervisorPID'],'supervisorStartIdentity':s['supervisorStartIdentity']},Path(I.read(fact)['SDKPath'])

def retained_dependencies(sdk,fact):
 rows=fact['nativePrerequisites'];need([x['name'] for x in rows]==['dotnet','host/fxr/11.0.0/libhostfxr.so','shared/Microsoft.NETCore.App/11.0.0/libcoreclr.so','shared/Microsoft.NETCore.App/11.0.0/libclrjit.so'],'EXACT_QUALIFIED_LINUX_NATIVE_CLOSURE');result=[]
 for row in rows:
  prefix='ObservedExistingHostDependenciesNoInventedELFSignature:';need(row['status'].startswith(prefix),'QUALIFIED_NATIVE_DEPENDENCY_EVIDENCE_FORMAT');current=[]
  for dep in json.loads(row['status'][len(prefix):]):
   need(all(Path(dep[k]).name==dep[k] and dep[k] not in ('.','..') and chr(92) not in dep[k] for k in ('import','resolvedName')),'EXACT_QUALIFIED_SONAME_ONLY')
   target=(sdk/row['name']).parent/dep['import']
   if not target.is_file():target=Path('/lib/x86_64-linux-gnu')/dep['resolvedName']
   need(target.is_file() and I.digest(target)==dep['sha256'],'CURRENT_OS_DEPENDENCY_BYTES_MATCH_QUALIFICATION');current.append({'import':dep['import'],'path':str(target),'sha256':dep['sha256']})
  result.append({'name':row['name'],'retainedEvidenceSha256':row['evidenceSha256'],'currentDependencies':current})
 return {'state':'CURRENT_PHYSICAL_NATIVE_DEPENDENCY_BYTES_MATCH_RETAINED_QUALIFICATION','packagesInstalled':0,'loaderCommandsReplayed':0,'scope':'Physical byte reuse only; no invented ELF signature or general runtime acceptance.','nativeClosure':result}

def worker(root,controller,spec):
 s=I.read(spec);ledger(s,time.monotonic_ns());need(os.getuid()==os.getgid()==1000 and I.digest(controller)==s['controllerSha256'] and str(root)==s['checkout'],'OWN_NONROOT_CURRENT_SOURCE');out=spec.parent;need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['bootId'],'SAME_ACTUAL_OWN_BOOT');need(out==Path(s['out']) and out.parent==Path('/home/ubuntu/.ownership06-local-verify') and out.stat().st_uid==1000 and out.stat().st_mode&0o777==0o700,'OWN_PRIVATE_NATIVE_DIRECTORY');exact_lease(s);caps=kernel(s['unit']);pid=os.getpid();inv=os.environ.get('INVOCATION_ID');need(re.fullmatch('[0-9a-f]{32}',inv or '') is not None,'CURRENT_SYSTEMD_INVOCATION')
 I.write(out/'stopped-worker.json',{'pid':pid,'processStartIdentity':start(pid),'unit':s['unit'],'token':s['token'],'invocationId':inv,'uid':os.getuid(),'gid':os.getgid(),'cgroup':caps['membership'].strip()[3:],'kernelLimits':caps['kernel']});os.kill(pid,signal.SIGSTOP)
 held=I.read(out/'held-before-continue.json');need(held['pid']==pid and held['processStartIdentity']==start(pid) and held['unit']==s['unit'] and held['invocationId']==inv and held['token']==s['token'] and held['retainedStartHandle'] is True and held['membershipBeforeRelease'] is True,'ACTUAL_HELD_BEFORE_EXEC_LINUX');need(kernel(s['unit'])==caps,'UNCHANGED_ACTUAL_LINUX_CAPS');exact_lease(s)
 ctx,sdk=context(root,controller,out,s,caps,held);fact=I.read(B.input_path(I.FACT.parent/'LOCAL-LINUX-HOST-FACT.json'));I.write(out/'current-native-dependency-bytes.json',retained_dependencies(sdk,fact));local=I.load(root,'local_sdk11_input',I.FACADE_SHA);receipt=local.inspect_sdk('linux-x64',sdk,ctx);I.write(out/'current-sdk-input.json',receipt);v=B.admission(root,int(time.time()));need(I.digest(root/B.MANIFEST)==s['inputAdmissionSha256'],'OWN_LINUX_ADMISSION_BYTES');config=B.prepare_feed(root,out,v);dotnet=sdk/'dotnet';cache=out/'cache';cache.mkdir();env=dict(OS_ENV)
 for key,name in [('DOTNET_CLI_HOME','home'),('NUGET_PACKAGES','packages'),('NUGET_HTTP_CACHE_PATH','http'),('NUGET_PLUGINS_CACHE_PATH','plugins'),('TEMP','tmp'),('TMP','tmp')]:
  p=cache/name;p.mkdir(exist_ok=True);env[key]=str(p)
 env.update(PATH=str(sdk)+':/usr/bin:/bin',TMPDIR=str(cache/'tmp'),DOTNET_ROOT=str(sdk),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='true',MSBuildEnableWorkloadResolver='false',DOTNET_CLI_USE_MSBUILD_SERVER='0',MSBUILDDISABLENODEREUSE='1',DOTNET_PROCESSOR_COUNT='2',DisableTransitiveFrameworkReferenceDownloads='true')
 import bounded_fixture as bounds
 from profile_limits import ResourceWatch,validate_resource_counters
 records=[];watch=ResourceWatch(caps)
 def run(argv,extra=None):
  exact_lease(s);left=(s['endNs']-time.monotonic_ns())/1e9;need(left>35,'LINUX_SAME_OUTER_CLEANUP_RESERVE');folder=out/('command-'+str(len(records)+1).zfill(2));folder.mkdir();localenv=dict(env);localenv.update(extra or {})
  bounds.run(list(map(str,argv)),cwd=root,env=localenv,evidence=folder,seconds=min(300,int(left-30)),disk_root=out,other_disk_roots=(root/'src',root/'tests'));watch.sample();record=I.read(folder/'process.json');record['evidence']=str(folder);records.append(record);return record
 try:
  stage=s.get('stage','verify');need(stage in ('verify','package'),'FINITE_LINUX_P3_STAGE');reused=B.prior_linux_units(root) if stage=='package' else None
  for i,argv in enumerate(B.plan(stage,dotnet,config,cache/'packages',out/'unit.xml'),1):
   run(argv)
   if i==3:B.graph(root,v)
  locks=B.graph(root,v)
  if stage=='verify':B.unit_count(out/'unit.xml')
  package=B.post_verify(root,out,s['commit'],dotnet,config,cache,run,rid='linux-x64',oracles=stage=='verify');I.write(out/'sdk-pool-postcondition.json',B.sdk_pool_postcondition(root,sdk,'linux-x64'));need(kernel(s['unit'])==caps,'UNCHANGED_LINUX_CAPS_AFTER_BUILD');B.admission(root,int(time.time()));exact_lease(s)
  I.write(out/'worker-result.json',{'state':'OWN06_LOCAL_LINUX_'+stage.upper()+'_COMMANDS_PASSED','sourceCommit':s['commit'],'sourceTree':s['tree'],'SDKExecutions':6 if stage=='package' else 10,'reusedVerification':reused,'commandGroups':len(records),'nativeLinuxPackage':package,'actualLocks':locks,'productAdmission':False,'Actions':0,'scope':'Own native Linux build/unit/package verification only; original packaged16/SQL/native128/R06paired/five profiles and signing/public release remain separately required.'})
 finally:
  counters=watch.finish();I.write(out/'resource-counters.json',counters);validate_resource_counters(counters)

def main(root,controller,argv):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--local-linux-verify',action='store_true');p.add_argument('--local-linux-package',action='store_true');p.add_argument('--local-linux-worker',type=Path);p.add_argument('--expected-commit');a=p.parse_args(argv);root=Path(root).resolve();controller=Path(controller).resolve()
 if a.local_linux_worker:need(not a.local_linux_verify and not a.local_linux_package and a.expected_commit is None,'LINUX_WORKER_ARGS');return worker(root,controller,a.local_linux_worker)
 need(a.local_linux_verify!=a.local_linux_package and a.expected_commit and sys.platform=='linux' and os.getuid()==0 and Path('/run/systemd/private').exists(),'EXISTING_ROOT_OS_STARTER_ONLY');need(not any(os.environ.get(k) for k in ('GITHUB_ACTIONS','GITHUB_RUN_ID','RUNNER_ENVIRONMENT')),'DISTINCT_LOCAL_NOT_CI');B.admission(root,int(time.time()))
 local=I.load(root,'local_sdk11_input',I.FACADE_SHA);prefix=local.git_prefix(root,I.REPOSITORY)
 def git(*args):
  r=subprocess.run([*prefix,*args],env=OS_ENV,capture_output=True,timeout=10);need(r.returncode==0 and len(r.stdout)+len(r.stderr)<=1048576,'OWN_LINUX_SOURCE_METADATA');return r.stdout.decode().strip()
 stage='package' if a.local_linux_package else 'verify'
 if stage=='package':B.prior_linux_units(root)
 head=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}');need(head==a.expected_commit and not git('status','--porcelain=v1','--untracked-files=all'),'CLEAN_EXPECTED_LINUX_SOURCE');lease=B.input_path(I.LEASE);need(I.digest(lease.with_name('LEASE-PROTOCOL.json'))==I.PROTOCOL_SHA,'CANONICAL_PROTOCOL_LINUX')
 base=Path('/home/ubuntu/.ownership06-local-verify');need(not base.is_symlink(),'PRIVATE_LINUX_BASE');
 if not base.exists():base.mkdir(mode=0o700);os.chown(base,1000,1000)
 need(base.stat().st_uid==1000 and base.stat().st_gid==1000 and base.stat().st_mode&0o777==0o700,'EXISTING_BASE_OWN_0700');out=base/(stage+'-'+secrets.token_hex(12));out.mkdir(mode=0o700);os.chown(out,1000,1000);token=secrets.token_hex(32);unit='ownershiplab-ci-'+secrets.token_hex(8)+'-verify';identity=start(os.getpid());holder={'projectId':'06','randomToken':token,'ownerOS':'Linux','ownerPID':os.getpid(),'ownerProcessStartIdentity':identity,'phase':'LOCAL_LINUX_VERIFY','bootId':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'startedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'receiptDirectory':str(out),'timeoutSeconds':900,'sourceCommit':head}
 try:I.write(lease,holder)
 except FileExistsError:I.write(out/'receipt.json',{'state':'BUSY_NOT_CLAIMED','SDKExecutions':0});return 20
 started=time.monotonic_ns();end=started+BUDGET*10**9;s={'stage':stage,'purpose':'OWN06_LOCAL_LINUX_VERIFY','projectId':'06','repository':I.REPOSITORY,'checkout':str(root),'commit':head,'tree':tree,'controllerSha256':I.digest(controller),'startNs':started,'endNs':end,'supervisorPID':os.getpid(),'supervisorStartIdentity':identity,'token':token,'unit':unit,'out':str(out),'leaseSha256':I.digest(lease),'bootId':holder['bootId'],'inputAdmissionSha256':I.digest(root/B.MANIFEST)};spec=out/'private-spec.json';proc=pidfd=None;held=None;continued=False;result={'state':'HOLD','sourceCommit':head,'sourceTree':tree,'Actions':0,'productAdmission':False,'released':False};group=Path('/sys/fs/cgroup/system.slice')/(unit+'.service')
 try:
  I.write(spec,s);need(show(unit).get('LoadState')=='not-found' and not group.exists(),'OWN_UNIT_ABSENT');left=int((end-time.monotonic_ns())/1e9);need(left>40,'LINUX_WORK_TERMINAL_RESERVE')
  args=['/usr/bin/systemd-run','--wait','--collect','--pipe','--unit='+unit,'--uid=1000','--gid=1000','--property=Description=ownership06-local-'+token,'--property=MemoryMax=4294967296','--property=MemorySwapMax=0','--property=CPUQuota=200%','--property=CPUQuotaPeriodSec=100ms','--property=TasksMax=64','--property=RuntimeMaxSec='+str(left-30),'--property=TimeoutStopSec=5','--property=KillMode=control-group','--property=SendSIGKILL=yes','--property=FinalKillSignal=SIGKILL','--property=WorkingDirectory='+str(root),*[ '--setenv='+k+'='+v for k,v in OS_ENV.items()],sys.executable,'-I','-S','-B',str(controller),'--local-linux-worker',str(spec)]
  with (out/'launcher-stdout.log').open('xb') as stdout,(out/'launcher-stderr.log').open('xb') as stderr:
   proc=subprocess.Popen(args,cwd=root,env=OS_ENV,stdout=stdout,stderr=stderr);until=min(end-30*10**9,time.monotonic_ns()+20*10**9)
   while not (out/'stopped-worker.json').is_file():need(proc.poll() is None and time.monotonic_ns()<until,'HELD_LINUX_START_DEADLINE');time.sleep(.05)
   held=I.read(out/'stopped-worker.json');pid=held['pid'];need(type(pid) is int and pid>0 and held['token']==token and held['unit']==unit and held['uid']==held['gid']==1000,'OWN_STOPPED_WORKER');pidfd=os.pidfd_open(pid)
   while not stopped(Path('/proc',str(pid),'stat').read_text()):need(proc.poll() is None and time.monotonic_ns()<until,'ACTUAL_STOPPED_STATE');time.sleep(.01)
   actual_nonroot_status(Path('/proc',str(pid),'status').read_text())
   obs=show(unit);need(start(pid)==held['processStartIdentity'] and obs.get('MainPID')==str(pid) and obs.get('InvocationID')==held['invocationId'] and obs.get('ControlGroup')==held['cgroup'] and Path('/proc',str(pid),'cgroup').read_text().strip()=='0::'+held['cgroup'],'ACTUAL_MANAGER_START_MEMBERSHIP');actual={n:(group/n).read_text().strip() for n in ('memory.max','memory.swap.max','pids.max','cpu.max')};need(actual==held['kernelLimits']=={'memory.max':'4294967296','memory.swap.max':'0','pids.max':'64','cpu.max':'200000 100000'},'ACTUAL_HELD_GENERIC64_CAPS');I.write(out/'held-before-continue.json',{**held,'retainedStartHandle':True,'membershipBeforeRelease':True});continued=True;signal.pidfd_send_signal(pidfd,signal.SIGCONT)
   proc.wait(timeout=max(.1,(end-time.monotonic_ns())/1e9-10));need(proc.returncode==0,'LOCAL_LINUX_WORKER_NONZERO');value=I.read(out/'worker-result.json');need(value['state']=='OWN06_LOCAL_LINUX_'+stage.upper()+'_COMMANDS_PASSED' and value['sourceCommit']==head,'CURRENT_LINUX_WORKER_RESULT');result.update(value)
 except Exception as exc:result.update(errorType=type(exc).__name__,error=str(exc)[:300])
 finally:
  # Only this random own unit is stopped. No reset-failed/foreign lease/unit operations.
  try:
   if group.exists():
    obs=show(unit);need(obs.get('Description')=='ownership06-local-'+token and (held is None and not continued or held is not None and obs.get('InvocationID')==held['invocationId']),'OWN_UNIT_INCARNATION_BEFORE_STOP');subprocess.run(['/usr/bin/systemctl','stop',unit],env=OS_ENV,capture_output=True,timeout=15,check=True)
   if proc is not None:proc.wait(timeout=10)
   observed=show(unit);population_value=population(group);exited=pidfd is not None and bool(select.select([pidfd],[],[],0)[0]);absent=observed.get('LoadState')=='not-found' and not group.exists();terminal=type(population_value) is int and population_value==0 and proc is not None and proc.poll() is not None and (exited or held is None and not continued and absent) and (absent or observed.get('MainPID')=='0' and observed.get('ControlPID')=='0');result['terminal']={'population':population_value,'heldPidfdExited':exited,'workerContinued':continued,'noSDKReleaseBeforeHeld':held is None and not continued,'manager':observed,'ownedLauncherExited':proc is not None and proc.poll() is not None,'verified':terminal};I.write(out/'outcome-before-release.json',result)
   if terminal and I.read(lease)==holder and start(os.getpid())==identity:lease.unlink();result['released']=True
   else:result['releaseError']='POSITIVE_OWN_TERMINAL_OR_EXACT_LEASE_MISSING'
  except Exception as exc:result['releaseError']=type(exc).__name__+':'+str(exc)[:200]
  if pidfd is not None:os.close(pidfd)
  result['elapsedSeconds']=(time.monotonic_ns()-started)/1e9;result['whole900Met']=result['elapsedSeconds']<=900;I.write(out/'receipt.json',result)
 print(json.dumps({'state':result['state'],'released':result['released'],'receipt':str(out/'receipt.json'),'Actions':0}));need(result['state']!='HOLD' and result['released'] and result['whole900Met'],'LOCAL_LINUX_VERIFY_HOLD');return 0
