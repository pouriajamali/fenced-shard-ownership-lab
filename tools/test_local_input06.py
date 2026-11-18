"""Own06 delta checks only; no SDK, OS Job, lane or shared-suite execution."""
import ast,copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import local_input06 as L

def sample():
 return {'purpose':'OWN06_P0_WINDOWS_P3_INPUT_ONLY','projectId':'06','repository':L.REPOSITORY,'startNs':100,'endNs':60000000100,'workerPID':2,'workerStart':'FILETIME:20','supervisorPID':1,'supervisorStartIdentity':'FILETIME:10','helperSha256':L.HELPER_SHA,'facadeSha256':L.FACADE_SHA,'beforeResume':{'membership':True,'retainedCreationHandles':True}}

class InputDelta(unittest.TestCase):
 def test_original_clock_cannot_reset_or_use_boolean(self):
  L.validate_spec(sample(),200)
  for key,value in [('startNs',True),('endNs',60000000200),('endNs',200),('startNs',201)]:
   s=sample();s[key]=value
   with self.assertRaises(RuntimeError):L.validate_spec(s,200)
 def test_foreign_scope_or_source_pin_is_denied(self):
  for key,value in [('projectId','04'),('repository','pouriajamali/data-admission-gate'),('purpose','P3_RUN_SDK'),('helperSha256','0'*64),('facadeSha256','0'*64)]:
   s=sample();s[key]=value
   with self.assertRaises(RuntimeError):L.validate_spec(s,200)
 def test_original_held_identity_required(self):
  for key,value in [('workerPID',True),('workerStart','20'),('supervisorPID',2),('supervisorStartIdentity','10')]:
   s=sample();s[key]=value
   with self.assertRaises(RuntimeError):L.validate_spec(s,200)
  s=sample();s['beforeResume']['retainedCreationHandles']=False
  with self.assertRaises(RuntimeError):L.validate_spec(s,200)
 def test_release_requires_exact_holder_and_integer_terminal(self):
  h={'ownerProcessStartIdentity':'FILETIME:10','randomToken':'own','ownerPID':1};r={'actualCap':{'kind':'actual-Windows-Job','activeProcessesAtTeardown':0,'memoryMax':4294967296,'activeProcessMax':64,'effectiveCpuCores':2,'retainedCreationHandles':True,'childMembershipBeforeResume':True},'childBeforeExec':{'pid':2,'processStartIdentity':'FILETIME:20','membershipBeforeResume':True}}
  self.assertTrue(L.release_allowed(h,dict(h),'FILETIME:10',r))
  self.assertFalse(L.release_allowed(h,{**h,'randomToken':'other'},'FILETIME:10',r));self.assertFalse(L.release_allowed(h,h,'FILETIME:11',r))
  for value in [False,True,1,None]:
   changed=copy.deepcopy(r);changed['actualCap']['activeProcessesAtTeardown']=value;self.assertFalse(L.release_allowed(h,h,'FILETIME:10',changed))
  self.assertFalse(L.release_allowed(h,h,'FILETIME:10',{}))
  for key,value in [('retainedCreationHandles',False),('childMembershipBeforeResume',False),('memoryMax',8589934592),('activeProcessMax',128),('effectiveCpuCores',3)]:
   changed=copy.deepcopy(r);changed['actualCap'][key]=value;self.assertFalse(L.release_allowed(h,h,'FILETIME:10',changed))
 def test_live_lease_owner_source_and_phase_cannot_be_borrowed(self):
  h={'projectId':'06','randomToken':'own','ownerPID':1,'ownerProcessStartIdentity':'FILETIME:10','phase':'P0_WINDOWS_P3_SDK_INPUT_ONLY','sourceCommit':'own-head','receiptDirectory':'own-out'}
  v={'leaseToken':'own','supervisorPID':1,'supervisorStartIdentity':'FILETIME:10','commit':'own-head','receiptDirectory':'own-out'}
  L.validate_lease(h,v)
  for key,value in [('projectId','04'),('randomToken','foreign'),('ownerPID',3),('ownerProcessStartIdentity','FILETIME:11'),('phase','OTHER'),('sourceCommit','other-head'),('receiptDirectory','other-out')]:
   with self.assertRaises(RuntimeError):L.validate_lease({**h,key:value},v)
 def test_no_sdk_target_or_generic_command_factory(self):
  text=Path(L.__file__).read_text();tree=ast.parse(text)
  calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and isinstance(n.func.value,ast.Name) and n.func.value.id=='subprocess']
  self.assertEqual([x.func.attr for x in calls],['check_output']);self.assertNotIn('dotnet.exe',text);self.assertIn("facade.inspect_sdk('win-x64'",text)

if __name__=='__main__':unittest.main()
