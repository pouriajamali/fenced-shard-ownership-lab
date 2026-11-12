"""M1 coallocation controls: actual Windows budget and no foreign/native unit stop."""
from pathlib import Path
import argparse,copy,json,os,subprocess,sys,unittest
from unittest.mock import patch
import profile_limits as limits
import wsl_host_entry as entry
import bounded_fixture as bounds
import linux_host as host
import check_package as package_check
UNIT='ownership06-synthetic-profile-00000001';TOKEN='a'*64;WORK=None;ACTUAL=None
class Controls(unittest.TestCase):
 def setUp(self):self.root=WORK/self._testMethodName;self.root.mkdir()
 def data(self,stop=True):
  out=self.root/'cases'/'host';out.mkdir(parents=True);terminal=self.root/'terminal.json';terminal.write_text(json.dumps(dict(unit=UNIT,token=TOKEN,terminal=False,populated=None)));group=Path('/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/app.slice')/(UNIT+'.service');record=dict(unit=UNIT,token=TOKEN,group=str(group),invocationId='own-invocation');(out/'unit.json').write_text(json.dumps(record));argv=['wsl_host_entry.py','--unit',UNIT,'--token',TOKEN,'--terminal',str(terminal),'--fixtures',str(self.root),'--out',str(out)]
  if stop:argv+=['--stop']
  return out,terminal,group,record,argv
 def test_controller_terminal_sibling_layout_accepted(self):
  out,terminal,group,record,argv=self.data();original=Path.read_text
  def text(path,*args,**kwargs):return 'synthetic-boot' if path.as_posix()=='/proc/sys/kernel/random/boot_id' else original(path,*args,**kwargs)
  with patch.object(sys,'argv',argv),patch.object(entry,'environment',return_value={}),patch.object(entry,'populated',return_value=0),patch.object(entry.subprocess,'run',side_effect=AssertionError('ALREADY_TERMINAL_NO_STOP')),patch.object(Path,'read_text',text):entry.main()
  observed=json.loads(terminal.read_bytes());self.assertTrue(observed['terminal']);self.assertEqual(observed['populated'],0)
 def test_nested_or_foreign_terminal_parent_rejected(self):
  out,terminal,group,record,argv=self.data()
  for folder in [out.parent,self.root/'foreign']:
   folder.mkdir(exist_ok=True);bad=folder/'bad-terminal.json';bad.write_bytes(terminal.read_bytes());changed=list(argv);changed[changed.index('--terminal')+1]=str(bad)
   with patch.object(sys,'argv',changed),patch.object(entry.subprocess,'run',side_effect=AssertionError('NO_TARGET_OR_STOP')) as child:
    with self.assertRaisesRegex(ValueError,'OWN_TERMINAL_PATH'):entry.main()
    child.assert_not_called()
 def test_integration_nested_terminal_rejected_before_child(self):
  import integration
  fixtures=Path(__file__).resolve().parents[2]/'state/etcd-amendment-01/serving-bundle-01';out=self.root/'cases'
  argv=['integration.py','--fixtures',str(fixtures),'--cli',str(self.root/'never-run.exe'),'--out',str(out),'--service-unit',UNIT]
  with patch.object(sys,'argv',argv),patch.dict(os.environ,{'OWNERSHIP_SERVICE_UNIT':UNIT,'OWNERSHIP_PROFILE_TOKEN':TOKEN,'OWNERSHIP_NATIVE_TERMINAL':str(out/'nested-terminal.json')}),patch.object(limits,'windows',return_value={'syntheticBudgetSeam':True}),patch.object(integration.subprocess,'Popen',side_effect=AssertionError('CHILD_MUST_NOT_START')) as child:
   with self.assertRaisesRegex(ValueError,'Own native terminal containment'):integration.main()
   child.assert_not_called()
 def synthetic_kernel(self,pids='128',profile=None,membership=None):
  values={'memory.max':'4294967296','memory.swap.max':'0','pids.max':pids,'cpu.max':'200000 100000'}
  membership=membership or '/user.slice/user-1000.slice/user@1000.service/app.slice/'+UNIT+'.service'
  def text(path,*args,**kwargs):return '0::'+membership+'\n' if path.name=='cgroup' else values[path.name]
  with patch.object(sys,'platform','linux'),patch.object(bounds.os,'getuid',return_value=1000,create=True),patch.object(Path,'read_text',text):return bounds.kernel_limits(runtime_profile=profile)
 def test_amendment_finite_selector_before_limits(self):
  for value in [None,0,128,129,'128','129','0','max','','generic-default-64','native-linux-15',True,float('inf')]:
   with patch.object(limits,'kernel_limits',side_effect=AssertionError('NO_KERNEL_OR_CHILD')) as read:
    with self.assertRaisesRegex(ValueError,'FINITE_NATIVE_RUNTIME_PROFILE'):limits.native_runtime(value)
    read.assert_not_called()
 def test_amendment_literal_kernel_limits(self):
  self.assertEqual(self.synthetic_kernel('64')['kernel']['pids.max'],'64')
  for pids in ['128','129','0','max','-1','nan','inf','64 128']:
   with self.assertRaisesRegex(ValueError,'AGGREGATE_TASK_HOLD'):self.synthetic_kernel(pids)
  for pids in ['129','0','max','-1','nan','inf']:
   with self.assertRaisesRegex(ValueError,'AGGREGATE_TASK_HOLD'):self.synthetic_kernel(pids,bounds.NATIVE_RUNTIME_PROFILE)
  self.assertEqual(self.synthetic_kernel('128',bounds.NATIVE_RUNTIME_PROFILE)['kernel']['pids.max'],'128')
  with self.assertRaisesRegex(ValueError,'OWN_NATIVE_RUNTIME_GROUP'):self.synthetic_kernel('128',bounds.NATIVE_RUNTIME_PROFILE,'/foreign/unrelated.service')
  for profile in [128,'128','max',True,'native-linux-16-extra']:
   with self.assertRaisesRegex(ValueError,'FINITE_NATIVE_RUNTIME_PROFILE'):self.synthetic_kernel('128',profile)
 def test_amendment_default_ignores_environment(self):
  with patch.dict(os.environ,{'OWNERSHIP_RUNTIME_PROFILE':bounds.NATIVE_RUNTIME_PROFILE,'OWNERSHIP_PROFILE_TASKS':'128'}):
   with self.assertRaisesRegex(ValueError,'AGGREGATE_TASK_HOLD'):self.synthetic_kernel('128')
 def test_amendment_exact_native_budget(self):
  caps=self.synthetic_kernel('128',bounds.NATIVE_RUNTIME_PROFILE)
  with patch.object(sys,'platform','linux'),patch.object(limits,'kernel_limits',return_value=caps):self.assertEqual(limits.native_runtime(bounds.NATIVE_RUNTIME_PROFILE),caps)
  for name,value in [('pids.max','64'),('memory.max','3221225472'),('cpu.max','100000 100000'),('memory.swap.max','max')]:
   changed=copy.deepcopy(caps);changed['kernel'][name]=value
   with patch.object(sys,'platform','linux'),patch.object(limits,'kernel_limits',return_value=changed):
    with self.assertRaisesRegex(ValueError,'NATIVE_RUNTIME_EXACT_BUDGET'):limits.native_runtime(bounds.NATIVE_RUNTIME_PROFILE)
 def test_amendment_wrong_os_before_any_child(self):
  import integration
  argv=['integration.py','--runtime-profile',bounds.NATIVE_RUNTIME_PROFILE,'--fixtures',str(self.root/'never-fixtures'),'--cli',str(self.root/'never-cli'),'--out',str(self.root/'never-out')]
  with patch.object(sys,'argv',argv),patch.object(sys,'platform','win32'),patch.object(integration,'reference',side_effect=AssertionError('NO_REFERENCE_OR_CHILD')),patch.object(integration.subprocess,'Popen',side_effect=AssertionError('NO_CHILD')) as child:
   with self.assertRaisesRegex(ValueError,'NATIVE_RUNTIME_LINUX_ONLY'):integration.main()
   child.assert_not_called()
  with patch.object(sys,'platform','win32'),patch.object(limits,'kernel_limits',side_effect=AssertionError('NO_KERNEL_OR_CHILD')) as read:
   with self.assertRaisesRegex(ValueError,'NATIVE_RUNTIME_LINUX_ONLY'):limits.native_runtime(bounds.NATIVE_RUNTIME_PROFILE)
   read.assert_not_called()
  self.assertFalse((self.root/'never-out').exists())
 def test_amendment_wrong_profile_entries_before_any_child(self):
  import integration,contextlib,io
  for module in [integration,host]:
   for value in ['128','129','0','max','native-linux-16-extra']:
    args=['--fixtures',str(self.root/'never-fixtures'),'--out',str(self.root/'never-out'),'--runtime-profile',value]
    if module is integration:args+=['--cli',str(self.root/'never-cli')]
    with patch.object(sys,'argv',[module.__name__+'.py',*args]),patch.object(module.subprocess,'Popen',side_effect=AssertionError('NO_CHILD')) as child,contextlib.redirect_stderr(io.StringIO()):
     with self.assertRaises(SystemExit) as ex:module.main()
     self.assertEqual(ex.exception.code,2);child.assert_not_called()
  args=['linux_host.py','--fixtures',str(self.root/'never-fixtures'),'--out',str(self.root/'never-out'),'--runtime-profile',bounds.NATIVE_RUNTIME_PROFILE,'--windows-client-unit',UNIT,'--profile-token',TOKEN]
  with patch.object(sys,'argv',args),patch.object(sys,'platform','linux'),patch.object(host,'native_runtime',side_effect=AssertionError('NO_KERNEL_OR_CHILD')),patch.object(host.subprocess,'Popen',side_effect=AssertionError('NO_CHILD')) as child:
   with self.assertRaisesRegex(ValueError,'NATIVE_RUNTIME_LINUX_ONLY'):host.main()
   child.assert_not_called()
  self.assertFalse((self.root/'never-out').exists())
 def test_amendment_counters_and_new_denial_refusal(self):
  before=dict(pidsCurrent=2,kernelPidsPeak=2,memoryCurrent=100,kernelMemoryPeak=100,pidsEvents={'max':0},memoryEvents={'oom':0,'oom_kill':0});peak=dict(before,pidsCurrent=85,kernelPidsPeak=90,memoryCurrent=400,kernelMemoryPeak=450);after=dict(before,pidsCurrent=3,kernelPidsPeak=90,kernelMemoryPeak=450)
  with patch.object(limits,'resource_counters',side_effect=[before,peak,after]):watch=limits.ResourceWatch({'synthetic':True});watch.sample();record=watch.finish()
  self.assertEqual(record['observedPidsPeak'],85);self.assertEqual(record['kernelPidsPeak'],90);self.assertEqual(record['kernelMemoryPeak'],450);limits.validate_resource_counters(record)
  for name in ['pidsMaxDelta','oomDelta','oomKillDelta']:
   changed=dict(record);changed[name]=1
   with self.assertRaisesRegex(ValueError,'NO_NEW_TASK_DENIAL_OR_OOM'):limits.validate_resource_counters(changed)
 def test_amendment_package_blob_binding_independent(self):
  package=self.root/'package';(package/'tools').mkdir(parents=True);names=['bounded_fixture.py','linux_host.py','integration.py','profile_limits.py','test_profile_limits.py','check_package.py'];literal=b'independent signed source blob\n'
  for name in names:(package/'tools'/name).write_bytes(literal)
  with patch.object(package_check.subprocess,'check_output',return_value=literal),patch.object(package_check.subprocess,'run',side_effect=AssertionError('NO_APPHOST')):
   package_check.verify_profile_helpers(package,'a'*40);(package/'tools/integration.py').write_bytes(b'forged candidate and manifest')
   with self.assertRaisesRegex(ValueError,'Exact native-runtime helper Git blob differs'):package_check.verify_profile_helpers(package,'a'*40)
 def actual_amendment_kernel_positive(self):
  self.assertEqual(sys.platform,'linux')
  if ACTUAL=='generic64':
   caps=bounds.kernel_limits();self.assertEqual(caps['kernel'],{'memory.max':'4294967296','memory.swap.max':'0','pids.max':'64','cpu.max':'200000 100000'})
   with self.assertRaisesRegex(ValueError,'NATIVE_RUNTIME_EXACT_BUDGET'):limits.native_runtime(bounds.NATIVE_RUNTIME_PROFILE)
  elif ACTUAL=='native128':
   caps=limits.native_runtime(bounds.NATIVE_RUNTIME_PROFILE)
   with self.assertRaisesRegex(ValueError,'AGGREGATE_TASK_HOLD'):bounds.kernel_limits()
   import integration
   for module in [integration,host]:
    args=['--fixtures',str(self.root/'never-fixtures'),'--out',str(self.root/('never-'+module.__name__))]
    if module is integration:args+=['--cli',str(self.root/'never-cli')]
    with patch.object(sys,'argv',[module.__name__+'.py',*args]),patch.dict(os.environ,{'OWNERSHIP_RUNTIME_PROFILE':bounds.NATIVE_RUNTIME_PROFILE}),patch.object(module.subprocess,'Popen',side_effect=AssertionError('NO_CHILD')) as child:
     with self.assertRaisesRegex(ValueError,'AGGREGATE_TASK_HOLD'):module.main()
     child.assert_not_called()
  else:raise ValueError('ACTUAL_POSITIVE_MODE_REQUIRED')
  watch=limits.ResourceWatch(caps);watch.sample();metrics=watch.finish();limits.validate_resource_counters(metrics);(self.root/'actual-kernel.json').write_text(json.dumps(dict(caps=caps,metrics=metrics),indent=2)+'\n')
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
 global WORK,ACTUAL
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--opt',type=int,required=True);p.add_argument('--only',choices=['test_controller_unit_mismatch_before_work_or_child','terminal-contract','native-runtime-amendment','actual-kernel-positive']);p.add_argument('--actual-kernel-profile',choices=['generic64','native128']);a=p.parse_args();ACTUAL=a.actual_kernel_profile
 if sys.flags.optimize!=a.opt:raise ValueError('ACTUAL_OPTIMIZATION')
 WORK=a.out.absolute();WORK.mkdir(exist_ok=False);suite=unittest.TestSuite(Controls(name) for name in ['test_amendment_finite_selector_before_limits','test_amendment_literal_kernel_limits','test_amendment_default_ignores_environment','test_amendment_exact_native_budget','test_amendment_wrong_os_before_any_child','test_amendment_wrong_profile_entries_before_any_child','test_amendment_counters_and_new_denial_refusal','test_amendment_package_blob_binding_independent']) if a.only=='native-runtime-amendment' else (unittest.TestSuite([Controls('actual_amendment_kernel_positive')]) if a.only=='actual-kernel-positive' else (unittest.TestSuite(Controls(name) for name in ['test_controller_terminal_sibling_layout_accepted','test_nested_or_foreign_terminal_parent_rejected','test_integration_nested_terminal_rejected_before_child','test_foreign_unit_record_before_any_stop','test_changed_invocation_never_stopped','test_nonterminal_group_cannot_claim_pass','test_unready_bus_proves_no_target_started']) if a.only=='terminal-contract' else (unittest.TestSuite([Controls(a.only)]) if a.only else unittest.defaultTestLoader.loadTestsFromTestCase(Controls))));result=unittest.TextTestRunner(verbosity=1).run(suite);r=dict(status='PASS' if result.wasSuccessful() and not result.skipped else 'FAIL',tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),skips=len(result.skipped),optimization=sys.flags.optimize,realWindowsBudgetQueried=a.only is None,actualKernelPositive=ACTUAL,linuxUnitOrFixtureOrSdkStarted=False,scope='Actual1GiB/1CPU/16-process Windows readback plus synthetic strict3GiB/1CPU/48-task/own-invocation/terminal controls. Actual coupled profile remains separate.')
 (WORK/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(0 if r['status']=='PASS' else 1)
if __name__=='__main__':main()
