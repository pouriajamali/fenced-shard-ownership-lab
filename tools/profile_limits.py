"""Actual coallocated Windows/Linux profile budgets, before service or CLI children."""
import ctypes,os,re
from pathlib import Path
from bounded_fixture import require
WINDOWS_MEMORY=1073741824
LINUX_MEMORY=3221225472

def guest(caps,unit):
 require(isinstance(unit,str) and re.fullmatch(r'ownership(?:06|lab)-[a-z0-9-]{8,100}',unit),'OWN_FRESH_SERVICE_UNIT')
 require(caps['kernel']=={'memory.max':str(LINUX_MEMORY),'memory.swap.max':'0','pids.max':'48','cpu.max':'100000 100000'} and caps['group'].endswith('/'+unit+'.service'),'COALLOCATED_GUEST_ACTUAL_BUDGET')
 return caps

def windows():
 require(os.name=='nt','WINDOWS_CLIENT_REQUIRED')
 from ctypes import wintypes as W
 class BASIC(ctypes.Structure):_fields_=[('processTime',ctypes.c_longlong),('jobTime',ctypes.c_longlong),('flags',W.DWORD),('minWorking',ctypes.c_size_t),('maxWorking',ctypes.c_size_t),('activeLimit',W.DWORD),('affinity',ctypes.c_size_t),('priority',W.DWORD),('scheduling',W.DWORD)]
 class IO(ctypes.Structure):_fields_=[(n,ctypes.c_ulonglong) for n in ('readOps','writeOps','otherOps','readBytes','writeBytes','otherBytes')]
 class EXT(ctypes.Structure):_fields_=[('basic',BASIC),('io',IO),('processMemory',ctypes.c_size_t),('jobMemory',ctypes.c_size_t),('peakProcess',ctypes.c_size_t),('peakJob',ctypes.c_size_t)]
 class CPU(ctypes.Structure):_fields_=[('flags',W.DWORD),('rate',W.DWORD)]
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=W.HANDLE;k.IsProcessInJob.argtypes=[W.HANDLE,W.HANDLE,ctypes.POINTER(W.BOOL)];k.QueryInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD,ctypes.c_void_p]
 member=W.BOOL();require(k.IsProcessInJob(k.GetCurrentProcess(),None,ctypes.byref(member)) and member.value,'ACTUAL_WINDOWS_JOB_REQUIRED');limits=EXT();cpu=CPU();require(k.QueryInformationJobObject(None,9,ctypes.byref(limits),ctypes.sizeof(limits),None) and k.QueryInformationJobObject(None,15,ctypes.byref(cpu),ctypes.sizeof(cpu),None),'ACTUAL_WINDOWS_JOB_READBACK')
 logical=os.cpu_count() or 1;require(limits.basic.flags&0x200 and 0<limits.jobMemory<=WINDOWS_MEMORY and limits.basic.flags&8 and 0<limits.basic.activeLimit<=16 and cpu.flags==5 and 0<cpu.rate*logical<=10000,'COALLOCATED_WINDOWS_ACTUAL_BUDGET')
 return dict(pid=os.getpid(),memoryMax=limits.jobMemory,activeProcessMax=limits.basic.activeLimit,cpuRate=cpu.rate,logicalProcessors=logical,effectiveCpuCores=cpu.rate*logical/10000,memberBeforeServiceOrClientChildren=True)
