"""Fixed own06 local Windows lock/build stages; no acquisition or generic command CLI."""
import argparse,base64,datetime,hashlib,json,os,re,secrets,shutil,subprocess,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
import local_input06 as I
need=I.need
PROJECTS=('src/Ownership/Ownership.csproj','src/Ownership.Cli/Ownership.Cli.csproj','tests/Ownership.Tests/Ownership.Tests.csproj')
BUDGETS={'locks':600,'verify':900,'package':900}
MANIFEST='tools/local06-input-admission.json'
REPOSITORY_SIGNERS=frozenset(('0e5f38f57dc1bcc806d8494f4f90fbcedd988b46760709cbeec6f4219aa6157d','5a2901d6ada3d18260b9c6dfe2133c95d74b9eef6ae0e5dc334c8454d1477df4','1f4b311d9acc115c8dc8018b5a49e00fce6da8e2855f9f014ca6f34570bc482d'))
MANAGED_MODE='STANDARD_ONLINE_WINDOWS_SDK_VERIFICATION_NO_REPORTED_UNKNOWN_OR_ISSUE'

def windows_base_environment():
 # Same existing validated nonsecret machine paths as the original CI controller.
 from ci_pipeline import validated_windows_machine_paths
 names=('SystemRoot','WINDIR','COMSPEC','PATHEXT','USERPROFILE','APPDATA','LOCALAPPDATA')
 env={k:os.environ[k] for k in names if k in os.environ};env.update(validated_windows_machine_paths());env.update(PATH='C:/Windows/System32;C:/Windows',PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1');return env

def seconds(stage):
 need(stage in BUDGETS,'FINITE_LOCAL_STAGE');return BUDGETS[stage]

def crypto_row(x,now):
 need(x.get('cryptographicAdmission') is True,'ACTUAL_CRYPTO_PROOF_REQUIRED')
 if x.get('kind')=='native-corehost':
  need(x.get('cmsPublisherVerified') is True and x.get('RFC3161Verified') is True and x.get('revocationCoverageVerified') is True,'ACTUAL_CRYPTO_PROOF_REQUIRED')
 else:
  need(x.get('kind')=='managed' and x.get('verificationMode')==MANAGED_MODE and x.get('actualPackageSuccess') is True and type(x.get('reportedIssueCount')) is int and x['reportedIssueCount']==0 and x.get('sdkReportedRepositoryLeaf') in REPOSITORY_SIGNERS,'ACTUAL_MANAGED_SDK_PACKAGE_PROOF')
  observed=x.get('originalVerificationObservedAtUnix');need(type(observed) is int and 0<=now-observed<=86400,'ORIGINAL_MANAGED_SIGNATURE_WINDOW')
  code=x.get('actualGlobalCommandExitCode');need(type(code) is int and (code==0 and x.get('reusedActualPackageSuccess') is False or code==1 and x.get('reusedActualPackageSuccess') is True),'PRESERVE_PARTIAL_BATCH_GLOBAL_HOLD')

def admission(root,now):
 """Source-reviewed data gate. It supplies no invented NuGet normalization formula."""
 p=root/MANIFEST;need(p.is_file(),'REAL_INPUT_ADMISSION_NOT_YET_DELIVERED');v=I.read(p)
 need(v.get('schema')=='own06-verified-product-inputs/v1' and v.get('state')=='PRODUCER04_PROOFS_REVIEWED_OWN06_INPUTS_ADMITTED' and v.get('projectId')=='06' and v.get('repository')==I.REPOSITORY,'OWN_REVIEWED_INPUT_ADMISSION')
 need(v.get('inputContractSha256')==I.digest(root/'tools/local06-input-contract.json'),'EXACT_INPUT_CONTRACT')
 advisory=v.get('advisory',{});observed=advisory.get('observedAtUnix');expires=advisory.get('expiresAtUnix')
 need(type(observed) is int and type(expires) is int and observed<=now<expires<=observed+86400 and expires-now>=300,'REAL_ADVISORY_FRESHNESS_NO_EXTENSION')
 pki=v.get('certificateWindow',{});verified=pki.get('nativeVerifiedAtUnix');valid=pki.get('expiresAtUnix');crls=pki.get('inputCRLs',[])
 need(type(verified) is int and type(valid) is int and verified<=now<valid<=verified+86400 and valid-now>=300 and type(crls) is list and bool(crls),'CURRENT_CERTIFICATE_PROOF_WINDOW')
 for crl in crls:need(type(crl.get('thisUpdate')) is int and type(crl.get('nextUpdate')) is int and crl['thisUpdate']<=now<crl['nextUpdate'] and valid<=crl['nextUpdate'],'CURRENT_EXACT_CRL_TIME_WINDOW')
 expected={(x['id'].lower(),x['version']):x for x in I.read(root/'tools/local06-input-contract.json')['packages']};rows=v.get('packages',[])
 need(len(rows)==38 and len(expected)==38 and {(x['id'].lower(),x['version']) for x in rows}==set(expected),'EXACT_34_MANAGED_PLUS4_COREHOST')
 for x in rows:
  crypto_row(x,now)
  for key,size in [('rawSha512',128),('verificationReceiptSha256',64)]:need(type(x.get(key)) is str and len(x[key])==size and all(c in '0123456789abcdef' for c in x[key]),'INPUT_HASH_ENCODING')
  norm=x.get('normalizedContentHash');need(type(norm) is str and len(base64.b64decode(norm,validate=True))==64,'ACTUAL_NORMALIZED_HASH_REQUIRED')
  need(x.get('kind')==('native-corehost' if x['id'].lower().startswith('microsoft.netcore.app.') else 'managed'),'EXACT_PACKAGE_VERIFICATION_KIND')
  old=expected[(x['id'].lower(),x['version'])]['normalizedContentHash'];need(old is None or norm==old,'UNCHANGED_MANAGED_LOCK_IDENTITY')
  need(type(x.get('bytes')) is int and 0<x['bytes']<=67108864 and x.get('retainedData') and x.get('producerProjectId')=='04','EXACT_PROVIDER_INPUT_AND_NOTICES')
 return v

def retained_posix_path(value):
 text=str(value)
 if len(text)>3 and text[1]==':' and text[2] in ('/',chr(92)):
  drive=text[0].lower();tail=text[3:].replace(chr(92),'/');need(drive in ('c','e') and '..' not in tail.split('/'),'EXACT_RETAINED_INPUT_DRIVE')
  return '/mnt/'+drive+'/'+tail
 return text

def input_path(value):
 return Path(retained_posix_path(value) if os.name=='posix' else value)


def verify_file(row,pathkey,hashkey,limit):
 p=input_path(row[pathkey]);I.ordinary(p);need(p.is_file() and p.stat().st_size<=limit,'RETAINED_PROOF_BYTES')
 need(I.digest(p)==row[hashkey],'RETAINED_PROOF_SHA');return p

def producer_record(x):
 p=verify_file(x,'verificationReceiptPath','verificationReceiptSha256',1048576);proof=I.read(p)
 rows=proof.get('packages',[]);matches=[row for row in rows if row.get('id','').lower()==x['id'].lower() and row.get('version')==x['version']]
 need(len(matches)==1,'EXACT_PRODUCER_PACKAGE_PROOF');row=matches[0];raw=row.get('rawSignedArchive',row)
 need(raw.get('sha512')==x['rawSha512'] and raw.get('bytes')==x['bytes'] and row.get('normalizedNuGetContentHash')==x['normalizedContentHash'],'PRODUCER_RAW_NORMALIZED_PROOF_BINDING')
 if x.get('kind')=='managed':
  actual=row.get('actualSDKVerification',{});need(actual.get('actualPackageSuccess') is True and actual.get('reportedSignatureOutcome')=='ACTUAL_PACKAGE_VERIFIED_NO_REPORTED_ISSUE' and actual.get('rawSHA256')==x['rawSha256'] and actual.get('actualSDKLogSHA256')==x['actualSDKBlockSha256'] and actual.get('sdkReportedRepositoryLeaf',{}).get('certificateSHA256')==x['sdkReportedRepositoryLeaf'] and actual.get('actualGlobalCommandExitCode')==x['actualGlobalCommandExitCode'],'ACTUAL_MANAGED_RECORD_BINDING')
 return row

def managed_report(x):
 p=verify_file(x,'actualSDKBlockPath','actualSDKBlockSha256',1048576);text=p.read_text(encoding='utf-8-sig');identity=x['id']+'.'+x['version']
 need(text.count('Content hash: '+x['normalizedContentHash'])==1 and text.count("Successfully verified package '"+identity+"'.")==1 and not re.search(r'\b(?:warning|error|unknown)\b|\bNU[0-9]{4}\b|validation failed',text,re.I),'ACTUAL_MANAGED_REPORT_BLOCK')
 need(x['sdkReportedRepositoryLeaf'].lower() in text.lower().replace(':',''),'ACTUAL_REPOSITORY_CERTIFICATE_REPORT')


def prepare_feed(root,out,v):
 """Recheck exact admitted bytes in this phase, then stage only the finite feed."""
 feed=out/'feed';feed.mkdir()
 verify_file(v['advisory'],'receiptPath','receiptSha256',1048576)
 verify_file(v['certificateWindow'],'receiptPath','receiptSha256',1048576)
 for x in v['packages']:
  producer_record(x)
  raw=input_path(x['path']);I.ordinary(raw);need(raw.is_file() and raw.stat().st_size==x['bytes'],'CURRENT_RAW_PACKAGE_SIZE')
  with raw.open('rb') as f:need(hashlib.file_digest(f,'sha512').hexdigest()==x['rawSha512'],'CURRENT_RAW_SIGNED_PACKAGE_IDENTITY')
  if x['kind']=='managed':managed_report(x)
  for datum in x['retainedData']:verify_file(datum,'path','sha256',1048576)
  dest=feed/(x['id'].lower()+'.'+x['version'].lower()+'.nupkg');shutil.copyfile(raw,dest)
  with dest.open('rb') as f:need(hashlib.file_digest(f,'sha512').hexdigest()==x['rawSha512'],'COPIED_FEED_BYTES')
 config=out/'NuGet.Config';tree=ET.Element('configuration');sources=ET.SubElement(tree,'packageSources');ET.SubElement(sources,'clear');ET.SubElement(sources,'add',key='own06-verified-local',value=str(feed))
 audit=ET.SubElement(tree,'auditSources');ET.SubElement(audit,'clear');ET.SubElement(audit,'add',key='official-nuget-current-advisory',value='https://api.nuget.org/v3/index.json',protocolVersion='3')
 ET.ElementTree(tree).write(config,encoding='utf-8',xml_declaration=True)
 return config

def plan(stage,dotnet,config,packages,unit):
 seconds(stage);restore=lambda p,mode:[str(dotnet),'restore',p,mode,'--configfile',str(config),'--packages',str(packages)]
 if stage=='locks':return [restore(p,'--force-evaluate')+['--use-lock-file'] for p in PROJECTS]
 if stage=='package':return [restore(PROJECTS[2],'--locked-mode')]
 return [restore(p,'--locked-mode') for p in PROJECTS]+[[str(dotnet),'run','--project',PROJECTS[2],'-c','Release','--no-restore','--','-noLogo','-xml',str(unit)],[str(dotnet),'build',PROJECTS[1],'-c','Release','--no-restore']]

WINDOWS_VERIFY_REFERENCE='state/execution-evidence/net11-local-build06/verify-04c81c1ee0484045a4bc6625/receipt.json'
WINDOWS_VERIFY_SHA='097e8ab7bed1803117d76800700698b57b18ce34205c4aeeed098a84c72b7a31'
WINDOWS_VERIFY_COMMIT='48d7ec83c89c7def191a560d49d4b5e00c181e98'
REPACKAGE_ONLY_CHANGES=frozenset(('tools/local_build06.py','tools/local_linux_build06.py','tools/test_local_build06.py','tools/ci06-source-pins.json','docs/RELEASE-v0.1.0-preview.8.md','README.md'))

def repackage_changes(names):
 need(set(names)<=REPACKAGE_ONLY_CHANGES,'REPACKAGE_APPLICATION_OR_VALIDATOR_SOURCE_CHANGED')

def prior_windows_verification(root):
 p=root.parents[1]/WINDOWS_VERIFY_REFERENCE;need(I.digest(p)==WINDOWS_VERIFY_SHA,'EXACT_PRIOR_WINDOWS_VERIFY_RECEIPT');v=I.read(p)
 need(v['state']=='OWN06_LOCAL_VERIFY_COMMANDS_PASSED' and v['sourceCommit']==WINDOWS_VERIFY_COMMIT and v['released'] is True and v['wholePhaseBudgetMet'] is True and v['process']['actualCap']['activeProcessesAtTeardown']==0,'CLOSED_PRIOR_WINDOWS_VERIFY')
 changed=subprocess.check_output(['C:/Program Files/Git/cmd/git.exe','-C',str(root),'diff','--name-only',WINDOWS_VERIFY_COMMIT,'HEAD'],timeout=10).decode().splitlines();repackage_changes(changed)
 return {'sourceCommit':WINDOWS_VERIFY_COMMIT,'receipt':str(p),'receiptSha256':WINDOWS_VERIFY_SHA,'scope':'Prior real50 units/original oracle,notice,signature-verifier and SBOM regressions reused only with unchanged application/SQL/locks/target/notices/validators; new source archive rebuilt and checked.'}

def lease(s):
 need(I.digest(I.LEASE)==s['leaseSHA256'],'CURRENT_STAGE_LEASE_BYTES');h=I.read(I.LEASE)
 need(h.get('projectId')=='06' and h.get('randomToken')==s['leaseToken'] and h.get('ownerPID')==s['supervisorPID'] and h.get('ownerProcessStartIdentity')==s['supervisorStartIdentity'] and h.get('phase')=='LOCAL_WINDOWS_'+s['stage'].upper() and h.get('sourceCommit')==s['commit'] and h.get('receiptDirectory')==s['receiptDirectory'],'EXACT_STAGE_LEASE')

def validate_spec(s,now):
 budget=seconds(s.get('stage'));need(s.get('purpose')=='OWN06_LOCAL_WINDOWS_LOCK_BUILD' and s.get('projectId')=='06' and s.get('repository')==I.REPOSITORY,'STAGE_SCOPE')
 need(type(s.get('startNs')) is int and type(s.get('endNs')) is int and 0<s['startNs']<=now<s['endNs'] and s['endNs']-s['startNs']==budget*10**9,'SINGLE_AFTER_CLAIM_PHASE_CLOCK')
 need(type(s.get('workerPID')) is int and s['workerPID']>0 and type(s.get('supervisorPID')) is int and s['supervisorPID']>0 and s['workerPID']!=s['supervisorPID'],'HELD_STAGE_IDENTITIES')
 need(str(s.get('workerStart','')).startswith('FILETIME:') and str(s.get('supervisorStartIdentity','')).startswith('FILETIME:'),'STAGE_START_IDENTITIES')
 need(s.get('helperSha256')==I.HELPER_SHA and s.get('facadeSha256')==I.FACADE_SHA and s.get('beforeResume',{}).get('membership') is True and s['beforeResume'].get('retainedCreationHandles') is True,'EXACT_HELD_SOURCE')

def current_input(root,controller,out,s,j):
 need(os.getpid()==s['workerPID'] and j._start_identity(os.getpid())==s['workerStart'] and os.getppid()==s['supervisorPID'],'ACTUAL_STAGE_MAIN');cap=j.current_witness(s['jobName']);held=s['beforeResume']
 who={'pid':os.getpid(),'processStartIdentity':s['workerStart'],'jobName':s['jobName'],'memoryMaxBytes':cap['memoryMax'],'tasksMax':cap['tasksMax'],'cpuRate':cap['cpuRate'],'logicalHostCpu':cap['logicalHostCpu']}
 before={**who,'memoryMaxBytes':held['memoryMax'],'tasksMax':held['activeProcessMax'],'cpuRate':held['cpuRate'],'logicalHostCpu':held['logicalHostCpu'],'state':'SUSPENDED','membershipBeforeRelease':held['membership'],'retainedStartHandle':held['retainedCreationHandles']}
 profile=root/'profiles/local-windows-build06.json';contract=root/'tools/ci06-normal-contract.json';pins=root/'tools/ci06-source-pins.json'
 bootstrap={'pythonVersion':'.'.join(map(str,sys.version_info[:3])),'pythonExeSha256':I.digest(sys.executable),'gitSha256':I.digest('C:/Program Files/Git/cmd/git.exe')}
 caps={'schema':'sdk11-own-current-cap-evidence/v1','projectId':'06','repository':I.REPOSITORY,'sourceCommit':s['commit'],'sourceTree':s['tree'],'profileSha256':I.digest(profile),'controllerSha256':I.digest(controller),'bootstrap':bootstrap,'worker':who,'heldBeforeExec':before,'supervisor':{'pid':s['supervisorPID'],'processStartIdentity':s['supervisorStartIdentity'],'deadlineMonotonicNs':s['endNs']},'rowStartedMonotonicNs':s['startNs'],'deadlineMonotonicNs':s['endNs']}
 cp=out/'own-current-caps.json';ap=out/'local-input-context.json';I.write(cp,caps);I.write(ap,{'schema':'sdk11-local-input-current/v1','state':'OWN_CURRENT_INPUT_CONTEXT_BOUND','projectId':'06','repository':I.REPOSITORY,'rid':'win-x64','qualifiedFactPath':str(I.FACT),'qualifiedFactSha256':I.FACT_SHA,'profileSha256':I.digest(profile),'controllerSha256':I.digest(controller),'ownCapsEvidenceSha256':I.digest(cp),'sourcePinTableSha256':hashlib.sha256(I.canonical(I.read(pins)['sourcePins'])).hexdigest()})
 ctx={'projectId':'06','repository':I.REPOSITORY,'checkout':str(root),'controller':str(controller),'contract':str(contract),'profile':str(profile),'sourcePins':str(pins),'admission':str(ap),'capsEvidence':str(cp),'expectedSourceCommit':s['commit'],'expectedSourceTree':s['tree'],'rowStartedMonotonicNs':s['startNs'],'deadlineMonotonicNs':s['endNs'],'supervisorPID':s['supervisorPID'],'supervisorStartIdentity':s['supervisorStartIdentity']}
 facade=I.load(root,'local_sdk11_input',I.FACADE_SHA);sdk=Path(I.read(I.FACT)['SDKPath']);receipt=facade.inspect_sdk('win-x64',sdk,ctx);I.write(out/'current-sdk-input.json',receipt);return sdk/'dotnet.exe'

def sdk_pool_postcondition(root,sdk,rid):
 # Recheck read-only reuse after the actual phase; no qualification target replay.
 f=I.load(root,'local_sdk11_input',I.FACADE_SHA);name,expected=f.CATALOGS[rid];catalog=root/'tools'/name;need(I.digest(catalog)==expected,'UNCHANGED_QUALIFIED_MEMBER_CATALOG');members=f.C._read(catalog)['members']
 if rid=='linux-x64':f.C._load('materialize_qualification_linux',f.C.PINS['materializerSha256']).verify_physical(sdk,members)
 else:f.C._load('qualification_input_guard',f.C.PINS['guardSha256']).verify_tree(sdk,members,rid,full=True)
 return {'state':'EXACT_SHARED_SDK_POOL_BYTES_UNCHANGED_AFTER_PHASE','rid':rid,'catalogSha256':expected,'qualificationCommandsReplayed':0,'SDK_READY':False,'scope':'Postcondition after actual SDK commands, not a repeated qualification or product admission.'}

def graph(root,admitted):
 allowed={(x['id'].lower(),x['version']):x['normalizedContentHash'] for x in admitted['packages']};result=[]
 for project in PROJECTS:
  path=root/Path(project).parent/'packages.lock.json';v=I.read(path);deps=v.get('dependencies',{});need(v.get('version')==1 and set(deps)=={'net11.0','net11.0/linux-x64','net11.0/win-x64'},'ACTUAL_NET11_BOTH_RID_LOCK_TARGETS')
  for target,rows in deps.items():
   for name,row in rows.items():
    if row.get('type')=='Project':continue
    key=(name.lower(),row.get('resolved'));need(key in allowed and row.get('contentHash')==allowed[key],'ACTUAL_GRAPH_UNADMITTED_PACKAGE_OR_HASH')
  result.append({'project':project,'lockSha256':I.digest(path),'targets':list(deps),'packagesByTarget':{k:len(v) for k,v in deps.items()}})
 return result

def unit_count(path):
 tree=ET.parse(path);assemblies=[n for n in tree.iter('assembly')];need(assemblies and sum(int(n.get('total','0')) for n in assemblies)==50 and sum(int(n.get('failed','0'))+int(n.get('errors','0'))+int(n.get('skipped','0')) for n in assemblies)==0,'ORIGINAL41_PLUS9_ALL_PASS')

def post_verify(root,out,commit,dotnet,config,cache,run,rid='win-x64',regressions=True):
 # Original verify tools/oracles, under this same own Job and original phase clock.
 py=lambda name,*args:[sys.executable,'-B',str(root/'tools'/name),*map(str,args)]
 if regressions:
  run(py('test_receipt_oracle.py','--out',out/'receipt-oracle-normal'),extra={'PYTHONOPTIMIZE':'0'})
  run(py('test_receipt_oracle.py','--out',out/'receipt-oracle-optimized'),extra={'PYTHONOPTIMIZE':'1'})
 need(rid in ('win-x64','linux-x64'),'FIXED_NATIVE_PACKAGE_RID')
 run(py('package.py','--rid',rid,'--commit',commit,'--work',out/'build','--out',out/'delivery','--dotnet',dotnet,'--restore-config',config,'--packages',cache/'packages'))
 if regressions:run(py('test_notices.py','--out',out/'notices-tests'));run(py('test_verifier.py','--out',out/'verifier-tests'))
 run(py('audit_dependencies.py','--dotnet',dotnet,'--out',out/'dependency-advisories.json'))
 archives=list((out/'delivery').iterdir());need(len(archives)==1 and archives[0].is_file() and archives[0].name.endswith('.zip' if rid=='win-x64' else '.tar.gz'),'ONE_NATIVE_PLATFORM_ARCHIVE')
 run(py('extract_package.py','--archive',archives[0],'--out',out/'extracted with spaces'))
 folders=list((out/'extracted with spaces').iterdir());need(len(folders)==1 and folders[0].is_dir(),'ONE_NATIVE_PACKAGE_ROOT');package=folders[0]
 run(py('check_package.py','--package',package,'--commit',commit,'--out',out/'package-checks.json'))
 rec=run([str(dotnet),'nuget','locals','global-packages','--list']);location=Path(rec['evidence'])/'stdout.log';text=location.read_text(encoding='utf-8-sig').strip();need(text.startswith('global-packages: ') and Path(text[len('global-packages: '):].strip()).resolve()==(cache/'packages').resolve(),'ACTUAL_OWN_NUGET_ARCHIVES')
 run(py('check_sbom_archives.py','--package',package,'--nuget-root',cache/'packages','--out',out/'sbom-archive-checks.json'))
 if regressions:run(py('test_sbom_archives.py','--out',out/'sbom-regressions'))
 return {'archive':str(archives[0]),'sha256':I.digest(archives[0]),'package':str(package),'rid':rid,'gate':'ORIGINAL_NATIVE_PACKAGE_NOTICES_ADVISORY_SBOM_VERIFIERS_PASS','runtimeAcceptance':False}

def worker(root,controller,path):
 need(os.name=='nt','STAGE_WINDOWS_ONLY');s=I.read(path);validate_spec(s,time.monotonic_ns());need(Path(s['checkout']).resolve()==root.resolve() and s['controllerSha256']==I.digest(controller),'STAGE_EXACT_SOURCE')
 out=path.parent;need(out.parent==root.parents[1]/'state/execution-evidence/net11-local-build06' and str(out)==s['receiptDirectory'],'OWN_STAGE_DIRECTORY');lease(s);j=I.load(root,'windows_qualification_job_local',I.HELPER_SHA)
 dotnet=current_input(root,controller,out,s,j);need(I.digest(root/MANIFEST)==s['inputAdmissionSha256'],'STAGE_ADMISSION_SOURCE_BYTES');v=admission(root,int(time.time()));config=prepare_feed(root,out,v)
 cache=out/'cache';cache.mkdir();env=windows_base_environment()
 for key,name in [('DOTNET_CLI_HOME','home'),('NUGET_PACKAGES','packages'),('NUGET_HTTP_CACHE_PATH','http'),('NUGET_PLUGINS_CACHE_PATH','plugins'),('TEMP','tmp'),('TMP','tmp')]:
  p=cache/name;p.mkdir(exist_ok=True);env[key]=str(p)
 env.update(PATH=str(dotnet.parent)+';C:/Program Files/Git/cmd;C:/Windows/System32/OpenSSH;C:/Windows/System32;C:/Windows',DOTNET_ROOT=str(dotnet.parent),DOTNET_MULTILEVEL_LOOKUP='0',DOTNET_CLI_TELEMETRY_OPTOUT='1',DOTNET_GENERATE_ASPNET_CERTIFICATE='false',DOTNET_CLI_WORKLOAD_UPDATE_NOTIFY_DISABLE='true',MSBuildEnableWorkloadResolver='false',DOTNET_CLI_USE_MSBUILD_SERVER='0',MSBUILDDISABLENODEREUSE='1',DOTNET_PROCESSOR_COUNT='1',DisableTransitiveFrameworkReferenceDownloads='true',PYTHONDONTWRITEBYTECODE='1')
 from bounded_fixture import workspace_limit
 commands=plan(s['stage'],dotnet,config,cache/'packages',out/'unit.xml');records=[]
 def run(argv,extra=None):
  lease(s);workspace_limit([out,root/'artifacts',root/'src',root/'tests']);need(time.monotonic_ns()<s['endNs']-30*10**9,'ORIGINAL_STAGE_CLEANUP_RESERVE')
  deadline=min(j.tick()+300000,j.tick()+(s['endNs']-time.monotonic_ns())//1000000-30000);folder=out/('command-'+str(len(records)+1).zfill(2));local=dict(env);local.update(extra or {})
  rec=j.run_job(argv,root,local,deadline,folder,inherited_job_name=s['jobName']);rec['evidence']=str(folder);records.append(rec)
  workspace_limit([out,root/'artifacts',root/'src',root/'tests']);return rec
 for i,argv in enumerate(commands,1):
  run(argv)
  if s['stage']=='verify' and i==3:graph(root,v)
 locks=graph(root,v);package=None;reused=None
 if s['stage']=='verify':
  unit_count(out/'unit.xml');package=post_verify(root,out,s['commit'],dotnet,config,cache,run)
 elif s['stage']=='package':
  reused=prior_windows_verification(root);package=post_verify(root,out,s['commit'],dotnet,config,cache,run,regressions=False)
 I.write(out/'sdk-pool-postcondition.json',sdk_pool_postcondition(root,dotnet.parent,'win-x64'));j.current_witness(s['jobName'])
 admission(root,int(time.time()));lease(s);I.write(out/'worker-result.json',{'state':'OWN06_LOCAL_'+s['stage'].upper()+'_COMMANDS_PASSED','stage':s['stage'],'sourceCommit':s['commit'],'sourceTree':s['tree'],'SDKExecutions':3 if s['stage']=='locks' else 6 if s['stage']=='package' else 10,'reusedVerification':reused,'commandGroups':len(records),'nativeWindowsPackage':package,'actualLocks':locks,'inputAdmissionSha256':s['inputAdmissionSha256'],'productAdmission':False,'scope':'Own Windows lock/build/unit/package/notices/current-advisory/SBOM tools only. Signed release, original nativeLinux/packaged16/SQL/runtime-oracles/five resource profiles and direct public delivery remain separately required.'})

def main(root,controller,argv):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--local-windows-stage',choices=tuple(BUDGETS));p.add_argument('--local-build-worker',type=Path);p.add_argument('--expected-commit');a=p.parse_args(argv);root=Path(root);controller=Path(controller).resolve()
 if a.local_build_worker:need(a.local_windows_stage is None and a.expected_commit is None,'BUILD_WORKER_ARGS');return worker(root,controller,a.local_build_worker)
 need(a.local_windows_stage in BUDGETS and a.expected_commit and os.name=='nt','FINITE_LOCAL_WINDOWS_BUILD_ENTRY');need(not any(os.environ.get(k) for k in ('GITHUB_ACTIONS','GITHUB_RUN_ID','RUNNER_ENVIRONMENT')),'NO_CI_IMPERSONATION')
 def git(*args):return subprocess.check_output(['C:/Program Files/Git/cmd/git.exe','-C',str(root),*args],timeout=10,creationflags=0x08000000).decode().strip()
 head=git('rev-parse','HEAD');tree=git('rev-parse','HEAD^{tree}');need(head==a.expected_commit and not git('status','--porcelain=v1','--untracked-files=all'),'CLEAN_EXPECTED_LOCAL_STAGE_SOURCE');admission(root,int(time.time()))
 if a.local_windows_stage=='package':prior_windows_verification(root)
 need(I.digest(I.FACT)==I.FACT_SHA and sys.version_info[:3]==(3,12,10) and I.digest(sys.executable)==I.read(I.FACT)['bootstrap']['pythonExeSha256'],'QUALIFIED_EXISTING_STAGE_BOOTSTRAP')
 need(I.digest(I.LEASE.with_name('LEASE-PROTOCOL.json'))==I.PROTOCOL_SHA,'CANONICAL_STAGE_PROTOCOL');j=I.load(root,'windows_qualification_job_local',I.HELPER_SHA)
 base=root.parents[1]/'state/execution-evidence/net11-local-build06';I.ordinary(base);base.mkdir(exist_ok=True);out=base/(a.local_windows_stage+'-'+secrets.token_hex(12));out.mkdir();identity=j._start_identity(os.getpid());token=secrets.token_hex(32);budget=seconds(a.local_windows_stage)
 holder={'projectId':'06','randomToken':token,'ownerOS':'Windows','ownerPID':os.getpid(),'ownerProcessStartIdentity':identity,'phase':'LOCAL_WINDOWS_'+a.local_windows_stage.upper(),'startedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'receiptDirectory':str(out),'timeoutSeconds':budget,'sourceCommit':head}
 try:I.write(I.LEASE,holder)
 except FileExistsError:I.write(out/'receipt.json',{'state':'BUSY_NOT_CLAIMED','SDKExecutions':0});return 20
 start=time.monotonic_ns();tick=j.tick();end=start+budget*10**9;result={'state':'HOLD','sourceCommit':head,'sourceTree':tree,'Actions':0,'productAdmission':False,'released':False};record={}
 try:
  spec=out/'private-spec.json';value={'purpose':'OWN06_LOCAL_WINDOWS_LOCK_BUILD','stage':a.local_windows_stage,'projectId':'06','repository':I.REPOSITORY,'checkout':str(root),'commit':head,'tree':tree,'controllerSha256':I.digest(controller),'helperSha256':I.HELPER_SHA,'facadeSha256':I.FACADE_SHA,'startNs':start,'endNs':end,'supervisorPID':os.getpid(),'supervisorStartIdentity':identity,'receiptDirectory':str(out),'leaseToken':token,'leaseSHA256':I.digest(I.LEASE),'inputAdmissionSha256':I.digest(root/MANIFEST)}
  env=windows_base_environment();env.update(PATH='C:/Windows/System32;C:/Windows',PYTHONDONTWRITEBYTECODE='1')
  record=j.run_job([sys.executable,'-I','-S','-B',str(controller),'--local-build-worker',str(spec)],root,env,tick+(budget-30)*1000,out/'job',job_name='Local\\ownership06-net11-build-'+secrets.token_hex(12),ready_spec={'path':spec,'value':value},local_console_mode='DETACHED_LOCAL_CONSOLE_FREE_V1')
  value=I.read(out/'worker-result.json');need(value['state']=='OWN06_LOCAL_'+a.local_windows_stage.upper()+'_COMMANDS_PASSED' and value['sourceCommit']==head,'ACTUAL_OWN_STAGE_RESULT');result.update(value)
 except Exception as exc:
  result.update(errorType=type(exc).__name__,error=str(exc)[:300])
  if (out/'job/process.json').is_file():record=I.read(out/'job/process.json')
 finally:
  result['process']=record;I.write(out/'outcome-before-release.json',result)
  try:
   if I.release_allowed(holder,I.read(I.LEASE),j._start_identity(os.getpid()),record):I.LEASE.unlink();result['released']=True
   else:result['releaseError']='EXACT_OWNER_OR_POSITIVE_TERMINAL_MISSING'
  except Exception as exc:result['releaseError']=type(exc).__name__+':'+str(exc)[:150]
  result['elapsedSeconds']=(time.monotonic_ns()-start)/1e9;result['wholePhaseBudgetMet']=result['elapsedSeconds']<=budget;I.write(out/'receipt.json',result)
 print(json.dumps({'state':result['state'],'released':result['released'],'receipt':str(out/'receipt.json'),'Actions':0}));need(result['state']!='HOLD' and result['released'] and result['wholePhaseBudgetMet'],'LOCAL_STAGE_HOLD');return 0
