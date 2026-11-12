"""M1 coallocation controls: actual Windows budget and no foreign/native unit stop."""
from pathlib import Path
import argparse,copy,json,os,subprocess,sys,unittest
from unittest.mock import patch
import profile_limits as limits
import wsl_host_entry as entry
UNIT='ownership06-synthetic-profile-00000001';TOKEN='a'*64;WORK=None
class Controls(unittest.TestCase):
 def setUp(self):self.root=WORK/self._testMethodName;self.root.mkdir()
 def data(self,stop=True):
  out=self.root/'host';out.mkdir();terminal=self.root/'terminal.json';terminal.write_text(json.dumps(dict(unit=UNIT,token=TOKEN,terminal=False,populated=None)));group=Path('/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/app.slice')/(UNIT+'.service');record=dict(unit=UNIT,token=TOKEN,group=str(group),invocationId='own-invocation');(out/'unit.json').write_text(json.dumps(record));argv=['wsl_host_entry.py','--unit',UNIT,'--token',TOKEN,'--terminal',str(terminal),'--fixtures',str(self.root),'--out',str(out)]
  if stop:argv+=['--stop']
  return out,terminal,group,record,argv
 def test_actual_windows_lower_budget(self):
  proof=limits.windows();self.assertLessEqual(proof['memoryMax'],1073741824);self.assertLessEqual(proof['effectiveCpuCores'],1);self.assertLessEqual(proof['activeProcessMax'],16);self.assertTrue(proof['memberBeforeServiceOrClientChildren']);(self.root/'actual-job.json').write_text(json.dumps(proof,indent=2)+'\n')
 def test_controller_unit_mismatch_before_work_or_child(self):
  import integration
  fixtures=Path(__file__).resolve().parents[2]/'state/etcd-amendment-01/serving-bundle-01'
  argv=['integration.py','--fixtures',str(fixtures),'--cli',str(self.root/'never-run.exe'),'--out',str(self.root/'never-created'),'--service-unit',UNIT]
  with patch.object(sys,'argv',argv),patch.dict(os.environ,{'OWNERSHIP_SERVICE_UNIT':'ownership06-different-controller0001'}),patch.object(limits,'windows',return_value={'syntheticBudgetSeam':True}),patch.object(integration.subprocess,'Popen',side_effect=AssertionError('CHILD_MUST_NOT_START')) as child:
   with self.assertRaisesRegex(ValueError,'Own controller service unit mismatch'):integration.main()
   child.assert_not_called()
  self.assertFalse((self.root/'never-created').exists())
 def test_linux_budget_requires_exact_partition_and_unit(self):
  caps=dict(kernel={'memory.max':'3221225472','memory.swap.max':'0','pids.max':'48','cpu.max':'100000 100000'},group='/sys/fs/cgroup/user.slice/own/'+UNIT+'.service');self.assertEqual(limits.guest(caps,UNIT),caps)
  for key,value in [('memory.max','4294967296'),('pids.max','64'),('cpu.max','200000 100000'),('memory.swap.max','max')]:
   bad=copy.deepcopy(caps);bad['kernel'][key]=value
   with self.assertRaisesRegex(ValueError,'COALLOCATED_GUEST_ACTUAL_BUDGET'):limits.guest(bad,UNIT)
  with self.assertRaisesRegex(ValueError,'COALLOCATED_GUEST_ACTUAL_BUDGET'):limits.guest(dict(caps,group='/foreign/another.service'),UNIT)
 def test_foreign_unit_record_before_any_stop(self):
  out,terminal,group,record,argv=self.data();record['token']='b'*64;(out/'unit.json').write_text(json.dumps(record))
  with patch.object(sys,'argv',argv),patch.object(entry,'environment',return_value={}),patch.object(entry,'populated',return_value=1),patch.object(entry,'group_for',return_value=group),patch.object(entry.subprocess,'run',side_effect=AssertionError('FOREIGN_STOP_MUST_NOT_START')) as child:
   with self.assertRaisesRegex(ValueError,'EXACT_OWN_INVOCATION_RECORD'):entry.main()
   child.assert_not_called()
 def test_changed_invocation_never_stopped(self):
  out,terminal,group,record,argv=self.data();seen=[]
  def query(args,**kwargs):seen.append(args);return subprocess.CompletedProcess(args,0,stdout='foreign-invocation\n')
  with patch.object(sys,'argv',argv),patch.object(entry,'environment',return_value={}),patch.object(entry,'populated',return_value=1),patch.object(entry,'group_for',return_value=group),patch.object(entry,'ready',return_value=True),patch.object(entry.subprocess,'run',side_effect=query):
   with self.assertRaisesRegex(ValueError,'OWN_ACTIVE_UNIT_INCARCATION'):entry.main()
  self.assertEqual(len(seen),1);self.assertIn('show',seen[0]);self.assertNotIn('stop',seen[0]);self.assertFalse(json.loads(terminal.read_bytes())['terminal'])
 def test_nonterminal_group_cannot_claim_pass(self):
  out,terminal,group,record,argv=self.data(stop=False);(out/'unit.json').unlink();active=[False];original=Path.read_text
  def text(path,*args,**kwargs):return 'synthetic-boot' if path.as_posix()=='/proc/sys/kernel/random/boot_id' else original(path,*args,**kwargs)
  def fake(args,**kwargs):active[0]=True;return subprocess.CompletedProcess(args,0)
  with patch.object(sys,'argv',argv),patch.object(entry,'environment',return_value={}),patch.object(entry,'populated',side_effect=lambda unit:1 if active[0] else 0),patch.object(entry,'ready',return_value=True),patch.object(entry.subprocess,'run',side_effect=fake),patch.object(Path,'read_text',text):
   with self.assertRaisesRegex(ValueError,'NATIVE_GROUP_TERMINAL_REQUIRED'):entry.main()
  r=json.loads(terminal.read_bytes());self.assertFalse(r['terminal']);self.assertEqual(r['populated'],1)
 def test_unready_bus_proves_no_target_started(self):
  out,terminal,group,record,argv=self.data(stop=False);(out/'unit.json').unlink();original=Path.read_text
  def text(path,*args,**kwargs):return 'synthetic-boot' if path.as_posix()=='/proc/sys/kernel/random/boot_id' else original(path,*args,**kwargs)
  with patch.object(sys,'argv',argv),patch.object(entry,'environment',return_value={}),patch.object(entry,'populated',return_value=0),patch.object(entry,'ready',return_value=False),patch.object(entry.subprocess,'run',side_effect=AssertionError('TARGET_MUST_NOT_START')) as child,patch.object(Path,'read_text',text):
   with self.assertRaises(SystemExit) as failure:entry.main()
   self.assertEqual(failure.exception.code,125);child.assert_not_called()
  r=json.loads(terminal.read_bytes());self.assertTrue(r['terminal']);self.assertEqual(r['populated'],0);self.assertFalse(r['targetStarted'])
def main():
 global WORK
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--opt',type=int,required=True);p.add_argument('--only',choices=['test_controller_unit_mismatch_before_work_or_child']);a=p.parse_args()
 if sys.flags.optimize!=a.opt:raise ValueError('ACTUAL_OPTIMIZATION')
 WORK=a.out.absolute();WORK.mkdir(exist_ok=False);suite=unittest.TestSuite([Controls(a.only)]) if a.only else unittest.defaultTestLoader.loadTestsFromTestCase(Controls);result=unittest.TextTestRunner(verbosity=1).run(suite);r=dict(status='PASS' if result.wasSuccessful() and not result.skipped else 'FAIL',tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),skips=len(result.skipped),optimization=sys.flags.optimize,realWindowsBudgetQueried=True,linuxUnitOrFixtureOrSdkStarted=False,scope='Actual1GiB/1CPU/16-process Windows readback plus synthetic strict3GiB/1CPU/48-task/own-invocation/terminal controls. Actual coupled profile remains separate.')
 (WORK/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(0 if r['status']=='PASS' else 1)
if __name__=='__main__':main()
