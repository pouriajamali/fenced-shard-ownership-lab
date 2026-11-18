"""Only new local build boundary checks; SDK0, no Job or canonical lease access."""
import base64,copy,json,sys,tempfile,time,unittest,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import local_build06 as B

def spec(stage='locks'):
 return {'stage':stage,'purpose':'OWN06_LOCAL_WINDOWS_LOCK_BUILD','projectId':'06','repository':B.I.REPOSITORY,'startNs':100,'endNs':100+B.seconds(stage)*10**9,'workerPID':2,'workerStart':'FILETIME:2','supervisorPID':1,'supervisorStartIdentity':'FILETIME:1','helperSha256':B.I.HELPER_SHA,'facadeSha256':B.I.FACADE_SHA,'beforeResume':{'membership':True,'retainedCreationHandles':True}}

class LocalBuildBoundary(unittest.TestCase):
 def test_only_original_finite_stages_and_clocks(self):
  for stage,limit in [('locks',600),('verify',900)]:
   self.assertEqual(B.seconds(stage),limit);B.validate_spec(spec(stage),200)
   v=spec(stage);v['endNs']+=1
   with self.assertRaises(RuntimeError):B.validate_spec(v,200)
  for stage in ['R06','runtime','shell','prepare',None]:
   with self.assertRaises(RuntimeError):B.seconds(stage)
 def test_boolean_foreign_and_unheld_spec_denied(self):
  for k,v in [('startNs',True),('workerPID',True),('projectId','04'),('supervisorPID',2),('workerStart','2'),('supervisorStartIdentity','1'),('helperSha256','0'*64)]:
   s=spec();s[k]=v
   with self.assertRaises(RuntimeError):B.validate_spec(s,200)
  s=spec();s['beforeResume']['retainedCreationHandles']=False
  with self.assertRaises(RuntimeError):B.validate_spec(s,200)
 def test_missing_actual_input_manifest_is_closed_before_execution(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(RuntimeError,'REAL_INPUT_ADMISSION_NOT_YET_DELIVERED'):B.admission(Path(d),1000)
 def test_lock_transition_is_three_fixed_generations_only(self):
  rows=B.plan('locks',Path('sdk/dotnet.exe'),Path('own/config'),Path('own/packages'),Path('unit.xml'))
  self.assertEqual([r[2] for r in rows],list(B.PROJECTS));self.assertEqual(len(rows),3)
  self.assertTrue(all('--force-evaluate' in r and '--use-lock-file' in r and '--configfile' in r and '--packages' in r for r in rows))
  self.assertTrue(all('NuGetAudit=false' not in ' '.join(r) and '--ignore-failed-sources' not in r for r in rows))
 def test_verify_cannot_generate_or_unlock_locks(self):
  rows=B.plan('verify','sdk/dotnet.exe','own/config','own/packages','unit.xml');self.assertEqual(len(rows),5)
  self.assertTrue(all('--locked-mode' in r for r in rows[:3]));self.assertTrue(all('--force-evaluate' not in r and '--use-lock-file' not in r for r in rows))
  self.assertTrue(all('--no-restore' in r for r in rows[3:]))
 def test_full_50_tests_required_without_skips_or_errors(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'u.xml'
   for total,failed,errors,skipped,accept in [(50,0,0,0,True),(41,0,0,0,False),(50,1,0,0,False),(50,0,1,0,False),(50,0,0,1,False)]:
    p.write_text(f'<assemblies><assembly total="{total}" failed="{failed}" errors="{errors}" skipped="{skipped}"/></assemblies>')
    if accept:B.unit_count(p)
    else:
     with self.assertRaises(RuntimeError):B.unit_count(p)
 def test_unadmitted_new_graph_package_or_hash_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);ad={'packages':[{'id':'Npgsql','version':'10.0.3','normalizedContentHash':'exact'}]}
   for project in B.PROJECTS:
    p=root/Path(project).parent/'packages.lock.json';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps({'version':1,'dependencies':{'net11.0':{'Npgsql':{'type':'Direct','resolved':'10.0.3','contentHash':'exact'}},'net11.0/linux-x64':{},'net11.0/win-x64':{}}}))
   self.assertEqual(len(B.graph(root,ad)),3)
   p=root/Path(B.PROJECTS[0]).parent/'packages.lock.json';v=json.loads(p.read_text());v['dependencies']['net11.0']['Npgsql']['contentHash']='wrong';p.write_text(json.dumps(v))
   with self.assertRaisesRegex(RuntimeError,'UNADMITTED_PACKAGE_OR_HASH'):B.graph(root,ad)
 def test_net10_locks_cannot_be_relabelled_as_accepted(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/Path(B.PROJECTS[0]).parent/'packages.lock.json';p.parent.mkdir(parents=True);p.write_text(json.dumps({'version':1,'dependencies':{'net10.0':{}}}))
   with self.assertRaisesRegex(RuntimeError,'ACTUAL_NET11_BOTH_RID'):B.graph(root,{'packages':[]})

class AdmissionBoundary(unittest.TestCase):
 def fixture(self,root):
  (root/'tools').mkdir();contract={'packages':[{'id':'P'+str(i),'version':'1.0.0','normalizedContentHash':None} for i in range(38)]};(root/'tools/local06-input-contract.json').write_text(json.dumps(contract))
  v={'schema':'own06-verified-product-inputs/v1','state':'PRODUCER04_PROOFS_REVIEWED_OWN06_INPUTS_ADMITTED','projectId':'06','repository':B.I.REPOSITORY,'inputContractSha256':B.I.digest(root/'tools/local06-input-contract.json'),'advisory':{'observedAtUnix':900,'expiresAtUnix':2000,'receiptPath':str(root/'missing-advisory'),'receiptSha256':'0'*64},'packages':[]}
  v['certificateWindow']={'nativeVerifiedAtUnix':900,'expiresAtUnix':2000,'inputCRLs':[{'thisUpdate':800,'nextUpdate':3000}],'receiptPath':str(root/'missing-pki'),'receiptSha256':'0'*64}
  for row in contract['packages']:v['packages'].append({**row,'normalizedContentHash':base64.b64encode(bytes(64)).decode(),'cryptographicAdmission':True,'cmsPublisherVerified':True,'RFC3161Verified':True,'revocationCoverageVerified':True,'rawSha512':'0'*128,'verificationReceiptSha256':'0'*64,'bytes':1,'notices':[{'path':'missing','sha256':'0'*64}],'producerProjectId':'04'})
  return v
 def check_denied(self,edit,error):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);v=self.fixture(root);edit(v);(root/B.MANIFEST).write_text(json.dumps(v))
   with self.assertRaisesRegex(RuntimeError,error):B.admission(root,1000)
 def test_expired_or_too_short_or_extended_proof_window_denied(self):
  for key,value in [('expiresAtUnix',1000),('expiresAtUnix',1299),('expiresAtUnix',90000),('observedAtUnix',1001),('observedAtUnix',True)]:
   self.check_denied(lambda v:v['advisory'].__setitem__(key,value),'FRESHNESS')
 def test_expired_or_extended_certificate_and_crl_window_denied(self):
  for key,value in [('expiresAtUnix',1000),('expiresAtUnix',1299),('expiresAtUnix',90000),('nativeVerifiedAtUnix',1001)]:
   self.check_denied(lambda v:v['certificateWindow'].__setitem__(key,value),'CERTIFICATE_PROOF_WINDOW')
  for key,value in [('thisUpdate',1001),('nextUpdate',999),('nextUpdate',True),('nextUpdate',1999)]:
   self.check_denied(lambda v:v['certificateWindow']['inputCRLs'][0].__setitem__(key,value),'EXACT_CRL_TIME_WINDOW')
 def test_each_crypto_gate_required_as_real_boolean_true(self):
  for field in ['cryptographicAdmission','cmsPublisherVerified','RFC3161Verified','revocationCoverageVerified']:
   self.check_denied(lambda v:v['packages'][0].__setitem__(field,False),'ACTUAL_CRYPTO')
 def test_foreign_duplicate_or_unhashed_input_is_denied(self):
  self.check_denied(lambda v:v['packages'][0].__setitem__('id','foreign'),'EXACT_34')
  self.check_denied(lambda v:v['packages'].__setitem__(0,copy.deepcopy(v['packages'][1])),'EXACT_34')
  self.check_denied(lambda v:v['packages'][0].__setitem__('verificationReceiptSha256',''),'INPUT_HASH')
 def test_true_flags_never_replace_retained_proof_bytes(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);v=self.fixture(root);(root/B.MANIFEST).write_text(json.dumps(v));accepted=B.admission(root,1000);out=root/'out';out.mkdir()
   with self.assertRaisesRegex(RuntimeError,'RETAINED_PROOF_BYTES'):B.prepare_feed(root,out,accepted)


class ProducerProofBoundary(unittest.TestCase):
 def test_actual_record_binds_both_raw_and_normalized_identities(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'proof.json';row={'id':'P','version':'1.0.0','bytes':7,'sha512':'a'*128,'normalizedNuGetContentHash':'normalized'};p.write_text(json.dumps({'packages':[row]}));x={'id':'P','version':'1.0.0','bytes':7,'rawSha512':'a'*128,'normalizedContentHash':'normalized','verificationReceiptPath':str(p),'verificationReceiptSha256':B.I.digest(p)};self.assertEqual(B.producer_record(x),row)
   for k,v in [('rawSha512','b'*128),('bytes',8),('normalizedContentHash','other')]:
    with self.assertRaisesRegex(RuntimeError,'PRODUCER_RAW_NORMALIZED_PROOF_BINDING'):B.producer_record({**x,k:v})
 def test_valid_unrelated_or_duplicate_proof_never_admits_package(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'proof.json';x={'id':'P','version':'1.0.0','verificationReceiptPath':str(p)}
   for rows in [[],[{'id':'Other','version':'1.0.0'}],[{'id':'P','version':'1.0.0'}]*2]:
    p.write_text(json.dumps({'packages':rows}));x['verificationReceiptSha256']=B.I.digest(p)
    with self.assertRaisesRegex(RuntimeError,'EXACT_PRODUCER_PACKAGE_PROOF'):B.producer_record(x)


class PackageRestoreBoundary(unittest.TestCase):
 def test_existing_restore_default_and_local_pair_required(self):
  import package as P
  self.assertEqual(P.restore_command('dotnet'),['dotnet','restore','src/Ownership.Cli/Ownership.Cli.csproj','--locked-mode'])
  with tempfile.TemporaryDirectory() as d:
   config=Path(d)/'with spaces'/'NuGet.Config';packages=Path(d)/'own packages'
   self.assertEqual(P.restore_command('sdk',config,packages)[-4:],['--configfile',str(config),'--packages',str(packages)])
   for a,b in [(config,None),(None,packages),(Path('relative'),packages),(config,Path('relative'))]:
    with self.assertRaises(ValueError):P.restore_command('sdk',a,b)
 def test_foreign_global_package_cache_blocks_final_package_gate(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);out=root/'out';out.mkdir();cache=out/'cache';calls=[]
   def run(argv,extra=None):
    calls.append(argv);folder=out/('command-'+str(len(calls)));folder.mkdir()
    if len(argv)>2 and Path(argv[2]).name=='package.py':
     (out/'delivery').mkdir();(out/'delivery'/'native.zip').write_bytes(b'unit-test-only-placeholder')
    if len(argv)>2 and Path(argv[2]).name=='extract_package.py':(out/'extracted with spaces'/'native').mkdir(parents=True)
    if 'nuget' in argv:(folder/'stdout.log').write_text('global-packages: '+str(root/'foreign-cache'))
    return {'evidence':str(folder)}
   with self.assertRaisesRegex(RuntimeError,'ACTUAL_OWN_NUGET_ARCHIVES'):B.post_verify(root,out,'source','sdk',out/'config',cache,run)
   self.assertFalse(any('check_sbom_archives.py' in ' '.join(x) for x in calls))


class LinuxBindingBoundary(unittest.TestCase):
 def test_after_claim_clock_and_unit_cannot_expand_to_runtime128(self):
  import local_linux_build06 as L
  v={'purpose':'OWN06_LOCAL_LINUX_VERIFY','projectId':'06','repository':B.I.REPOSITORY,'startNs':100,'endNs':900000000100,'supervisorPID':1,'supervisorStartIdentity':'proc-start:1','unit':'ownershiplab-ci-'+'a'*16+'-verify'};L.ledger(v,200)
  for key,value in [('startNs',True),('endNs',900000000101),('projectId','04'),('supervisorPID',True),('unit','ownershiplab-ci-'+'a'*16+'-runtime')]:
   with self.assertRaises(RuntimeError):L.ledger({**v,key:value},200)
 def test_kernel_stop_state_parses_spaces_and_parentheses_in_comm(self):
  import local_linux_build06 as L
  self.assertTrue(L.stopped('12 (worker (test)) T 1 2 3'));self.assertTrue(L.stopped('12 (worker) t 1 2 3'));self.assertFalse(L.stopped('12 (worker) S 1 2 3'))
 def test_all_actual_uid_and_gid_columns_must_be_nonroot_owner(self):
  import local_linux_build06 as L
  L.actual_nonroot_status('Uid:\t1000 1000 1000 1000\nGid:\t1000 1000 1000 1000\n'.replace('\\t','\t').replace('\\n','\n'))
  for text in ['Uid: 0 1000 1000 1000\nGid: 1000 1000 1000 1000','Uid: 1000 1000 1000 1000\nGid: 0 1000 1000 1000','Uid: 1000 1000 1000 1000']:
   with self.assertRaises(RuntimeError):L.actual_nonroot_status(text.replace('\\n','\n'))
 def test_retained_windows_input_paths_translate_without_traversal(self):
  self.assertEqual(B.retained_posix_path('C:/public/package.nupkg'),'/mnt/c/public/package.nupkg');self.assertEqual(B.retained_posix_path('E:'+chr(92)+'public'+chr(92)+'p.json'),'/mnt/e/public/p.json')
  self.assertEqual(B.retained_posix_path('/home/ubuntu/proof.json'),'/home/ubuntu/proof.json')
  for value in ['D:/public/package.nupkg','C:/public/../private']:
   with self.assertRaises(RuntimeError):B.retained_posix_path(value)


class LinuxTerminalBoundary(unittest.TestCase):
 def test_actual_absence_is_distinct_from_live_group_missing_events(self):
  import local_linux_build06 as L
  with tempfile.TemporaryDirectory() as d:
   group=Path(d)/'own.service';self.assertEqual(L.population(group),0);group.mkdir()
   with self.assertRaisesRegex(RuntimeError,'LIVE_CGROUP_WITHOUT_EVENTS'):L.population(group)
   (group/'cgroup.events').write_text('populated 1\n');self.assertEqual(L.population(group),1)
   (group/'cgroup.events').write_text('populated 0\n');self.assertEqual(L.population(group),0)
   (group/'cgroup.events').write_text('populated false\n')
   with self.assertRaisesRegex(RuntimeError,'ACTUAL_CGROUP_POPULATED_FIELD'):L.population(group)

class NativeLinuxProofBoundary(unittest.TestCase):
 def test_current_native_dependency_hash_or_soname_mismatch_blocks_sdk(self):
  import local_linux_build06 as L
  with tempfile.TemporaryDirectory() as d:
   sdk=Path(d);(sdk/'fixed.so').write_bytes(b'changed-current-library');names=['dotnet','host/fxr/11.0.0/libhostfxr.so','shared/Microsoft.NETCore.App/11.0.0/libcoreclr.so','shared/Microsoft.NETCore.App/11.0.0/libclrjit.so'];rows=[{'name':n,'status':'ObservedExistingHostDependenciesNoInventedELFSignature:'+json.dumps([{'import':'fixed.so','resolvedName':'fixed.so','sha256':'0'*64}]),'evidenceSha256':'0'*64} for n in names]
   with self.assertRaisesRegex(RuntimeError,'CURRENT_OS_DEPENDENCY_BYTES'):L.retained_dependencies(sdk,{'nativePrerequisites':rows})
   rows[0]['status']='ObservedExistingHostDependenciesNoInventedELFSignature:'+json.dumps([{'import':'../escape','resolvedName':'fixed.so','sha256':'0'*64}])
   with self.assertRaisesRegex(RuntimeError,'EXACT_QUALIFIED_SONAME_ONLY'):L.retained_dependencies(sdk,{'nativePrerequisites':rows})
 def test_linux_package_gate_cannot_accept_windows_archive(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);out=root/'out';out.mkdir();calls=[]
   def run(argv,extra=None):
    calls.append(argv)
    if len(argv)>2 and Path(argv[2]).name=='package.py':
     self.assertEqual(argv[argv.index('--rid')+1],'linux-x64');(out/'delivery').mkdir();(out/'delivery'/'wrong-win.zip').write_bytes(b'unit-test-only-placeholder')
    return {}
   with self.assertRaisesRegex(RuntimeError,'ONE_NATIVE_PLATFORM_ARCHIVE'):B.post_verify(root,out,'source','sdk',out/'config',out/'cache',run,rid='linux-x64')
   self.assertFalse(any('extract_package.py' in ' '.join(x) for x in calls))

if __name__=='__main__':unittest.main()
