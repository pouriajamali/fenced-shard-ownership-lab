"""Pinned private Windows SDK staging, called only inside the CI verify Job.
No installer, health command, public upload, global installation or fallback.
"""
import ctypes,hashlib,json,os,re,stat,time,urllib.parse,urllib.request,zipfile
from pathlib import Path
from ctypes import wintypes as W
import bounded_fixture as bounds
ROOT=Path(__file__).resolve().parents[1]
LOCK_SHA256='87e5e22cac8fbd8849074e70664e89f6a50357d986b0ce5e00e19b82df70f761'
URL='https://builds.dotnet.microsoft.com/dotnet/Sdk/10.0.404/dotnet-sdk-10.0.404-win-x64.zip'
RAW_BYTES=303618098
RAW_SHA512='330ddd2665b43cd2e428216a0d8ea1ac7bb19b5434fdc530e62010dc3b52823a620bf95489d628e1ed6f5122401793ee4887cca4a019122361a1231497f632ee'
INPUT_MAX=536870912
UNPACKED_MAX=2147483648
DOWNLOAD_SECONDS=180
STAGING_SECONDS=300

def need(value,reason):
 if not value:raise RuntimeError('HOLD_CI_SDK404_'+reason)

def actual_windows_job():
 need(os.name=='nt' and os.environ.get('GITHUB_ACTIONS')=='true','WINDOWS_HOSTED_JOB_ONLY')
 class Basic(ctypes.Structure):
  _fields_=[('processTime',ctypes.c_longlong),('jobTime',ctypes.c_longlong),('flags',W.DWORD),('minWorking',ctypes.c_size_t),('maxWorking',ctypes.c_size_t),('activeLimit',W.DWORD),('affinity',ctypes.c_size_t),('priority',W.DWORD),('scheduling',W.DWORD)]
 class IO(ctypes.Structure):_fields_=[(n,ctypes.c_ulonglong) for n in ('readOps','writeOps','otherOps','readBytes','writeBytes','otherBytes')]
 class Extended(ctypes.Structure):_fields_=[('basic',Basic),('io',IO),('processMemory',ctypes.c_size_t),('jobMemory',ctypes.c_size_t),('peakProcess',ctypes.c_size_t),('peakJob',ctypes.c_size_t)]
 class CPU(ctypes.Structure):_fields_=[('flags',W.DWORD),('rate',W.DWORD)]
 k=ctypes.WinDLL('kernel32',use_last_error=True);k.GetCurrentProcess.restype=W.HANDLE;k.IsProcessInJob.argtypes=[W.HANDLE,W.HANDLE,ctypes.POINTER(W.BOOL)];k.IsProcessInJob.restype=W.BOOL;k.QueryInformationJobObject.argtypes=[W.HANDLE,ctypes.c_int,ctypes.c_void_p,W.DWORD,ctypes.c_void_p];k.QueryInformationJobObject.restype=W.BOOL;k.GetActiveProcessorCount.argtypes=[W.WORD];k.GetActiveProcessorCount.restype=W.DWORD
 member=W.BOOL();need(k.IsProcessInJob(k.GetCurrentProcess(),None,ctypes.byref(member)) and member.value,'PARENT_ACTUAL_JOB_MEMBERSHIP_BEFORE_DOWNLOAD')
 limits=Extended();cpu=CPU();need(k.QueryInformationJobObject(None,9,ctypes.byref(limits),ctypes.sizeof(limits),None) and k.QueryInformationJobObject(None,15,ctypes.byref(cpu),ctypes.sizeof(cpu),None),'PARENT_JOB_QUERY')
 logical=int(k.GetActiveProcessorCount(0xffff));effective=cpu.rate*logical/10000
 need(limits.basic.flags&0x200 and limits.basic.flags&8 and limits.basic.flags&0x2000 and limits.jobMemory==4294967296 and limits.basic.activeLimit==64 and cpu.flags==5 and logical>0 and 0<effective<=2,'EXACT_PARENT_4G_CPU2_TASK64')
 return dict(kind='actual-Windows-parent-Job',memoryMax=int(limits.jobMemory),activeProcessMax=int(limits.basic.activeLimit),cpuRate=int(cpu.rate),logicalHostCpu=logical,effectiveCpuCores=effective,parentMembershipBeforeDownload=True,childMembershipBeforeResume='separate existing ci_pipeline outer Job receipt')

def load_lock():
 raw=(ROOT/'tools/ci-sdk404-win.lock.json').read_bytes();need(hashlib.sha256(raw).hexdigest()==LOCK_SHA256,'SOURCE_LOCK_SHA')
 value=json.loads(raw);need(value['schema']=='ci06-private-windows-sdk404/v1' and value['url']==URL and value['bytes']==RAW_BYTES and value['sha512']==RAW_SHA512 and value['sdkVersion']=='10.0.404' and value['coreRuntime']=='10.0.15' and value['memberCount']==5578 and value['unpackedBytes']==812144112,'EXACT_SOURCE_SPEC')
 need(len(value['members'])==5578 and len(value['notices'])==10,'COMPLETE_SOURCE_MEMBER_NOTICE_CATALOG');return value

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):raise RuntimeError('HOLD_CI_SDK404_REDIRECT_NOT_ALLOWED')

def download(raw,workspace):
 started=time.monotonic();count=0;digest=hashlib.sha512();opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect());last=started
 with opener.open(urllib.request.Request(URL,headers={'User-Agent':'ownership-ci-sdk404/1'}),timeout=20) as response,raw.open('xb') as output:
  need(response.status==200 and response.url==URL,'FIXED_OFFICIAL_RESPONSE');need(response.headers.get('Content-Length')==str(RAW_BYTES),'FIXED_CONTENT_LENGTH')
  while True:
   need(time.monotonic()-started<=DOWNLOAD_SECONDS,'DOWNLOAD_WALL');data=response.read(65536)
   if not data:break
   count+=len(data);need(count<=RAW_BYTES and count<=INPUT_MAX and time.monotonic()-started<=DOWNLOAD_SECONDS,'INPUT_OR_DOWNLOAD_WALL');digest.update(data);output.write(data)
   if time.monotonic()-last>=1:bounds.workspace_limit([workspace]);last=time.monotonic()
  output.flush();os.fsync(output.fileno())
 need(count==RAW_BYTES and digest.hexdigest()==RAW_SHA512,'RAW_SIZE_SHA512_BEFORE_EXTRACTION')
 bounds.workspace_limit([workspace]);elapsed=time.monotonic()-started
 need(elapsed<=DOWNLOAD_SECONDS,'DOWNLOAD_WALL_AFTER_FLUSH')
 return dict(bytes=count,sha512=digest.hexdigest(),seconds=elapsed)

def safe_name(name):
 need(isinstance(name,str) and 0<len(name)<=1024 and '\\' not in name and not name.startswith('/') and not any(ord(c)<32 or c in '<>:"|?*' for c in name),'MEMBER_NAME')
 parts=name.split('/');need(0<len(parts)<=32 and all(p and p not in ('.','..') and p.rstrip(' .')==p and not re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',p,re.I) for p in parts),'MEMBER_NAMESPACE')
 return '/'.join(parts)

def extract(raw,dest,lock,workspace,started):
 # Production caller supplies only the source-hash-verified lock, after raw SHA512.
 need(time.monotonic()-started<=STAGING_SECONDS,'STAGING_WALL_BEFORE_EXTRACTION')
 rows=lock['members'];expected={safe_name(r['path']):r for r in rows};need(len(expected)==len(rows) and len({x.casefold() for x in expected})==len(rows),'SOURCE_MEMBER_UNIQUENESS')
 with zipfile.ZipFile(raw) as z:
  infos=z.infolist();names=[safe_name(i.filename) for i in infos]
  need(len(infos)==lock['memberCount'] and len(names)==len(set(names))==len({n.casefold() for n in names}) and set(names)==set(expected),'EXACT_MEMBER_SET')
  need(sum(i.file_size for i in infos)==lock['unpackedBytes'] and lock['unpackedBytes']<=UNPACKED_MAX,'UNPACKED_CAP')
  for info,name in zip(infos,names):
   need(not info.is_dir() and not info.flag_bits&1 and info.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED) and stat.S_IFMT(info.external_attr>>16) in (0,stat.S_IFREG) and not info.external_attr&0x400 and info.file_size==expected[name]['bytes'],'REGULAR_MEMBER_LENGTH')
  dest.mkdir(exist_ok=False);canonical=dest.resolve();charged=0;last_disk=time.monotonic()
  for info,name in zip(infos,names):
   target=bounds.canonical(dest/name,exists=False);need(target.is_relative_to(canonical),'EXTRACTION_CONTAINMENT');target.parent.mkdir(parents=True,exist_ok=True);digest=hashlib.sha256();size=0
   with z.open(info) as stream,target.open('xb') as output:
    while True:
     data=stream.read(65536)
     if not data:break
     size+=len(data);charged+=len(data);need(size<=expected[name]['bytes'] and charged<=UNPACKED_MAX and time.monotonic()-started<=STAGING_SECONDS,'COPY_SIZE_OR_STAGING_WALL');digest.update(data);output.write(data)
   need(size==expected[name]['bytes'] and digest.hexdigest()==expected[name]['sha256'],'FULL_MEMBER_SHA256')
   if time.monotonic()-last_disk>=1:bounds.workspace_limit([workspace]);last_disk=time.monotonic()
  need(charged==lock['unpackedBytes'],'EXACT_TOTAL_COPY_BYTES')
 for row in lock['notices']:
  need(time.monotonic()-started<=STAGING_SECONDS,'STAGING_WALL_BEFORE_NOTICE')
  notice=dest/safe_name(row['path']);data=notice.read_bytes();need(len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],'FULL_ORIGINAL_NOTICE_BYTES')
 need((dest/'dotnet.exe').is_file() and (dest/'sdk/10.0.404/dotnet.dll').is_file() and (dest/'shared/Microsoft.NETCore.App/10.0.15/Microsoft.NETCore.App.runtimeconfig.json').is_file(),'EXACT_404_CORE15_LAYOUT')
 bounds.workspace_limit([workspace]);need(time.monotonic()-started<=STAGING_SECONDS,'STAGING_WALL_AFTER_EXTRACTION')

def stage_sdk(env):
 # Verify parent caps before opening a network connection or any downloaded target.
 caps=actual_windows_job();lock=load_lock();art=ROOT/'artifacts';bounds.workspace_limit([art]);work=bounds.canonical(art/'ci-private-sdk404-win-x64',exists=False);work.mkdir(exist_ok=False);raw=work/'sdk.zip';dest=work/'sdk';started=time.monotonic();transport=download(raw,art);extract(raw,dest,lock,art,started)
 env.update(DOTNET_ROOT=str(dest),DOTNET_ROOT_X64=str(dest),DOTNET_MULTILEVEL_LOOKUP='0',PATH=str(dest)+os.pathsep+env['PATH'])
 receipt=dict(schema='ci06-private-sdk404-staging/v1',status='RAW_AND_ALL_MEMBER_NOTICE_BYTES_VERIFIED_BEFORE_FIRST_SDK_TARGET',sourceLockSha256=LOCK_SHA256,transport=transport,actualParentCap=caps,files=lock['memberCount'],unpackedBytes=lock['unpackedBytes'],fullNotices=lock['notices'],firstSdkTarget='existing locked restore; not invoked by this helper',sdkHealthInstallerGlobalInstallUploadsOrSignatureClaim=False,workspaceGuard='4GiB acceptance guard; not filesystem quota',seconds=time.monotonic()-started)
 with (art/'ci-caps/verify/sdk404.json').open('x',encoding='utf-8') as output:json.dump(receipt,output,indent=2);output.write('\n');output.flush();os.fsync(output.fileno())
 # Acceptance deadline after extraction, notice checks and durable receipt writes.
 # Blocking I/O uses its socket timeout; the enclosing Job retains the hard wall.
 need(time.monotonic()-started<=STAGING_SECONDS,'TOTAL_STAGING_WALL_BEFORE_FIRST_SDK_TARGET')
 return str(dest/'dotnet.exe')

if __name__=='__main__':raise SystemExit('Library only; no SDK staging CLI')
