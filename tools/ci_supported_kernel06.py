"""INERT06 supported-CI kernel adapter. Review source only; never run locally.
Root boundary is exactly existing sudo-n/systemd-run of one fixed own worker.
"""
import ctypes,hashlib,json,os,re,select,signal,stat,subprocess,sys,time
from pathlib import Path

def need(ok,why):
 if not ok:raise RuntimeError('HOLD_CI06_KERNEL_'+why)

def write(path,data):
 with Path(path).open('x',encoding='utf-8',newline='\n') as f:
  json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())

def proc_start(pid):
 text=Path('/proc',str(pid),'stat').read_text();return 'proc-start:'+text[text.rfind(')')+2:].split()[19]

def remaining(phase):
 data=json.loads((Path(phase).parents[1]/'ci-host-deadline.json').read_bytes())
 need(data['sourceCommit']==os.environ.get('GITHUB_SHA') and data['runId']==os.environ.get('GITHUB_RUN_ID') and data['jobId']==os.environ.get('GITHUB_JOB'),'DEADLINE_JOB_BINDING')
 left=(data['deadlineMonotonicNs']-time.monotonic_ns())/1000000000
 need(0<left<=data['rowSeconds'],'SINGLE_JOB_DEADLINE');return left

def deadline(root):
 source=Path(os.environ['RUNNER_TEMP'])/'ci06-row-deadline.json'
 data=json.loads(source.read_bytes());start=data['rowStartedMonotonicNs'];end=data['deadlineMonotonicNs']
 expected={'ci_policy':300,'verify':900,'aggregate':600}.get(os.environ.get('GITHUB_JOB'))
 need(expected is not None and data['rowSeconds']==expected and end-start==expected*1000000000 and 0<start<=time.monotonic_ns()<end,'ORIGINAL_PRECHECKOUT_LEDGER')
 need(data['sourceCommit']==os.environ['GITHUB_SHA'] and data['runId']==os.environ['GITHUB_RUN_ID'] and data['jobId']==os.environ['GITHUB_JOB'],'ORIGINAL_LEDGER_OWNER')
 p=Path(root)/'artifacts/ci-host-deadline.json'
 if not p.exists():write(p,data)
 else:need(json.loads(p.read_bytes())==data,'NO_DEADLINE_RESET')
 return p

def group_for(unit):
 need(re.fullmatch('ownershiplab-ci-[0-9a-f]{16}-(verify|prepare|runtime|aggregate)',unit) is not None,'EXACT_OWN_SYSTEM_UNIT')
 return Path('/sys/fs/cgroup/system.slice')/(unit+'.service')

def system_caps(unit,profile):
 need(sys.platform=='linux' and os.getuid()!=0,'NONROOT_WORKER')
 need(profile in ('generic64','native-linux-16'),'FIXED_PROFILE')
 need(profile!='native-linux-16' or unit.endswith('-runtime'),'NO_GENERIC128')
 group=group_for(unit);membership=Path('/proc/self/cgroup').read_text()
 need(membership.strip()=='0::'+str(group).removeprefix('/sys/fs/cgroup'),'ACTUAL_OWN_MEMBERSHIP')
 values={n:(group/n).read_text().strip() for n in ('memory.max','memory.swap.max','pids.max','cpu.max')}
 need(values=={'memory.max':'4294967296','memory.swap.max':'0','pids.max':'128' if profile=='native-linux-16' else '64','cpu.max':'200000 100000'},'ACTUAL_FIXED_CGROUP_V2_LIMITS')
 return dict(membership=membership,group=str(group),kernel=values)

def worker_entry(stage,commit,phase,token,unit):
 from ci_supported_host06 import observe_host_environment
 from bounded_actionlint import _start_identity
 phase=Path(phase);context=json.loads((phase/'supported-host-parent.json').read_bytes())
 own=observe_host_environment('linux-x64')
 need(own['uid']==context['uid'] and own['gid']==context['gid'] and own['bootId']==context['bootId'],'ACTUAL_RUNNER_UID_GID_BOOT')
 caps=system_caps(unit,'native-linux-16' if stage=='runtime' else 'generic64')
 inv=os.environ.get('INVOCATION_ID');need(re.fullmatch('[0-9a-f]{32}',inv or '') is not None,'ACTUAL_SYSTEM_INVOCATION')
 write(phase/'supported-held-worker.json',dict(projectId='06',stage=stage,sourceCommit=commit,token=token,unit=unit,pid=os.getpid(),processStart=_start_identity(os.getpid()),uid=os.getuid(),gid=os.getgid(),bootId=own['bootId'],invocationId=inv,group=caps['group'],actualCaps=caps))
 os.kill(os.getpid(),signal.SIGSTOP)
 release=json.loads((phase/'supported-held-membership.json').read_bytes())
 need(release['pid']==os.getpid() and release['token']==token and release['unit']==unit and release['invocationId']==inv and release['membershipVerifiedBeforeResume'] is True,'HELD_CHILD_RELEASE_BINDING')
 system_caps(unit,'native-linux-16' if stage=='runtime' else 'generic64')
 remaining(phase)
 return own,caps

def show_unit(unit):
 argv=['/usr/bin/systemctl','show',unit,'--property=LoadState','--property=ActiveState','--property=SubState','--property=MainPID','--property=ControlPID','--property=InvocationID','--property=Result','--property=ExecMainCode','--property=ExecMainStatus','--property=ControlGroup']
 r=subprocess.run(argv,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'},capture_output=True,timeout=3)
 need(len(r.stdout)<=16384 and len(r.stderr)<=4096,'SYSTEM_SHOW_OUTPUT_BOUND')
 values=dict(line.split('=',1) for line in r.stdout.decode().splitlines() if '=' in line)
 return r.returncode,values

def run_linux(argv,stage,commit,phase,token,unit,service_flags):
 from ci_supported_host06 import observe_host_environment,fixed_linux_system_starter
 from bounded_actionlint import _start_identity
 phase=Path(phase);root=phase.parents[2];deadline(root)
 own=observe_host_environment('linux-x64');own.update(checkout=str(root),python=str(Path(sys.executable).resolve()),stage=stage,sourceCommit=commit,token=token,kernelProfile='native-linux-16' if stage=='runtime' else 'generic64')
 group=group_for(unit);need(not group.exists(),'NO_UNIT_REUSE')
 write(phase/'supported-host-parent.json',own)
 left=int(remaining(phase));need(left>15,'TERMINAL_RESERVE')
 fixed=fixed_linux_system_starter(own,argv,unit,left-10)
 # Each validated nonsecret env value remains one literal argv; no shell.
 args=fixed[:-len(argv)]+list(service_flags)+argv
 record=dict(projectId='06',unit=unit,token=token,sourceCommit=commit,rootStarter='/usr/bin/sudo -n /usr/bin/systemd-run',workerUser=own['uid'],workerGroup=own['gid'],rootSdkOrProduct=False,terminal=False)
 child=None;pidfd=None;safe=False;code=125
 try:
  child=subprocess.Popen(args,cwd=root,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
  end=time.monotonic()+min(10,remaining(phase)-10);owner_path=phase/'supported-held-worker.json';held=None
  while time.monotonic()<end:
   if owner_path.exists():
    held=json.loads(owner_path.read_bytes());pid=held.get('pid')
    need(type(pid) is int and pid>0 and held['token']==token and held['unit']==unit and held['sourceCommit']==commit,'OWN_STOPPED_WORKER_IDENTITY')
    if Path('/proc/'+str(pid)+'/status').exists() and 'State:\tT' in Path('/proc/'+str(pid)+'/status').read_text():break
   if child.poll() is not None:raise RuntimeError('SYSTEM_STARTER_EXIT_BEFORE_HELD_WORKER:'+str(child.returncode))
   time.sleep(.05)
  else:raise RuntimeError('OWN_STOPPED_WORKER_DEADLINE')
  pidfd=os.pidfd_open(pid,0)
  need(held['processStart']==_start_identity(pid) and held['uid']==own['uid'] and held['gid']==own['gid'] and held['bootId']==own['bootId'],'LIVE_WORKER_START_UID_BOOT')
  status=Path('/proc/'+str(pid)+'/status').read_text();uidline=next(x for x in status.splitlines() if x.startswith('Uid:'));gidline=next(x for x in status.splitlines() if x.startswith('Gid:'))
  need(all(int(x)==own['uid'] for x in uidline.split()[1:]) and all(int(x)==own['gid'] for x in gidline.split()[1:]),'ACTUAL_NONROOT_ALL_UID_GID_IDS')
  need(Path('/proc/'+str(pid)+'/cgroup').read_text().strip()=='0::'+str(group).removeprefix('/sys/fs/cgroup'),'STOPPED_CHILD_ACTUAL_MEMBERSHIP')
  rc,observed=show_unit(unit)
  need(rc==0 and observed.get('MainPID')==str(pid) and observed.get('InvocationID')==held['invocationId'] and observed.get('ControlGroup')==str(group).removeprefix('/sys/fs/cgroup'),'ACTUAL_MANAGER_PID_INVOCATION_GROUP')
  kernel={n:(group/n).read_text().strip() for n in ('memory.max','memory.swap.max','pids.max','cpu.max')}
  need(kernel==held['actualCaps']['kernel'],'ACTUAL_CHILD_PARENT_CAP_READBACK')
  write(phase/'supported-held-membership.json',dict(pid=pid,token=token,unit=unit,invocationId=held['invocationId'],membershipVerifiedBeforeResume=True,kernel=kernel,processStart=held['processStart']))
  if stage=='verify':prepare_shared_context(root,phase,held,kernel,pid,token)
  signal.pidfd_send_signal(pidfd,signal.SIGCONT)
  try:code=child.wait(timeout=max(.1,remaining(phase)-5))
  except subprocess.TimeoutExpired:
   # Unit RuntimeMaxSec/TimeoutStopSec kill only this own control-group.
   record['cause']='OUTER_REMAINING_DEADLINE';raise
 finally:
  rc,observed=show_unit(unit)
  if group.exists():
   events=dict(x.split() for x in (group/'cgroup.events').read_text().splitlines());populated=int(events['populated']);group_observation='ACTUAL_CGROUP_EVENTS'
  else:populated=0;group_observation='ACTUAL_CGROUP_ABSENT'
  pid_exited=False
  if pidfd is not None:
   poll=select.poll();poll.register(pidfd,select.POLLIN);pid_exited=bool(poll.poll(0));os.close(pidfd)
  removed=observed.get('LoadState')=='not-found' and not group.exists() and pid_exited
  main=0 if removed else int(observed.get('MainPID','-1'));control=0 if removed else int(observed.get('ControlPID','-1'))
  safe=type(populated) is int and populated==0 and main==0 and control==0 and pid_exited and child is not None and child.poll() is not None
  record.update(exitCode=code,systemShow=observed,systemShowExitCode=rc,populated=populated,MainPID=main,ControlPID=control,heldPidfdExited=pid_exited,groupObservation=group_observation,terminal=safe,typedTerminalBasis='Actual manager PID fields, or actual manager not-found plus absent cgroup and held pidfd exit. No collect/reset/foreign stop. Preserve cause before upload.')
  write(phase/'supported-system-terminal.json',record)
 need(safe,'ACTUAL_TERMINAL_REQUIRED')
 return code,dict(populated=populated,MainPID=main,ControlPID=control,terminal=safe),held['actualCaps']

def windows_cpu_v2():
 """Own current CPUs via fixed CPUID stub; W^X allocation, thread-only affinity.
 No SDK/compiler, installed executable, global policy or host cap change.
 """
 from ctypes import wintypes as W
 need(os.name=='nt','WINDOWS_NATIVE_ONLY')
 k=ctypes.WinDLL('kernel32',use_last_error=True)
 class PN(ctypes.Structure):_fields_=[('Group',W.WORD),('Number',ctypes.c_ubyte),('Reserved',ctypes.c_ubyte)]
 class GA(ctypes.Structure):_fields_=[('Mask',ctypes.c_size_t),('Group',W.WORD),('Reserved',W.WORD*3)]
 k.VirtualAlloc.argtypes=[ctypes.c_void_p,ctypes.c_size_t,W.DWORD,W.DWORD];k.VirtualAlloc.restype=ctypes.c_void_p
 k.VirtualProtect.argtypes=[ctypes.c_void_p,ctypes.c_size_t,W.DWORD,ctypes.POINTER(W.DWORD)]
 k.VirtualFree.argtypes=[ctypes.c_void_p,ctypes.c_size_t,W.DWORD]
 k.GetCurrentThread.restype=W.HANDLE;k.GetCurrentProcess.restype=W.HANDLE
 k.GetCurrentProcessorNumberEx.argtypes=[ctypes.POINTER(PN)]
 k.GetActiveProcessorGroupCount.restype=W.WORD;k.GetActiveProcessorCount.argtypes=[W.WORD];k.GetActiveProcessorCount.restype=W.DWORD
 k.SetThreadGroupAffinity.argtypes=[W.HANDLE,ctypes.POINTER(GA),ctypes.POINTER(GA)]
 k.FlushInstructionCache.argtypes=[W.HANDLE,ctypes.c_void_p,ctypes.c_size_t]
 code=bytes.fromhex('534989c989d04489c10fa241890141895904418949084189510c5bc3');ptr=k.VirtualAlloc(None,len(code),0x3000,0x04);need(ptr,'OWN_CPUID_RW_ALLOC')
 original=GA();restore=False;rows=[]
 try:
  ctypes.memmove(ptr,code,len(code));old=W.DWORD();need(k.VirtualProtect(ptr,len(code),0x20,ctypes.byref(old)),'OWN_CPUID_RX_PROTECT');need(k.FlushInstructionCache(k.GetCurrentProcess(),ptr,len(code)),'OWN_CPUID_ICACHE')
  fn=ctypes.CFUNCTYPE(None,ctypes.POINTER(ctypes.c_uint32),ctypes.c_uint32,ctypes.c_uint32)(ptr)
  for group in range(k.GetActiveProcessorGroupCount()):
   for cpu in range(k.GetActiveProcessorCount(group)):
    wanted=GA();wanted.Group=group;wanted.Mask=1<<cpu;previous=GA();need(k.SetThreadGroupAffinity(k.GetCurrentThread(),ctypes.byref(wanted),ctypes.byref(previous)),'OWN_THREAD_CPU_AFFINITY')
    if not restore:original=previous;restore=True
    current=PN();k.GetCurrentProcessorNumberEx(ctypes.byref(current));need((current.Group,current.Number)==(group,cpu),'ACTUAL_ASSIGNED_LOGICAL_CPU')
    a=(ctypes.c_uint32*4)();b=(ctypes.c_uint32*4)();fn(a,1,0);fn(b,0x80000001,0)
    mask=sum(1<<i for i in (0,9,13,19,20,23));need(a[2]&mask==mask and b[2]&1,'EVERY_LOGICAL_CPU_V2')
    rows.append(dict(group=group,cpu=cpu,leaf1ecx=int(a[2]),extended1ecx=int(b[2])))
  need(bool(rows),'ACTUAL_CPU_SET')
 finally:
  try:
   if restore:
    unused=GA();need(k.SetThreadGroupAffinity(k.GetCurrentThread(),ctypes.byref(original),ctypes.byref(unused)),'RESTORE_OWN_THREAD_AFFINITY')
  finally:need(k.VirtualFree(ptr,0,0x8000),'FREE_OWN_CPUID_MEMORY')
 return dict(observed=True,logicalCpuCount=len(rows),observations=rows,temporaryThreadAffinityRestored=True,ownMemoryFreed=True)


def prepare_shared_context(root,phase,held,kernel,pid,token):
 import platform,tempfile
 root=Path(root);phase=Path(phase);repository='pouriajamali/fenced-shard-ownership-lab'
 ledger=json.loads((root/'artifacts/ci-host-deadline.json').read_bytes())
 evidence_dir=Path(tempfile.mkdtemp(prefix='ci06-held-'+token[:12]+'-',dir=os.environ['RUNNER_TEMP']));os.chmod(evidence_dir,0o700)
 info=evidence_dir.stat();need(info.st_uid==os.getuid() and info.st_gid==os.getgid() and stat.S_IMODE(info.st_mode)==0o700,'OWN_PRIVATE_EVIDENCE_SCOPE')
 controller=root/'tools/ci_pipeline.py';profile=root/'profiles/ci06-normal-input-profile.json';contract=root/'tools/ci06-normal-contract.json';pins=root/'tools/ci06-source-pins.json'
 def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
 def git(*args):return subprocess.check_output(['/usr/bin/git','-C',str(root),*args],text=True,timeout=5).strip()
 commit=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}')
 need(commit==os.environ['GITHUB_SHA'] and not git('status','--porcelain=v1','--untracked-files=all'),'EXACT_CLEAN_SOURCE_BEFORE_CONTEXT')
 profile_sha=digest(profile);controller_sha=digest(controller);supervisor_start=proc_start(os.getpid());worker_start=proc_start(pid)
 caps={'schema':'sdk11-own-current-cap-evidence/v1','projectId':'06','repository':repository,'sourceCommit':commit,'sourceTree':tree,'profileSha256':profile_sha,'controllerSha256':controller_sha,'worker':{'pid':pid,'processStartIdentity':worker_start,'uid':held['uid'],'gid':held['gid'],'cgroup':held['group'].removeprefix('/sys/fs/cgroup'),'kernelLimits':kernel},'beforeExec':{'pid':pid,'processStartIdentity':worker_start,'cgroup':held['group'].removeprefix('/sys/fs/cgroup'),'kernelLimits':kernel,'state':'T','membershipBeforeRelease':True,'retainedStartHandle':True},'supervisor':{'pid':os.getpid(),'processStartIdentity':supervisor_start,'deadlineMonotonicNs':ledger['deadlineMonotonicNs']},'rowStartedMonotonicNs':ledger['rowStartedMonotonicNs'],'deadlineMonotonicNs':ledger['deadlineMonotonicNs'],'bootstrap':{'pythonVersion':platform.python_version(),'pythonExeSha256':digest(Path(sys.executable).resolve()),'gitSha256':digest('/usr/bin/git'),'systemctlSha256':digest('/usr/bin/systemctl')}}
 caps_path=evidence_dir/'caps.json';write(caps_path,caps)
 source_pins=json.loads(pins.read_bytes())
 pins_sha=hashlib.sha256(json.dumps(source_pins['sourcePins'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
 # Exact reviewed route constructs the frozen canonical admission from actual
 # current evidence. It grants no route before the separate source/runtime gate.
 admission={'schema':'sdk11-consumer-host-admission/v1','state':'ADMITTED_EXACT_SUPPORTED_HOST_CLASS','projectId':'06','producerFactSha256':'757abf2d3dde65d10cd895cfc97eaeccb7fc11e8685b94ad046e6a8ec8829007','admittedFor':{'hostClass':'GitHubHostedUbuntu24.04x64','rid':'linux-x64','sdk':'11.0.100','runtime':'11.0.0','memberManifestSha256':'d411111d23492b4d101dd62851d1d1fedf3a4badc057d999aedc155ae4cc103a','contractSha256':digest(contract),'sourcePinTableSha256':pins_sha,'controllerSha256':controller_sha,'profileSha256':profile_sha},'currentExecution':{'runId':os.environ['GITHUB_RUN_ID'],'job':os.environ['GITHUB_JOB'],'attempt':os.environ['GITHUB_RUN_ATTEMPT'],'instanceId':os.environ['RUNNER_NAME'],'ownCapsEvidenceSha256':digest(caps_path)},'identityRule':'QUALIFIED_ON_IS_HISTORICAL_PRODUCER_INSTANCE_CURRENT_CONSUMER_JOB_MAY_DIFFER'}
 admission_path=evidence_dir/'admission.json';write(admission_path,admission)
 context={'admission':str(admission_path),'capsEvidence':str(caps_path),'checkout':str(root),'contract':str(contract),'controller':str(controller),'deadlineMonotonicNs':ledger['deadlineMonotonicNs'],'expectedSourceCommit':commit,'expectedSourceTree':tree,'profile':str(profile),'projectId':'06','repository':repository,'rowStartedMonotonicNs':ledger['rowStartedMonotonicNs'],'sourcePins':str(pins),'supervisorPID':os.getpid(),'supervisorStartIdentity':supervisor_start}
 write(phase/'sdk11-shared-context.json',{'context':context})
 write(phase/'sdk11-own-cap-evidence.json',caps);write(phase/'sdk11-consumer-admission.json',admission)
