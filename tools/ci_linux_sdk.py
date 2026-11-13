"""Pinned private Linux SDK404 staging inside the existing owned generic64 worker.
Library only. No SDK commands, installers, extraction APIs or global settings.
"""
import gzip,hashlib,json,os,re,stat,sys,tarfile,time,urllib.parse,urllib.request
from pathlib import Path
import bounded_fixture as bounds
import bounded_actionlint as job
from profile_limits import ResourceWatch,validate_resource_counters
ROOT=Path(__file__).resolve().parents[1]
LOCK_SHA256='9b1ed597094b8ffa3decb86bb60d7fc12cfd5fc683e0d87b7fad6c2d7f45f81f'
URL='https://builds.dotnet.microsoft.com/dotnet/Sdk/10.0.404/dotnet-sdk-10.0.404-linux-x64.tar.gz'
RAW_BYTES=243138887
RAW_SHA512='577d0eb17fec33d029104c5c63a1ab0accc3e28776274abef2218dbac5af18d2109b5406d26b31d76f5c245215e3ba0926a94c20246c672c41847c9e1eb1dc50'
RAW_SHA256='c0610757a818fde4b960d27a0ac421f273068a05dc5ec7abafc01dbf84e9cb4d'
INPUT_MAX=536870912
UNPACKED_MAX=2147483648
DOWNLOAD_SECONDS=180
STAGING_SECONDS=300
EXPECTED_KERNEL={'memory.max':'4294967296','memory.swap.max':'0','pids.max':'64','cpu.max':'200000 100000'}
PHASE_FIELDS={'projectId','ownerPID','ownerProcessStartIdentity','randomToken','phase','sourceCommit','ownerOS','nativeUnit'}
HOSTS=frozenset(('builds.dotnet.microsoft.com',))

def need(value,reason):
 if not value:raise RuntimeError('HOLD_LINUX_SDK404_'+reason)

def elapsed(started,limit,reason):need(time.monotonic()-started<=limit,reason)

def read_small(path,cap=65536):
 with path.open('rb') as source:data=source.read(cap+1)
 need(len(data)<=cap,'CONTEXT_READ_CAP');return data

def validate_context(holder,owner,caps,actual):
 need(type(holder) is dict and type(owner) is dict and type(caps) is dict and type(actual) is dict and set(holder)==PHASE_FIELDS,'EXACT_PHASE_FIELDS')
 need(type(holder['ownerPID']) is int and holder['ownerPID']>0 and holder['ownerProcessStartIdentity']==actual['parentStart'],'PARENT_PID_START')
 need(type(actual['pid']) is int and actual['pid']>0 and actual['uid']!=0,'ACTUAL_NONROOT_PID')
 unit=owner.get('unit');need(type(unit) is str and re.fullmatch(r'ownershiplab-ci-[0-9a-f]{16}-verify',unit),'OWN_VERIFY_UNIT')
 expected=dict(projectId='06',ownerPID=holder['ownerPID'],ownerProcessStartIdentity=actual['parentStart'],randomToken=owner.get('token'),phase='verify',sourceCommit=actual['commit'],ownerOS='posix',nativeUnit=unit)
 need(all(type(holder[k]) is type(expected[k]) and holder[k]==expected[k] for k in PHASE_FIELDS),'EXACT_PHASE_BINDING')
 need(type(holder['randomToken']) is str and re.fullmatch('[0-9a-f]{64}',holder['randomToken']),'PHASE_TOKEN')
 need(owner.get('pid')==actual['pid'] and type(owner.get('pid')) is int and owner.get('processStart')==actual['selfStart'] and owner.get('stage')=='verify' and owner.get('sourceCommit')==actual['commit'],'SELF_OWNER_SOURCE_STAGE')
 need(owner.get('invocationId')==actual['invocation'] and type(actual['invocation']) is str and re.fullmatch('[0-9a-f]{32}',actual['invocation']) and owner.get('bootId')==actual['boot'],'OWN_INVOCATION_BOOT')
 group=str(Path('/sys/fs/cgroup')/f"user.slice/user-{actual['uid']}.slice/user@{actual['uid']}.service/app.slice"/(unit+'.service'))
 need(caps['kernel']==EXPECTED_KERNEL and caps['group']==group and caps['membership'].strip()=='0::'+group.removeprefix('/sys/fs/cgroup') and owner.get('group')==group and owner.get('actualCaps')==caps,'ACTUAL_GENERIC64_SOURCE_UNIT')
 return dict(sourceCommit=actual['commit'],stage='verify',unit=unit,pid=actual['pid'],processStart=actual['selfStart'],invocationId=actual['invocation'],bootId=actual['boot'],actualCaps=caps)

def actual_context(art):
 need(sys.platform=='linux' and os.getuid()!=0,'EXISTING_NONROOT_LINUX')
 need(os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('GITHUB_RUN_ATTEMPT')=='1','HOSTED_ATTEMPT')
 commit=os.environ.get('GITHUB_SHA','');need(re.fullmatch('[0-9a-f]{40}',commit),'SOURCE_SHA')
 holder=json.loads(read_small(art/'ci-lane.json'));owner=json.loads(read_small(art/'ci-caps/verify/unit-owner.json'));need(type(holder) is dict and type(holder.get('ownerPID')) is int and holder['ownerPID']>0,'PARENT_PID_TYPE')
 actual=dict(pid=os.getpid(),uid=os.getuid(),parentStart=job._start_identity(holder['ownerPID']),selfStart=job._start_identity(os.getpid()),commit=commit,invocation=os.environ.get('INVOCATION_ID'),boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
 caps=bounds.kernel_limits();safe=validate_context(holder,owner,caps,actual);job.check_owner(holder,holder);return safe,caps

def load_spec():
 path=ROOT/'tools/ci-sdk404-linux.lock.json';raw=read_small(path,8388608);need(hashlib.sha256(raw).hexdigest()==LOCK_SHA256,'SOURCE_LOCK_SHA');value=json.loads(raw)
 need(value['schema']=='ci06-private-linux-sdk404/v1' and value['url']==URL and value['bytes']==RAW_BYTES and value['sha512']==RAW_SHA512 and value['sha256']==RAW_SHA256 and value['sdkVersion']=='10.0.404' and value['coreRuntime']=='10.0.15','SOURCE_SPEC')
 need(value['memberCount']==5631 and value['fileCount']==4907 and value['directoryCount']==724 and value['unpackedBytes']==644980579 and len(value['notices'])==10 and value['links']==[],'SOURCE_TYPED_COUNTS')
 need(value['auxiliaryMetadata']['count']==1913 and value['auxiliaryMetadata']['notSdkMembers'] is True,'SEPARATE_AUXILIARY_RECORDS');return value

class FixedRedirect(urllib.request.HTTPRedirectHandler):
 max_redirections=3
 max_repeats=1
 def redirect_request(self,request,fp,code,msg,headers,newurl):
  target=urllib.parse.urlsplit(urllib.parse.urljoin(request.full_url,newurl));need(target.scheme=='https' and target.hostname in HOSTS and target.port in (None,443) and target.username is None and target.password is None and not target.fragment,'REDIRECT_BEFORE_REQUEST')
  return super().redirect_request(request,fp,code,msg,headers,target.geturl())

def download(raw,workspace,spec,started):
 begin=time.monotonic();total=0;h512=hashlib.sha512();h256=hashlib.sha256();last=begin;opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),FixedRedirect())
 with opener.open(urllib.request.Request(spec['url'],headers={'User-Agent':'ownership-ci-linux-sdk404/1'}),timeout=20) as response,raw.open('xb') as output:
  final=urllib.parse.urlsplit(response.url);need(response.status==200 and final.scheme=='https' and final.hostname in HOSTS and final.port in (None,443) and final.username is None and final.password is None and not final.fragment,'OFFICIAL_RESPONSE')
  need(response.headers.get('Content-Length')==str(spec['bytes']),'EXACT_CONTENT_LENGTH')
  while True:
   elapsed(begin,DOWNLOAD_SECONDS,'DOWNLOAD_WALL');elapsed(started,STAGING_SECONDS,'STAGING_WALL_DURING_DOWNLOAD');data=response.read(65536)
   if not data:break
   total+=len(data);need(total<=spec['bytes'] and total<=INPUT_MAX,'RAW_INPUT_CAP');h512.update(data);h256.update(data);output.write(data);elapsed(begin,DOWNLOAD_SECONDS,'DOWNLOAD_WALL_AFTER_READ')
   if time.monotonic()-last>=1:bounds.workspace_limit([workspace]);last=time.monotonic()
  output.flush();os.fsync(output.fileno())
 need(total==spec['bytes'] and h512.hexdigest()==spec['sha512'] and h256.hexdigest()==spec['sha256'],'RAW_SIZE_BOTH_DIGESTS_BEFORE_PARSER');bounds.workspace_limit([workspace]);elapsed(begin,DOWNLOAD_SECONDS,'DOWNLOAD_WALL_AFTER_FLUSH');elapsed(started,STAGING_SECONDS,'STAGING_WALL_AFTER_DOWNLOAD')
 return dict(bytes=total,sha512=h512.hexdigest(),sha256=h256.hexdigest(),seconds=time.monotonic()-begin)

def safe_name(name,root=False):
 need(type(name) is str and len(name)<=4096 and not any(ord(c)<32 or ord(c)==127 for c in name) and '\\' not in name and ':' not in name and not name.startswith('/'),'TAR_NAME_FRAME')
 if name.startswith('./'):name=name[2:]
 if name in ('','.'):need(root,'ROOT_DIRECTORY_ONLY');return '.'
 bits=name.rstrip('/').split('/');need(all(x and x not in ('.','..') for x in bits) and len(bits)<=64,'TAR_NAME_NAMESPACE');return '/'.join(bits)

def spec_index(spec):
 rows=spec['members'];need(len(rows)==spec['memberCount'] and len(rows)<=12000,'SPEC_MEMBER_COUNT');names=[r['path'] for r in rows];need(names and names[0]=='.' and len(set(names))==len(names),'SPEC_ORDER_UNIQUENESS');table=dict(zip(names,rows))
 for row in rows:
  need(row['path']==safe_name(row['path'],row['type']=='directory') and row['type'] in ('file','directory') and row['tarUid']==row['tarGid']==2001 and row['pax']=={} and row['mode'] in (0o644,0o744,0o755),'SPEC_E0_DATA_ONLY')
  need(type(row['bytes']) is int and row['bytes']>=0 and (row['type']!='directory' or row['bytes']==0),'SPEC_LENGTH_KIND')
  if row['path']!='.':
   parent=str(Path(row['path']).parent).replace('\\','/');need(parent in table and table[parent]['type']=='directory','SPEC_FILE_DIRECTORY_CONFLICT')
 need(sum(r['bytes'] for r in rows)==spec['unpackedBytes'] and spec['unpackedBytes']<=UNPACKED_MAX,'SPEC_EXPANDED_CAP');return table

class TarReader:
 def __init__(self,stream,started):self.stream=stream;self.started=started;self.total=0
 def read(self,size):
  need(type(size) is int and 0<=size<=65536,'BOUNDED_TAR_READ');data=self.stream.read(size);self.total+=len(data);need(self.total<=UNPACKED_MAX,'TAR_STREAM_CAP');elapsed(self.started,STAGING_SECONDS,'STAGING_WALL_TAR_READ');return data
 def exact(self,size):
  need(0<=size<=65536,'BOUNDED_EXACT_READ');result=bytearray()
  while len(result)<size:
   part=self.read(size-len(result));need(part,'TAR_TRUNCATION');result.extend(part)
  return bytes(result)

def ordinary_ancestry(path):
 for node in (path,*path.parents):
  if node.exists() or node.is_symlink():
   info=node.lstat();need(not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400,'OWN_PATH_NO_LINK_REPARSE')

def copy_target(dest,name,table):
 target=dest if name=='.' else dest/name;ordinary_ancestry(target);need(target.resolve().is_relative_to(dest.resolve()),'COPY_CONTAINMENT')
 if name!='.':
  parent=str(Path(name).parent).replace('\\','/');need(parent in table and table[parent]['type']=='directory' and target.parent.is_dir(),'DECLARED_EXISTING_PARENT')
 return target

def walk(raw,spec,started,dest=None,workspace=None):
 """Two passes use the same strict byte parser; first pass creates no SDK tree."""
 table=spec_index(spec);rows=spec['members'];aux=spec['auxiliaryMetadata']['rows'];typed=meta=expanded=0;pending=None;last=time.monotonic()
 for notice in spec['notices']:
  row=table.get(notice['path']);need(row is not None and row['type']=='file' and row['bytes']==notice['bytes'] and row['sha256']==notice['sha256'],'NOTICE_MAP_BEFORE_COPY')
 with gzip.open(raw,'rb') as source:
  reader=TarReader(source,started)
  while True:
   header=reader.exact(512)
   if header==bytes(512):
    need(reader.exact(512)==bytes(512),'TAR_TWO_END_BLOCKS')
    while True:
     tail=reader.read(65536)
     if not tail:break
     need(not any(tail),'TAR_TRAILING_NONZERO')
    break
   need(typed+meta<12000,'TAR_HEADER_CAP')
   try:info=tarfile.TarInfo.frombuf(header,'utf-8','strict')
   except (tarfile.HeaderError,UnicodeError,ValueError) as error:raise RuntimeError('HOLD_LINUX_SDK404_TAR_HEADER_CHECKSUM_FRAME') from error
   for at,width in ((100,8),(108,8),(116,8),(124,12),(136,12),(148,8)):
    numeric=header[at:at+width].strip(b' \0');need(numeric and re.fullmatch(b'[0-7]+',numeric),'TAR_OCTAL_NUMERIC_FRAME')
   if b'\0' in header[:100]:need(not any(header[:100].split(b'\0',1)[1]),'TAR_NAME_NUL_PADDING')
   magic=(header[257:263],header[263:265]);need(magic in ((b'ustar\0',b'00'),(b'ustar ',b' \0')),'TAR_HEADER_DIALECT')
   need(info.type in (tarfile.REGTYPE,tarfile.AREGTYPE,tarfile.DIRTYPE,tarfile.GNUTYPE_LONGNAME),'TAR_TYPE_NO_PAX_LINK_SPECIAL_SPARSE')
   need(not info.linkname and info.devmajor==0 and info.devminor==0 and not info.pax_headers and info.sparse is None,'TAR_NO_LINK_DEVICE_PAX_SPARSE')
   if magic[0]==b'ustar ':need(header[482]==0 and all(c in (0,32,48) for c in header[386:495]),'GNU_NO_SPARSE_EXTENSION')
   need(type(info.size) is int and 0<=info.size<=UNPACKED_MAX,'TAR_SIZE_CAP')
   if info.type==tarfile.GNUTYPE_LONGNAME:
    need(pending is None and meta<len(aux) and 1<=info.size<=4096,'GNU_L_ORDER_LENGTH')
    row=aux[meta];need(row['metadataHeaderType']=='L' and row['bytes']==info.size,'GNU_L_SEPARATE_SIZE')
    need(info.name=='././@LongLink','GNU_L_HEADER_NAME');payload=reader.exact(info.size);need(hashlib.sha256(payload).hexdigest()==row['sha256'],'GNU_L_PAYLOAD_HASH')
    need(payload[-1:]==b'\0' and b'\0' not in payload[:-1],'GNU_L_NUL_FRAME')
    try:pending=payload[:-1].decode('utf-8','strict')
    except UnicodeError as error:raise RuntimeError('HOLD_LINUX_SDK404_GNU_L_UTF8') from error
    safe_name(pending,pending.rstrip('/') in ('.','./'));meta+=1
   else:
    need(typed<len(rows),'TAR_EXTRA_TYPED');row=rows[typed];kind='directory' if info.type==tarfile.DIRTYPE else 'file'
    try:short=header[:100].split(b'\0',1)[0].decode('utf-8','strict')
    except UnicodeError as error:raise RuntimeError('HOLD_LINUX_SDK404_HEADER_NAME_UTF8') from error
    resolved=pending if pending is not None else info.name;pending=None
    need(short==row['tarHeaderName'] and safe_name(resolved,kind=='directory')==row['path'],'TAR_TYPED_ORDER_RAW_AND_FINAL_NAME')
    need(kind==row['type'] and info.size==row['bytes'] and info.mode==row['mode'] and info.uid==row['tarUid']==2001 and info.gid==row['tarGid']==2001,'TAR_TYPED_SIZE_E0_DATA_ONLY')
    target=copy_target(dest,row['path'],table) if dest is not None else None;out=None;digest=hashlib.sha256()
    if target is not None:
     if kind=='directory':
      if row['path']!='.':target.mkdir(mode=0o700,exist_ok=False)
      need(target.is_dir() and target.lstat().st_uid==os.getuid(),'COPY_OWN_DIRECTORY')
     else:out=os.fdopen(os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600),'wb')
    try:
     left=info.size
     while left:
      block=reader.exact(min(left,65536));digest.update(block);left-=len(block)
      if out is not None:out.write(block)
      if workspace is not None and time.monotonic()-last>=1:bounds.workspace_limit([workspace]);last=time.monotonic()
     if out is not None:out.flush();os.fsync(out.fileno())
    finally:
     if out is not None:out.close()
    if kind=='file':need(digest.hexdigest()==row['sha256'],'TAR_FILE_HASH')
    if target is not None:target.chmod(row['mode'])
    expanded+=info.size;need(expanded<=UNPACKED_MAX,'EXPANDED_CAP');typed+=1
   padding=(-info.size)%512
   if padding:need(not any(reader.exact(padding)),'TAR_ZERO_PAYLOAD_PADDING')
  need(pending is None and typed==len(rows)==spec['memberCount'] and meta==len(aux)==spec['auxiliaryMetadata']['count'] and expanded==spec['unpackedBytes'],'TAR_COMPLETE_COUNTS_END')
 if workspace is not None:bounds.workspace_limit([workspace])
 elapsed(started,STAGING_SECONDS,'STAGING_WALL_AFTER_FULL_TAR')
 return dict(typedMembers=typed,gnuLongnameAuxiliary=meta,expandedFileBytes=expanded)

def final_map(dest,spec,started,workspace):
 table=spec_index(spec);found={'.'}
 for path in dest.rglob('*'):
  name=path.relative_to(dest).as_posix();need(name in table and name not in found,'FINAL_NO_EXTRA_DUPLICATE');found.add(name)
 need(found==set(table),'FINAL_COMPLETE_MAP')
 for name,row in table.items():
  path=copy_target(dest,name,table);info=path.lstat();need(info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==row['mode'],'FINAL_OWN_NATIVE_MODE')
  need((stat.S_ISDIR(info.st_mode) if row['type']=='directory' else stat.S_ISREG(info.st_mode)),'FINAL_TYPE')
  if row['type']=='file':
   digest=hashlib.sha256();total=0
   with path.open('rb') as source:
    while True:
     block=source.read(65536)
     if not block:break
     total+=len(block);need(total<=row['bytes'],'FINAL_FILE_CAP');digest.update(block);elapsed(started,STAGING_SECONDS,'STAGING_WALL_FINAL_MAP')
   need(total==row['bytes'] and digest.hexdigest()==row['sha256'],'FINAL_FILE_BYTES')
 # Notice identities are a subset of this complete freshly rehashed map, never renamed/truncated substitutes.
 for notice in spec['notices']:
  row=table[notice['path']];need(row['bytes']==notice['bytes'] and row['sha256']==notice['sha256'],'FINAL_TEN_ORIGINAL_NOTICES')
 bounds.workspace_limit([workspace]);elapsed(started,STAGING_SECONDS,'STAGING_WALL_AFTER_NOTICES_WORKSPACE')

def write_receipt(path,value):
 ordinary_ancestry(path.parent);need(path.parent.is_dir(),'EXISTING_RECEIPT_PARENT');raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode();need(len(raw)<=131072,'SAFE_RECEIPT_CAP')
 with path.open('xb') as output:output.write(raw);output.flush();os.fsync(output.fileno())

def stage_sdk(env):
 started=time.monotonic();art=ROOT/'artifacts';safe,caps=actual_context(art);watch=ResourceWatch(caps);status='HOLD';resources_written=False
 try:
  spec=load_spec();ordinary_ancestry(art);bounds.workspace_limit([art]);work=art/'ci-private-sdk404-linux-x64';need(not work.exists() and not work.is_symlink(),'FRESH_PRIVATE_WORK');work.mkdir(mode=0o700,exist_ok=False)
  info=work.lstat();need(stat.S_IMODE(info.st_mode)==0o700 and info.st_uid==os.getuid(),'PRIVATE_NATIVE_OWN_WORK')
  raw=work/'sdk.tar.gz';dest=work/'sdk';elapsed(started,STAGING_SECONDS,'STAGING_WALL_BEFORE_NETWORK');transport=download(raw,art,spec,started);before=walk(raw,spec,started,workspace=art)
  # No SDK target directory exists until all raw/header/member/notice bytes pass.
  watch.sample();elapsed(started,STAGING_SECONDS,'STAGING_WALL_BEFORE_COPY_TARGET');dest.mkdir(mode=0o700,exist_ok=False);copied=walk(raw,spec,started,dest,art);need(copied==before,'COPY_SAME_MAP');final_map(dest,spec,started,art)
  exe=dest/'dotnet';need(exe.is_file() and os.access(exe,os.X_OK) and (dest/'sdk/10.0.404/dotnet.dll').is_file() and (dest/'shared/Microsoft.NETCore.App/10.0.15').is_dir(),'PINNED_PRIVATE_LAYOUT')
  counters=watch.finish();validate_resource_counters(counters)
  write_receipt(art/'ci-caps/verify/sdk404-linux-resources.json',dict(schema='ci06-linux-sdk404-resources/v1',status='OBSERVATIONS_ONLY_CALLER_ACCEPTANCE_REQUIRED',resources=counters));resources_written=True
  receipt=dict(schema='ci06-private-linux-sdk404-staging/v1',status='BYTE_MAP_OBSERVATIONS_ONLY_CALLER_ACCEPTANCE_REQUIRED',sourceLockSha256=LOCK_SHA256,transport=transport,context=safe,counts=before,notices=spec['notices'],resources=counters,firstSdkTarget='existing locked restore; not invoked by helper',workspaceGuard='4GiB elapsed acceptance; not a filesystem quota',sdkHealthInstallerGlobalInstallArtifactOrSignatureClaim=False,secondsBeforeReceipt=time.monotonic()-started)
  write_receipt(art/'ci-caps/verify/sdk404-linux.json',receipt);bounds.workspace_limit([art]);elapsed(started,STAGING_SECONDS,'STAGING_WALL_AFTER_RECEIPT_FLUSH_WORKSPACE')
  env.update(DOTNET_ROOT=str(dest),DOTNET_ROOT_X64=str(dest),DOTNET_MULTILEVEL_LOOKUP='0',PATH=str(dest)+os.pathsep+env['PATH'])
  elapsed(started,STAGING_SECONDS,'STAGING_WALL_BEFORE_SDK_RETURN');status='ACCEPTED';return str(exe)
 finally:
  if status!='ACCEPTED' and not resources_written:
   counters=watch.finish()
   write_receipt(art/'ci-caps/verify/sdk404-linux-resources.json',dict(schema='ci06-linux-sdk404-resources/v1',status='HOLD',resources=counters))

if __name__=='__main__':raise SystemExit('Library only; existing owned verify worker is the sole caller.')
