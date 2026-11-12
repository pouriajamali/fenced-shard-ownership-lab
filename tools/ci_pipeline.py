"""DRAFT: finite CI stages. No generic command CLI, installation or public writes.
Apply/run only after the exact coordinator extension gate; no local M1 replay.
"""
import argparse,hashlib,json,os,platform,re,selectors,secrets,shutil,signal,socket,stat,subprocess,sys,time,urllib.parse,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import bounded_actionlint as job
import bounded_fixture as bounds
from profile_limits import native_runtime,ResourceWatch,validate_resource_counters
BUNDLE={'futureUrl': 'https://github.com/pouriajamali/fenced-shard-ownership-lab/releases/download/tooling-etcd-v3.7.3-go1.26.11-r1/etcd-serving-v3.7.3-go1.26.11-linux-amd64-r1.zip', 'bytes': 39244465, 'sha256': '95ba2468a63859b086ec331cce5b66ef967b5360b1808e18677e163c81c51c51', 'entries': [{'path': 'ETCD-BUILD.json', 'bytes': 990, 'sha256': '8db0fc41dacf47e1b52e3743f46892932c3482a2e0b8e6e48234497d4889e235', 'mode': '0644'}, {'path': 'admission/advisory-snapshot.json', 'bytes': 45395, 'sha256': '139377ee21b074ab752060a02cbd97645db880d50b69415b5125ffb028be8f13', 'mode': '0644'}, {'path': 'admission/binary-audit.jsonl', 'bytes': 910713, 'sha256': 'd7706e8221267486ae5ba92f15ba44760b2c19185f32ce9fec34524593d4349d', 'mode': '0644'}, {'path': 'admission/buildinfo.json', 'bytes': 8390, 'sha256': '4141ff1543a3e5fecea025d119b1ad719a01843817012073b6d58b6d113945ed', 'mode': '0644'}, {'path': 'admission/licenses.json', 'bytes': 672427, 'sha256': '2669a151b0e3f30d82a21bf04bf7b584631045514d6dd86250d745181bbbac78', 'mode': '0644'}, {'path': 'admission/module-graph.json', 'bytes': 299649, 'sha256': 'b6825411e676482faf08301730b93aa8fef0f596379d5f8a38051c486f769f26', 'mode': '0644'}, {'path': 'admission/reproducibility.json', 'bytes': 1646, 'sha256': '42c816155b16648af275ae2ffec300995d8188ae13ec36ff0c5e3b9be6eb8522', 'mode': '0644'}, {'path': 'admission/source-audit.jsonl', 'bytes': 910500, 'sha256': '59693cea515bdafd7a7ae7aa43000c3b7822b02333eb3cb11868825c7e966734', 'mode': '0644'}, {'path': 'etcd-source-go1.26.11/etcd', 'bytes': 35702972, 'sha256': '720420f5f09bf4acb5b32365eddd7594764fb74e3e2b22aa7d1ae67b844f2af6', 'mode': '0755'}, {'path': 'notices/ETCD-FIXTURE-SOURCES.json', 'bytes': 672427, 'sha256': '2669a151b0e3f30d82a21bf04bf7b584631045514d6dd86250d745181bbbac78', 'mode': '0644'}, {'path': 'notices/GO-VULNDB-LICENSE.txt', 'bytes': 16215, 'sha256': '79c7317f4757f42cc3539abe8955d2021215a8510ffdbf71494dad051939cdaf', 'mode': '0644'}, {'path': 'notices/VULNDB-ATTRIBUTION.txt', 'bytes': 1557, 'sha256': '768316b64949abcabd2e183c57b378504078249c1ebf32cbc61c5a906594ceb7', 'mode': '0644'}], 'lockSha256': '47fbc300bda7c5350c771bd7f9ee46ffc1d086e8d4d36a7e11d18ad545fdc30c', 'binarySha256': '720420f5f09bf4acb5b32365eddd7594764fb74e3e2b22aa7d1ae67b844f2af6', 'binaryBytes': 35702972}
WALL={'policy':240,'verify':900,'prepare':240,'runtime':1080,'aggregate':480}
LOG_MAX=134217728
ART=ROOT/'artifacts'

def need(v,why):
 if not v:raise RuntimeError('HOLD_'+why)

def write(path,value):
 with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())

def env_for_child():
 names=['PATH','SystemRoot','WINDIR','COMSPEC','PATHEXT','HOME','USERPROFILE','APPDATA','LOCALAPPDATA','LANG','GITHUB_ACTIONS','GITHUB_EVENT_NAME','GITHUB_REF','GITHUB_SHA','GITHUB_EVENT_PATH','GITHUB_OUTPUT','GITHUB_STEP_SUMMARY','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_JOB','GITHUB_WORKSPACE','RUNNER_TEMP','RUNNER_OS']
 env={k:os.environ[k] for k in names if k in os.environ}
 cache=ART/'ci-cache'
 for name in ['home','packages','http','plugins','tmp']:(cache/name).mkdir(parents=True,exist_ok=True)
 for k,name in [('DOTNET_CLI_HOME','home'),('NUGET_PACKAGES','packages'),('NUGET_HTTP_CACHE_PATH','http'),('NUGET_PLUGINS_CACHE_PATH','plugins'),('TEMP','tmp'),('TMP','tmp')]:env[k]=str(cache/name)
 # Linux owned fixture scratch must have native0700 semantics, not a drive mount.
 env['TMPDIR']=str(cache/'tmp') if os.name=='nt' else '/tmp'
 env.update(PYTHONOPTIMIZE='0',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='true',MSBuildEnableWorkloadResolver='false',DOTNET_CLI_USE_MSBUILD_SERVER='0',MSBUILDDISABLENODEREUSE='1',DOTNET_PROCESSOR_COUNT='1',DOTNET_MULTILEVEL_LOOKUP='0',DisableTransitiveFrameworkReferenceDownloads='true')
 return env


# Explicit per-service values only. No manager import-environment/set-environment.
SERVICE_ENV_ALLOWLIST=frozenset(('PATH','SystemRoot','WINDIR','COMSPEC','PATHEXT','HOME','USERPROFILE','APPDATA','LOCALAPPDATA','LANG','GITHUB_ACTIONS','GITHUB_EVENT_NAME','GITHUB_REF','GITHUB_SHA','GITHUB_EVENT_PATH','GITHUB_OUTPUT','GITHUB_STEP_SUMMARY','GITHUB_RUN_ID','GITHUB_RUN_ATTEMPT','GITHUB_JOB','GITHUB_WORKSPACE','RUNNER_TEMP','RUNNER_OS','DOTNET_CLI_HOME','NUGET_PACKAGES','NUGET_HTTP_CACHE_PATH','NUGET_PLUGINS_CACHE_PATH','TEMP','TMP','TMPDIR','DOTNET_CLI_TELEMETRY_OPTOUT','DOTNET_GENERATE_ASPNET_CERTIFICATE','DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE','MSBuildEnableWorkloadResolver','DOTNET_CLI_USE_MSBUILD_SERVER','MSBUILDDISABLENODEREUSE','DOTNET_PROCESSOR_COUNT','DOTNET_MULTILEVEL_LOOKUP','DisableTransitiveFrameworkReferenceDownloads','PYTHONOPTIMIZE'))
SERVICE_ENV_UNSET=('GITHUB_TOKEN','GH_TOKEN','ACTIONS_RUNTIME_TOKEN','ACTIONS_ID_TOKEN_REQUEST_TOKEN','OWNERSHIP_LAB_DB','HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','http_proxy','https_proxy','all_proxy','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP')

def service_environment_flags(env,commit):
 need(type(env) is dict and set(env)<=SERVICE_ENV_ALLOWLIST,'SERVICE_ENV_FIXED_KEYS_ONLY')
 need(env.get('GITHUB_ACTIONS')=='true' and env.get('GITHUB_RUN_ATTEMPT')=='1' and env.get('GITHUB_SHA')==commit,'SERVICE_ENV_EXACT_CI_SOURCE')
 need(env.get('PYTHONOPTIMIZE') in ('0','1'),'SERVICE_ENV_FINITE_OPTIMIZATION')
 need(all(type(k) is str and type(v) is str and len(v.encode('utf-8'))<=8192 and not any(c in v for c in ('\0','\r','\n')) for k,v in env.items()),'SERVICE_ENV_VALUE_FRAME')
 need(sum(len((k+'='+v).encode('utf-8')) for k,v in env.items())<=65536,'SERVICE_ENV_TOTAL_CAP')
 # Each NAME=VALUE is one argv element. Values are never shell-interpolated/logged.
 return ['--setenv='+k+'='+env[k] for k in sorted(env)]+['--property=UnsetEnvironment='+' '.join(SERVICE_ENV_UNSET)]

def sdk(env):
 pin=json.loads((ROOT/'global.json').read_bytes())
 need(pin=={'sdk':{'version':'10.0.404','rollForward':'disable'}},'SDK_SOURCE_PIN')
 if os.name=='nt':
  from ci_windows_sdk import stage_sdk
  return stage_sdk(env)
 exe=shutil.which('dotnet',path=env['PATH']);need(exe,'PREINSTALLED_SDK_REQUIRED_NO_SETUP_FALLBACK')
 exe=Path(exe).resolve();need((exe.parent/'sdk/10.0.404/dotnet.dll').is_file(),'PREINSTALLED_404_REQUIRED_NO_INSTALL')
 # First project SDK invocation is the bounded locked restore, never a health probe.
 return str(exe)

def current_caps(stage):
 if stage=='runtime':return native_runtime('native-linux-16')
 caps=bounds.kernel_limits();need(caps['kernel']=={'memory.max':'4294967296','memory.swap.max':'0','pids.max':'64','cpu.max':'200000 100000'},'GENERIC64_EXACT_BUDGET');return caps

def runtime_command(argv,env,evidence,seconds):
 """One128-task command only: fixed packaged integration, stopped before exec."""
 caps=native_runtime('native-linux-16');watch=ResourceWatch(caps);start=time.monotonic();pipes=[os.pipe(),os.pipe()];sel=selectors.DefaultSelector();files=[];pid=None;code=None;logged=0;proof=None
 try:
  readers=[];writers=[]
  for pair,name in zip(pipes,['stdout.log','stderr.log']):
   reader,writer=pair;readers.append(reader);writers.append(os.fdopen(writer,'wb',buffering=0));dest=(evidence/name).open('xb');files.append(dest);os.set_blocking(reader,False);sel.register(reader,selectors.EVENT_READ,dest)
  cap={'cgroup':caps['membership'].strip()[3:],'kernelLimits':caps['kernel']}
  child,proof=job.stopped_linux_child(argv,ROOT,env,writers[0],writers[1],(),cap);pid=child.pid
  for writer in writers:writer.close()
  while True:
   ended=os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
   for key,_ in sel.select(.05):
    data=os.read(key.fd,65536)
    if not data:sel.unregister(key.fd);os.close(key.fd)
    else:need(logged+len(data)<=LOG_MAX,'RUNTIME_LOG_CAP_BEFORE_WRITE');key.data.write(data);logged+=len(data)
   watch.sample();bounds.workspace_limit([ART]);need(time.monotonic()-start<=seconds,'RUNTIME_WALL_CAP')
   if ended is not None and not sel.get_map():code=ended.si_status if ended.si_code==os.CLD_EXITED else -ended.si_status;break
 finally:
  # Retain the child zombie until its own group is terminated; no PID-reuse kill.
  if pid is not None:bounds._kill_owned_group(pid);os.waitpid(pid,0)
  for writer in locals().get('writers',[]):
   if not writer.closed:writer.close()
  for key in list(sel.get_map().values()):sel.unregister(key.fd);os.close(key.fd)
  sel.close()
  for f in files:f.close()
  metrics=watch.finish();write(evidence/'process.json',dict(argv=argv,exitCode=code,actualCaps=caps,childBeforeExec=proof,resourceCounters=metrics,savedLogBytes=logged))
 validate_resource_counters(metrics);need(code==0,'RUNTIME_NONZERO_NO_RETRY')
 return (evidence/'stdout.log').read_bytes()

def command(argv,env,folder,seconds,stage):
 folder.mkdir(exist_ok=False);bounds.workspace_limit([ART])
 if os.name=='nt':
  job.run(argv,cwd=ROOT,env=env,timeout=seconds,evidence=folder/'job')
  p=folder/'job';need(sum((p/n).stat().st_size for n in ['stdout.log','stderr.log'])<=LOG_MAX,'LOG_ACCEPTANCE_CAP');bounds.workspace_limit([ART]);return (p/'stdout.log').read_bytes()
 if stage=='runtime':return runtime_command(argv,env,folder,seconds)
 watch=ResourceWatch(current_caps(stage))
 try:bounds.run(argv,cwd=ROOT,env=env,evidence=folder,seconds=seconds,disk_root=ART)
 finally:metrics=watch.finish();write(folder/'resource-counters.json',metrics)
 validate_resource_counters(metrics)
 return (folder/'stdout.log').read_bytes()

BUNDLE_HOSTS=frozenset({'github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'})

class FixedBundleRedirect(urllib.request.HTTPRedirectHandler):
 max_redirections=5
 max_repeats=2
 def redirect_request(self,request,fp,code,msg,headers,newurl):
  target=urllib.parse.urlsplit(urllib.parse.urljoin(request.full_url,newurl))
  need(target.scheme=='https' and target.hostname in BUNDLE_HOSTS and target.port in (None,443) and target.username is None and target.password is None,'FIXED_BUNDLE_REDIRECT_BEFORE_REQUEST')
  return super().redirect_request(request,fp,code,msg,headers,target.geturl())

def fetch_bundle():
 from check_etcd_fixture import reference,identity
 lock=reference();need(hashlib.sha256((ROOT/'tools/etcd-build.lock.json').read_bytes()).hexdigest()==BUNDLE['lockSha256'],'SOURCE_HELD_FIXTURE_LOCK')
 need(lock['binarySha256']==BUNDLE['binarySha256'] and lock['binaryBytes']==BUNDLE['binaryBytes'],'SOURCE_HELD_FIXTURE_IMAGE')
 work=ART/'ci-fixture';work.mkdir(exist_ok=False);raw=work/'transport.zip';start=time.monotonic();total=0;digest=hashlib.sha256()
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),FixedBundleRedirect())
 with opener.open(urllib.request.Request(BUNDLE['futureUrl'],headers={'User-Agent':'ownership-ci-fixed-serving-bundle/1'}),timeout=20) as response,raw.open('xb') as output:
  need(response.status==200 and urllib.parse.urlsplit(response.url).scheme=='https' and urllib.parse.urlsplit(response.url).hostname in ['github.com','release-assets.githubusercontent.com','objects.githubusercontent.com'],'FIXED_BUNDLE_RESPONSE')
  while True:
   data=response.read(65536)
   if not data:break
   total+=len(data);need(total<=BUNDLE['bytes'] and total<=67108864 and time.monotonic()-start<=120,'FIXED_BUNDLE_INPUT_CAP');digest.update(data);output.write(data)
 need(total==BUNDLE['bytes'] and digest.hexdigest()==BUNDLE['sha256'],'EXACT_REVIEWED_TRANSPORT_BYTES')
 expected={row['path']:row for row in BUNDLE['entries']};dest=work/'etcd-serving'
 with zipfile.ZipFile(raw) as z:
  infos=z.infolist();need(len(infos)==12 and len({i.filename for i in infos})==12 and {i.filename for i in infos}==set(expected),'EXACT_BUNDLE_FILE_SET')
  need(sum(i.file_size for i in infos)<=134217728,'UNPACKED_BUNDLE_CAP')
  for info in infos:
   row=expected[info.filename];need(not info.is_dir() and not info.flag_bits&1 and info.compress_type==zipfile.ZIP_STORED and stat.S_IFMT(info.external_attr>>16)==stat.S_IFREG and info.file_size==row['bytes'],'REGULAR_EXACT_BUNDLE_ENTRY')
   need(hashlib.sha256(z.read(info)).hexdigest()==row['sha256'],'FULL_BUNDLE_ENTRY_SHA_BEFORE_EXTRACT')
  dest.mkdir()
  for info in infos:
   row=expected[info.filename];target=bounds.canonical(dest/info.filename,exists=False);need(target.is_relative_to(dest),'FIXED_EXTRACTION_CONTAINMENT');target.parent.mkdir(parents=True,exist_ok=True)
   data=z.read(info);need(len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],'EXACT_COPY_BYTES');target.write_bytes(data);os.chmod(target,int(row['mode'],8))
 identity(dest,lock)  # No target spawn; first execution remains prepare's held-image gate.
 source=ROOT/'vendor/notices/ETCD-FIXTURE-SOURCES.json'
 need((dest/'notices/ETCD-FIXTURE-SOURCES.json').read_bytes()==source.read_bytes(),'FULL_ORIGINAL_NOTICE_CLOSURE')
 write(work/'transport-receipt.json',dict(url=BUNDLE['futureUrl'],bytes=total,sha256=digest.hexdigest(),entryPins=BUNDLE['entries'],targetExecuted=False,compilerOrAuditOrDefaultReproduction=False))
 return dest

def package_root():
 roots=list((ART/'extracted with spaces').iterdir());need(len(roots)==1 and roots[0].is_dir(),'ONE_ACTUAL_EXTRACTED_PACKAGE');return roots[0]

PHASE_FIELDS=('projectId','ownerPID','ownerProcessStartIdentity','randomToken','phase','sourceCommit','ownerOS','nativeUnit')

def check_phase_owner(observed,expected):
 need(type(observed) is dict and type(expected) is dict and set(observed)==set(expected)==set(PHASE_FIELDS),'EXACT_PHASE_LEASE_FIELDS')
 need(type(observed['ownerPID']) is int and observed['ownerPID']>0,'EXACT_PHASE_PID_TYPE')
 need(all(type(observed[k]) is type(expected[k]) and observed[k]==expected[k] for k in PHASE_FIELDS),'EXACT_PHASE_LEASE_BINDING')
 job.check_owner(observed,expected)
 need(observed['ownerProcessStartIdentity']==job._start_identity(observed['ownerPID']),'EXACT_LIVE_PHASE_OWNER')

def worker(stage,rid,commit,phase,token,unit):
 holder=json.loads((ART/'ci-lane.json').read_bytes());expected=dict(projectId='06',ownerPID=holder.get('ownerPID'),ownerProcessStartIdentity=holder.get('ownerProcessStartIdentity'),randomToken=token,phase=stage,sourceCommit=commit,ownerOS=os.name,nativeUnit=unit);check_phase_owner(holder,expected);need(os.name!='nt' or unit is None,'NO_WINDOWS_NATIVE_UNIT')
 env=env_for_child();python=str(Path(sys.executable).resolve());count=0
 if os.name!='nt':
  caps=current_caps(stage);need(holder.get('nativeUnit')==unit and re.fullmatch('ownershiplab-ci-[0-9a-f]{16}-'+stage,unit) and caps['group'].endswith('/'+unit+'.service'),'OWN_WORKER_UNIT');need(os.environ.get('INVOCATION_ID'),'OWN_INVOCATION');stageWatch=ResourceWatch(caps)
  write(phase/'unit-owner.json',dict(token=token,unit=unit,stage=stage,sourceCommit=commit,invocationId=os.environ['INVOCATION_ID'],group=caps['group'],pid=os.getpid(),processStart=job._start_identity(os.getpid()),bootId=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),actualCaps=caps))
 def run(argv,seconds=180,extra=None):
  nonlocal count
  count+=1;local=dict(env);local.update(extra or {});return command(list(map(str,argv)),local,phase/('command-'+str(count).zfill(2)),seconds,stage)
 py=lambda name,*args:[python,'-B',str(ROOT/name),*args]
 if stage=='policy':
  run([python,'-m','unittest','discover','-s','.github/ci','-p','test_policy.py','-v'],60);run(py('.github/ci/policy.py','gate'),30);run(py('tools/build_actionlint.py','prepare-ci-sealed','--target','windows-amd64'),180);run(py('.github/ci/policy.py','lint'),90)
 elif stage=='verify':
  dotnet=sdk(env);run([dotnet,'restore','tests/Ownership.Tests/Ownership.Tests.csproj','--locked-mode'],300)
  run([dotnet,'run','--project','tests/Ownership.Tests/Ownership.Tests.csproj','-c','Release','--no-restore','--','-noLogo','-xml','artifacts/unit.xml'],300)
  run(py('tools/test_receipt_oracle.py','--out','artifacts/receipt-oracle-normal'),60,{'PYTHONOPTIMIZE':'0'});run(py('tools/test_receipt_oracle.py','--out','artifacts/receipt-oracle-optimized'),60,{'PYTHONOPTIMIZE':'1'})
  run(py('tools/package.py','--rid',rid,'--commit',commit,'--work','artifacts/build','--out','artifacts/delivery','--dotnet',dotnet),600)  # No --local-candidate.
  run(py('tools/test_notices.py','--out','artifacts/notices-tests'),120);run(py('tools/test_verifier.py','--out','artifacts/verifier-tests'),120);run(py('tools/audit_dependencies.py','--dotnet',dotnet,'--out','artifacts/dependency-advisories.json'),380)
  archives=list((ART/'delivery').iterdir());need(len(archives)==1 and archives[0].is_file(),'ONE_NATIVE_ARCHIVE')
  run(py('tools/extract_package.py','--archive',archives[0],'--out',ART/'extracted with spaces'),120);package=package_root()
  run(py('tools/check_package.py','--package',package,'--commit',commit,'--out','artifacts/package-checks.json'),120)
  text=run([dotnet,'nuget','locals','global-packages','--list'],30).decode('utf-8').strip();need(text.startswith('global-packages: '),'NUGET_LOCATION_FRAME');nuget=text[len('global-packages: '):].strip();need(Path(nuget).resolve()==Path(env['NUGET_PACKAGES']).resolve(),'OWN_NUGET_ARCHIVES')
  run(py('tools/check_sbom_archives.py','--package',package,'--nuget-root',nuget,'--out','artifacts/sbom-archive-checks.json'),180);run(py('tools/test_sbom_archives.py','--out','artifacts/sbom-regressions'),120)
 elif stage=='prepare':
  need(sys.platform=='linux','LINUX_FIXTURE_ONLY');run(py('tools/fetch_services.py','--out','artifacts/upstream'),180);bundle=fetch_bundle()
  run(py('tools/prepare_linux.py','--archives','artifacts/upstream','--etcd-bundle',bundle,'--out','artifacts/services'),180)
 elif stage=='runtime':
  need(sys.platform=='linux','LINUX_RUNTIME_ONLY');package=package_root()
  run([python,'-B',str(package/'tools/integration.py'),'--runtime-profile','native-linux-16','--fixtures',str(ART/'services'),'--cli',str(package/'ownership'),'--out',str(ART/'integration')],1020)
 elif stage=='aggregate':run(py('tools/check_release.py','--directory','artifacts/release','--commit',commit,'--tag','v0.1.0-preview.4'),480)
 if os.name!='nt':
  summary=stageWatch.finish();write(phase/'resource-summary.json',summary);validate_resource_counters(summary)
 write(phase/'worker.json',dict(status='PASS',stage=stage,commands=count,sourceCommit=commit,python=sys.version,sdkPolicy='Windows exact official404 private ephemeral Job staging; Linux existing404 only; global.json404/disable; first SDK target locked restore; no SDK health/global install'))

def bus_environment():
 uid=os.getuid();need(uid!=0,'NONROOT_EXISTING_USER_REQUIRED');base=Path('/run/user')/str(uid);bus=base/'bus'
 need(bus.exists() and stat.S_ISSOCK(bus.lstat().st_mode) and bus.lstat().st_uid==uid,'EXISTING_USER_BUS_MISSING_NO_INSTALL')
 env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','XDG_RUNTIME_DIR':str(base),'DBUS_SESSION_BUS_ADDRESS':'unix:path='+str(bus)}
 probe=subprocess.run(['/usr/bin/systemctl','--user','show','--property=Version','--value'],env=env,capture_output=True,timeout=3)
 need(probe.returncode==0 and 0<len(probe.stdout)<=4096,'EXISTING_MANAGER_NOT_READY_NO_START')
 return env

def group_for(unit):
 uid=os.getuid();return Path('/sys/fs/cgroup')/f'user.slice/user-{uid}.slice/user@{uid}.service/app.slice'/f'{unit}.service'

def terminal(group):
 if not group.exists():return dict(populated=0,observation='ACTUAL_OWN_CGROUP_REMOVED')
 events=dict(x.split() for x in (group/'cgroup.events').read_text().splitlines());return dict(populated=int(events['populated']),observation='ACTUAL_OWN_CGROUP_EVENTS')

def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=list(WALL),required=True);p.add_argument('--rid',choices=['win-x64','linux-x64'],required=True);p.add_argument('--commit',required=True);p.add_argument('--worker',action='store_true');p.add_argument('--token');p.add_argument('--unit');a=p.parse_args();need(a.worker or (a.token is None and a.unit is None),'INTERNAL_WORKER_ARGUMENTS_ONLY')
 need(sys.version_info[:2]==(3,12),'EXISTING_PYTHON312_REQUIRED_NO_INSTALL');need(re.fullmatch('[0-9a-f]{40}',a.commit),'EXACT_COMMIT');need(os.environ.get('GITHUB_ACTIONS')=='true','HOSTED_CI_ONLY')
 need(os.environ.get('GITHUB_RUN_ATTEMPT')=='1','NO_AUTOMATIC_RERUN')
 need((a.rid=='win-x64')==(os.name=='nt') and platform.machine().lower() in ['amd64','x86_64'],'ACTUAL_NATIVE_RID');need(a.stage not in ['prepare','runtime','aggregate'] or sys.platform=='linux','NO_WINDOWS128_OR_FIXTURE_BORROWING')
 need(a.stage!='policy' or os.name=='nt','POLICY_WINDOWS_ONLY')
 # Read-only Git identification, not a downloaded SDK/tool target.
 actual=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip();need(actual==a.commit and os.environ.get('GITHUB_SHA')==a.commit,'EXACT_CHECKOUT_SHA')
 ART.mkdir(exist_ok=True);phase=ART/'ci-caps'/a.stage
 if a.worker:
  need(a.token and re.fullmatch('[0-9a-f]{64}',a.token),'WORKER_TOKEN')
  try:worker(a.stage,a.rid,a.commit,phase,a.token,a.unit)
  except Exception as ex:
   write(phase/'worker-failure.json',dict(status='HOLD',stage=a.stage,errorType=type(ex).__name__,reason=str(ex)[:200],sourceCommit=a.commit,rawConsoleOrCredentialsIncluded=False));raise
  return
 phase.mkdir(parents=True,exist_ok=False);lease=ART/'ci-lane.json';token=secrets.token_hex(32);unit_name=None if os.name=='nt' else 'ownershiplab-ci-'+secrets.token_hex(8)+'-'+a.stage;holder=dict(projectId='06',ownerPID=os.getpid(),ownerProcessStartIdentity=job._start_identity(os.getpid()),randomToken=token,phase=a.stage,sourceCommit=a.commit,ownerOS=os.name,nativeUnit=unit_name);safe=False;code=125;record=dict(stage=a.stage,sourceCommit=a.commit,status='HOLD',released=False)
 try:
  with lease.open('x',encoding='utf-8') as f:json.dump(holder,f);f.flush();os.fsync(f.fileno())
 except FileExistsError:
  write(phase/'phase.json',dict(status='BUSY_NOT_CLAIMED',stage=a.stage,sourceCommit=a.commit));raise RuntimeError('HOLD_BUSY_NO_RESET')
 try:
  argv=[sys.executable,'-I','-B',str(Path(__file__).resolve()),'--worker','--stage',a.stage,'--rid',a.rid,'--commit',a.commit,'--token',token]
  if os.name=='nt':
   try:job.run(argv,cwd=ROOT,env=env_for_child(),timeout=WALL[a.stage],evidence=phase/'job');code=0
   finally:
    file=phase/'job/process.json'
    if file.exists():
     observed=json.loads(file.read_bytes());value=observed.get('actualCap',{}).get('activeProcessesAtTeardown');safe=type(value) is int and value==0;code=observed.get('exitCode',125);record['actualCap']=observed.get('actualCap',{})
  else:
   unit=unit_name;group=group_for(unit);need(not group.exists(),'FRESH_OWN_UNIT_ONLY');safe=True;env=bus_environment();argv+=['--unit',unit];safe=False;service_env=env_for_child();service_flags=service_environment_flags(service_env,a.commit)
   args=['/usr/bin/systemd-run','--user','--wait','--collect','--pipe','--quiet','--slice=app.slice','--expand-environment=no',*service_flags,'--unit='+unit,'--property=MemoryMax=4294967296','--property=MemorySwapMax=0','--property=CPUQuota=200%','--property=TasksMax='+('128' if a.stage=='runtime' else '64'),'--property=RuntimeMaxSec='+str(WALL[a.stage]),'--property=TimeoutStopSec=5','--property=KillMode=control-group','--property=WorkingDirectory='+str(ROOT),*argv]
   child=subprocess.Popen(args,env=env,cwd=ROOT)
   try:code=child.wait(timeout=WALL[a.stage]+15)
   except subprocess.TimeoutExpired:
    owner=json.loads((phase/'unit-owner.json').read_bytes());need(owner['token']==token and owner['unit']==unit and owner['stage']==a.stage and owner['sourceCommit']==a.commit and owner['group']==str(group) and owner['bootId']==Path('/proc/sys/kernel/random/boot_id').read_text().strip() and type(owner['pid']) is int and owner['pid']>0 and owner['processStart']==job._start_identity(owner['pid']),'OWN_INVOCATION_RECORD_ONLY')
    active=subprocess.run(['/usr/bin/systemctl','--user','show',unit,'--property=InvocationID','--value'],env=env,capture_output=True,text=True,timeout=3);need(active.returncode==0 and active.stdout.strip()==owner['invocationId'],'NEVER_STOP_FOREIGN_INVOCATION')
    subprocess.run(['/usr/bin/systemctl','--user','stop',unit],env=env,check=True,timeout=15);code=child.wait(timeout=10)
   state=terminal(group);safe=type(state['populated']) is int and state['populated']==0;record.update(unit=unit,actualNativeTerminal=state)
   owner_path=phase/'unit-owner.json'
   if owner_path.exists():
    owner=json.loads(owner_path.read_bytes());need(owner.get('token')==token and owner.get('unit')==unit and owner.get('stage')==a.stage and owner.get('sourceCommit')==a.commit,'EXACT_COMPLETED_UNIT_RECORD');record['actualCap']=owner.get('actualCaps',{})
  need(type(code) is int and code==0,'NEW_STAGE_FAILURE_STOP_NO_RETRY');need(safe,'ACTUAL_OWNED_TERMINAL_REQUIRED')
  complete=json.loads((phase/'worker.json').read_bytes());need(complete.get('status')=='PASS' and complete.get('sourceCommit')==a.commit and complete.get('stage')==a.stage and type(complete.get('commands')) is int and complete['commands']=={'policy':4,'verify':13,'prepare':2,'runtime':1,'aggregate':1}[a.stage],'COMPLETE_FIXED_STAGE_REQUIRED');record['status']='PASS'
 except Exception as ex:
  record['errorType']=type(ex).__name__;record['error']=str(ex)[:180];raise
 finally:
  record.update(exitCode=code,ownedTerminalVerified=safe);write(phase/'phase.json',record)
  if safe:
   try:check_phase_owner(json.loads(lease.read_bytes()),holder);lease.unlink();record['released']=True
   except Exception as ex:
    record['status']='HOLD';record['releaseErrorType']=type(ex).__name__;write(phase/'phase-final.json',record);os.replace(phase/'phase-final.json',phase/'phase.json');raise
   write(phase/'phase-final.json',record);os.replace(phase/'phase-final.json',phase/'phase.json')
  # Safe cap/terminal evidence in policy logs too; no command output, argv, lease token or credentials.
  public={k:record[k] for k in ('stage','sourceCommit','status','exitCode','ownedTerminalVerified','released','actualCap') if k in record};print(json.dumps(dict(schema='ci06-public-phase-facts/v1',**public),ensure_ascii=True),flush=True)
 need(record['status']=='PASS','STAGE_HOLD')

if __name__=='__main__':main()
