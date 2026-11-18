"""Fixed-cap Windows library; no CLI, target, acquisition or SDK on import."""
from __future__ import annotations
import contextlib,ctypes,hashlib,json,os,subprocess,time
from pathlib import Path
MEMORY=4294967296;TASKS=64;CPUS=2;LOG_LIMIT=1048576
class CapError(RuntimeError):pass
def need(value,reason):
 if not value:raise CapError(reason)
def _write_json(path,value):
 with Path(path).open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
def _kernel():
    from ctypes import wintypes as W
    K=ctypes.WinDLL('kernel32',use_last_error=True)
    for n in ('CreateJobObjectW','CreateFileW'):
        getattr(K,n).restype=W.HANDLE
    K.CreateJobObjectW.argtypes=[ctypes.c_void_p,W.LPCWSTR]
    K.CreateFileW.argtypes=[W.LPCWSTR,W.DWORD,W.DWORD,ctypes.c_void_p,W.DWORD,W.DWORD,W.HANDLE]
    K.CloseHandle.argtypes=[W.HANDLE]
    K.SetInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD]
    K.QueryInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD,ctypes.c_void_p]
    K.AssignProcessToJobObject.argtypes=[W.HANDLE,W.HANDLE]
    K.IsProcessInJob.argtypes=[W.HANDLE,W.HANDLE,ctypes.POINTER(W.BOOL)]
    K.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD]
    K.GetExitCodeProcess.argtypes=[W.HANDLE,ctypes.POINTER(W.DWORD)]
    K.TerminateJobObject.argtypes=[W.HANDLE,W.UINT]
    K.TerminateProcess.argtypes=[W.HANDLE,W.UINT]
    K.ResumeThread.argtypes=[W.HANDLE]
    K.ResumeThread.restype=W.DWORD
    return K,W

def _checked(v):
    if not v: raise ctypes.WinError(ctypes.get_last_error())
    return v

@contextlib.contextmanager
def held_windows_image(path):
    """Deny image write/delete; hold ancestors against rename while the native child starts."""
    import msvcrt
    K,W=_kernel(); path=Path(path).absolute(); handles=[]; fd=None
    invalid=ctypes.c_void_p(-1).value
    try:
        for parent in reversed(path.parents):
            h=K.CreateFileW(str(parent),0x80000000,3,None,3,0x02000000|0x00200000,None)
            need(h not in (None,invalid),'IMAGE_PARENT_HOLD'); handles.append(h)
        h=K.CreateFileW(str(path),0x80000000,1,None,3,0x00200000,None)
        need(h not in (None,invalid),'IMAGE_HOLD')
        fd=msvcrt.open_osfhandle(h,os.O_RDONLY|os.O_BINARY)
        with os.fdopen(fd,'rb',closefd=False) as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
        yield {'sha256':digest,'identity':{'canonicalPath':str(path),'heldReadOnlyDenyDelete':True,'ancestorHandles':len(handles)}}
    finally:
        if fd is not None: os.close(fd)
        for h in reversed(handles): K.CloseHandle(h)

def _start_identity(pid):
    if os.name!='nt':
        text=Path('/proc',str(pid),'stat').read_text();return 'proc-start:'+text[text.rfind(')')+2:].split()[19]
    from ctypes import wintypes as W
    K,W=_kernel();K.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];K.OpenProcess.restype=W.HANDLE
    K.GetProcessTimes.argtypes=[W.HANDLE,*[ctypes.POINTER(W.FILETIME)]*4]
    handle=K.OpenProcess(0x1000,False,pid);need(handle,'PORTABLE_OWNER_PROCESS')
    try:
        times=[W.FILETIME() for _ in range(4)];need(K.GetProcessTimes(handle,*[ctypes.byref(x) for x in times]),'PORTABLE_OWNER_START')
        return 'FILETIME:'+str((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)
    finally:K.CloseHandle(handle)


def tick():
 K,W=_kernel();K.GetTickCount64.restype=ctypes.c_ulonglong;return int(K.GetTickCount64())
def current_witness(job_name):
 K,W=_kernel();K.OpenJobObjectW.argtypes=[W.DWORD,W.BOOL,W.LPCWSTR];K.OpenJobObjectW.restype=W.HANDLE;K.GetCurrentProcess.restype=W.HANDLE
 handle=K.OpenJobObjectW(4,False,job_name);need(handle,'AGGREGATE_JOB_OPEN')
 try:
  member=W.BOOL();_checked(K.IsProcessInJob(K.GetCurrentProcess(),handle,ctypes.byref(member)));need(member.value,'ACTUAL_AGGREGATE_MEMBERSHIP')
  U=ctypes.c_size_t
  class Basic(ctypes.Structure):_fields_=[('ProcessTime',ctypes.c_longlong),('JobTime',ctypes.c_longlong),('Flags',W.DWORD),('MinWS',U),('MaxWS',U),('ActiveProcesses',W.DWORD),('Affinity',U),('Priority',W.DWORD),('Scheduling',W.DWORD)]
  class IO(ctypes.Structure):_fields_=[(n,ctypes.c_ulonglong) for n in ('ReadOps','WriteOps','OtherOps','ReadBytes','WriteBytes','OtherBytes')]
  class Extended(ctypes.Structure):_fields_=[('Basic',Basic),('IO',IO),('ProcessMemory',U),('JobMemory',U),('PeakProcessMemory',U),('PeakJobMemory',U)]
  class Cpu(ctypes.Structure):_fields_=[('Flags',W.DWORD),('Rate',W.DWORD)]
  actual=Extended();cpu=Cpu();_checked(K.QueryInformationJobObject(handle,9,ctypes.byref(actual),ctypes.sizeof(actual),None));_checked(K.QueryInformationJobObject(handle,15,ctypes.byref(cpu),ctypes.sizeof(cpu),None));K.GetActiveProcessorCount.argtypes=[W.WORD];K.GetActiveProcessorCount.restype=W.DWORD;logical=K.GetActiveProcessorCount(0xffff)
  need(actual.JobMemory==MEMORY and actual.Basic.ActiveProcesses==TASKS and cpu.Flags==5 and 0<cpu.Rate*logical/10000<=2,'ACTUAL_AGGREGATE_CAP_READBACK')
  return {'kind':'actual-Windows-Job','jobName':job_name,'currentProcessMember':True,'memoryMax':int(actual.JobMemory),'tasksMax':int(actual.Basic.ActiveProcesses),'effectiveCpuCores':cpu.Rate*logical/10000,'peakMemoryBytes':int(actual.PeakJobMemory),'cpuRate':int(cpu.Rate),'logicalHostCpu':int(logical)}
 finally:K.CloseHandle(handle)
def fixed_local_creation_flags(mode,job_name,inherited_job_name,ready_spec):
    if mode is None:return 0x4|0x400|0x08000000
    need(mode=='DETACHED_LOCAL_CONSOLE_FREE_V1','FIXED_LOCAL_CONSOLE_MODE_ONLY')
    need(os.name=='nt' and not any(os.environ.get(k) for k in ('GITHUB_ACTIONS','GITHUB_RUN_ID','RUNNER_ENVIRONMENT')),'DETACHED_MODE_LOCAL_ONLY')
    need(type(job_name) is str and job_name.startswith('Local\\') and inherited_job_name is None and isinstance(ready_spec,dict) and 'path' in ready_spec and 'value' in ready_spec,'DETACHED_DEDICATED_HELD_LOCAL_MAIN_ONLY')
    return 0x4|0x400|0x8

def run_job(argv,cwd,env,deadline_tick,evidence,job_name=None,inherited_job_name=None,ready_spec=None,stage_directory=None,local_console_mode=None):
    creation_flags=fixed_local_creation_flags(local_console_mode,job_name,inherited_job_name,ready_spec)
    evidence=Path(evidence);evidence.mkdir(parents=True,exist_ok=False)
    import msvcrt
    K,W=_kernel(); U=ctypes.c_size_t
    class Basic(ctypes.Structure):
        _fields_=[('ProcessTime',ctypes.c_longlong),('JobTime',ctypes.c_longlong),('Flags',W.DWORD),('MinWS',U),('MaxWS',U),('ActiveProcesses',W.DWORD),('Affinity',U),('Priority',W.DWORD),('Scheduling',W.DWORD)]
    class IO(ctypes.Structure): _fields_=[(n,ctypes.c_ulonglong) for n in ('ReadOps','WriteOps','OtherOps','ReadBytes','WriteBytes','OtherBytes')]
    class Extended(ctypes.Structure):
        _fields_=[('Basic',Basic),('IO',IO),('ProcessMemory',U),('JobMemory',U),('PeakProcessMemory',U),('PeakJobMemory',U)]
    class Cpu(ctypes.Structure): _fields_=[('Flags',W.DWORD),('Rate',W.DWORD)]
    class Accounting(ctypes.Structure):
        _fields_=[('User',ctypes.c_longlong),('Kernel',ctypes.c_longlong),('PeriodUser',ctypes.c_longlong),('PeriodKernel',ctypes.c_longlong),('Faults',W.DWORD),('Total',W.DWORD),('Active',W.DWORD),('Terminated',W.DWORD)]
    class Startup(ctypes.Structure):
        _fields_=[('cb',W.DWORD),('reserved',W.LPWSTR),('desktop',W.LPWSTR),('title',W.LPWSTR),('x',W.DWORD),('y',W.DWORD),('xs',W.DWORD),('ys',W.DWORD),('xc',W.DWORD),('yc',W.DWORD),('fill',W.DWORD),('flags',W.DWORD),('show',W.WORD),('reserved2',W.WORD),('reservedPtr',ctypes.c_void_p),('stdin',W.HANDLE),('stdout',W.HANDLE),('stderr',W.HANDLE)]
    class Process(ctypes.Structure): _fields_=[('process',W.HANDLE),('thread',W.HANDLE),('pid',W.DWORD),('tid',W.DWORD)]
    class Security(ctypes.Structure): _fields_=[('length',W.DWORD),('descriptor',ctypes.c_void_p),('inherit',W.BOOL)]
    K.CreateProcessW.argtypes=[W.LPCWSTR,W.LPWSTR,ctypes.c_void_p,ctypes.c_void_p,W.BOOL,W.DWORD,ctypes.c_void_p,W.LPCWSTR,ctypes.POINTER(Startup),ctypes.POINTER(Process)]
    K.GetActiveProcessorCount.argtypes=[W.WORD]; K.GetActiveProcessorCount.restype=W.DWORD
    ctypes.set_last_error(0);job=K.CreateJobObjectW(None,job_name);need(not job_name or ctypes.get_last_error()!=183,'JOB_ALREADY_EXISTS'); need(bool(job),'JOB_CREATE'); process=Process(); nul=None; start=time.monotonic(); timed=False
    try:
        limits=Extended(); limits.Basic.Flags=0x2000|0x200|0x8; limits.Basic.ActiveProcesses=TASKS; limits.JobMemory=MEMORY
        _checked(K.SetInformationJobObject(job,9,ctypes.byref(limits),ctypes.sizeof(limits)))
        logical=K.GetActiveProcessorCount(0xffff); need(logical>0,'CPU_COUNT'); rate=max(1,min(10000,int(10000*CPUS/logical))); cpu=Cpu(5,rate)
        _checked(K.SetInformationJobObject(job,15,ctypes.byref(cpu),ctypes.sizeof(cpu)))
        actual=Extended(); actualcpu=Cpu()
        _checked(K.QueryInformationJobObject(job,9,ctypes.byref(actual),ctypes.sizeof(actual),None)); _checked(K.QueryInformationJobObject(job,15,ctypes.byref(actualcpu),ctypes.sizeof(actualcpu),None))
        need(actual.JobMemory==MEMORY and actual.Basic.ActiveProcesses==TASKS and actualcpu.Flags==5 and actualcpu.Rate==rate,'JOB_LIMIT_READBACK')
        with open(evidence/'stdout.log','xb') as out,open(evidence/'stderr.log','xb') as err:
            oh,eh=msvcrt.get_osfhandle(out.fileno()),msvcrt.get_osfhandle(err.fileno()); os.set_handle_inheritable(oh,True); os.set_handle_inheritable(eh,True)
            sa=Security(ctypes.sizeof(Security),None,True); nul=K.CreateFileW('NUL',0x80000000,3,ctypes.byref(sa),3,0,None)
            need(nul not in (None,ctypes.c_void_p(-1).value),'NUL_STDIN')
            si=Startup(); si.cb=ctypes.sizeof(si); si.flags=0x100; si.stdin=nul; si.stdout=oh; si.stderr=eh
            line=ctypes.create_unicode_buffer(subprocess.list2cmdline(list(map(str,argv)))); block=ctypes.create_unicode_buffer('\0'.join(k+'='+str(v) for k,v in sorted(env.items(),key=lambda x:x[0].upper()))+'\0\0')
            _checked(K.CreateProcessW(None,line,None,None,True,creation_flags,block,str(cwd),ctypes.byref(si),ctypes.byref(process)))
            os.set_handle_inheritable(oh,False); os.set_handle_inheritable(eh,False)
            _checked(K.AssignProcessToJobObject(job,process.process)); member=W.BOOL(); _checked(K.IsProcessInJob(process.process,job,ctypes.byref(member))); need(bool(member.value),'ACTUAL_CHILD_JOB_MEMBERSHIP')
            K.GetProcessTimes.argtypes=[W.HANDLE,*[ctypes.POINTER(W.FILETIME)]*4]
            times=[W.FILETIME() for _ in range(4)];_checked(K.GetProcessTimes(process.process,*[ctypes.byref(x) for x in times]));child_start='FILETIME:'+str((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)
            need(rate*logical/10000<=2,'JOB_EFFECTIVE_CPU')
            if inherited_job_name:
                K.OpenJobObjectW.argtypes=[W.DWORD,W.BOOL,W.LPCWSTR];K.OpenJobObjectW.restype=W.HANDLE;outer=K.OpenJobObjectW(4,False,inherited_job_name);need(outer,'AGGREGATE_JOB_OPEN')
                try:
                    inherited=W.BOOL();_checked(K.IsProcessInJob(process.process,outer,ctypes.byref(inherited)));need(inherited.value,'ACTUAL_INHERITED_AGGREGATE_BEFORE_RESUME')
                finally:K.CloseHandle(outer)
            if ready_spec is not None:
                payload=dict(ready_spec['value']);payload.update({'workerPID':int(process.pid),'workerStart':child_start,'jobName':job_name,'beforeResume':{'kind':'actual-Windows-Job','memoryMax':MEMORY,'activeProcessMax':TASKS,'effectiveCpuCores':rate*logical/10000,'cpuRate':rate,'logicalHostCpu':logical,'membership':True,'retainedCreationHandles':True}});_write_json(ready_spec['path'],payload)
            _checked(K.ResumeThread(process.thread)!=0xffffffff)
            while K.WaitForSingleObject(process.process,100)==0x102:
                effective_deadline=deadline_tick
                if stage_directory is not None:
                    for index in range(4):
                        sp=Path(stage_directory)/('stage-'+str(index)+'.json')
                        if sp.with_name(sp.name+'.ready').exists():
                            need(sp.stat().st_size<=4096,'STAGE_CLOCK_SIZE');stage=json.loads(sp.read_bytes());need(stage['index']==index and stage['deadlineTick']<=deadline_tick,'STAGE_CLOCK_INVALID');effective_deadline=stage['deadlineTick']
                if tick()>=effective_deadline or out.tell()+err.tell()>LOG_LIMIT:
                    _checked(K.TerminateJobObject(job,124)); timed=True; break
            need(K.WaitForSingleObject(process.process,10000)==0,'OWNED_CHILD_REAP')
        code=W.DWORD(); _checked(K.GetExitCodeProcess(process.process,ctypes.byref(code)))
        accounting=Accounting(); deadline=time.monotonic()+10
        while True:
            _checked(K.QueryInformationJobObject(job,1,ctypes.byref(accounting),ctypes.sizeof(accounting),None))
            if accounting.Active==0: break
            if time.monotonic()>deadline: _checked(K.TerminateJobObject(job,124)); raise CapError('OWNED_DESCENDANTS_REAP')
            time.sleep(.1)
        _checked(K.QueryInformationJobObject(job,9,ctypes.byref(actual),ctypes.sizeof(actual),None))
        proof={'kind':'actual-Windows-Job','memoryMax':int(actual.JobMemory),'activeProcessMax':int(actual.Basic.ActiveProcesses),'cpuRate':int(actualcpu.Rate),'logicalHostCpu':int(logical),'effectiveCpuCores':actualcpu.Rate*logical/10000,'childMembershipBeforeResume':True,'inheritedAggregateBeforeResume':bool(inherited_job_name),'retainedCreationHandles':True,'peakJobMemory':int(actual.PeakJobMemory),'activeProcessesAtTeardown':int(accounting.Active),'totalProcesses':int(accounting.Total)}
        record={'childBeforeExec':{'pid':int(process.pid),'processStartIdentity':child_start,'membershipBeforeResume':True},'schema':'bounded-sdk11-process/v1','argv':list(map(str,argv)),'cwd':str(cwd),'pid':int(process.pid),'exitCode':int(code.value),'timedOut':timed,'seconds':time.monotonic()-start,'actualCap':proof}
        _write_json(evidence/'process.json',record); need(not timed,'CHILD_WALL_OR_LOG_CAP'); need(code.value==0,'CHILD_NONZERO:'+str(code.value)); return record
    finally:
        if process.process and K.WaitForSingleObject(process.process,0)==0x102:
            K.TerminateProcess(process.process,124); K.WaitForSingleObject(process.process,5000)
        if process.thread: K.CloseHandle(process.thread)
        if process.process: K.CloseHandle(process.process)
        if nul and nul!=ctypes.c_void_p(-1).value: K.CloseHandle(nul)
        K.CloseHandle(job)

