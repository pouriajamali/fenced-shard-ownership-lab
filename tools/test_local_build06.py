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
  for row in contract['packages']:v['packages'].append({**row,'normalizedContentHash':base64.b64encode(bytes(64)).decode(),'cryptographicAdmission':True,'cmsPublisherVerified':True,'RFC3161Verified':True,'revocationCoverageVerified':True,'rawSha512':'0'*128,'verificationReceiptSha256':'0'*64,'bytes':1,'notices':[{'path':'missing','sha256':'0'*64}],'producerProjectId':'04'})
  return v
 def check_denied(self,edit,error):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);v=self.fixture(root);edit(v);(root/B.MANIFEST).write_text(json.dumps(v))
   with self.assertRaisesRegex(RuntimeError,error):B.admission(root,1000)
 def test_expired_or_too_short_or_extended_proof_window_denied(self):
  for key,value in [('expiresAtUnix',1000),('expiresAtUnix',1299),('expiresAtUnix',90000),('observedAtUnix',1001),('observedAtUnix',True)]:
   self.check_denied(lambda v:v['advisory'].__setitem__(key,value),'FRESHNESS')
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

if __name__=='__main__':unittest.main()
