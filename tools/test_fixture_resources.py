"""N13 actual owned supervision regressions; trusted tiny Python children only."""
import argparse,json,os,subprocess,sys,unittest
from pathlib import Path
from unittest import mock
import bounded_fixture as b
WORK=None
class ResourceControls(unittest.TestCase):
 def setUp(self):self.root=WORK/self._testMethodName;self.root.mkdir()
 def test_missing_capability_before_fork(self):
  evidence=self.root/'evidence';evidence.mkdir()
  with mock.patch.object(b,'kernel_limits',side_effect=ValueError('DELEGATED_CGROUP_REQUIRED')),mock.patch.object(b.os,'fork',side_effect=AssertionError('CHILD_MUST_NOT_START')) as fork:
   with self.assertRaisesRegex(ValueError,'^DELEGATED_CGROUP_REQUIRED$'):b.run([sys.executable,'-c','raise SystemExit(0)'],cwd=self.root,env={},evidence=evidence,seconds=1,disk_root=self.root)
   fork.assert_not_called()
 def test_wall_log_fast_exit_disk_and_nonowned_sentinel(self):
  actual=b.kernel_limits();sentinel=subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(30)'],start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   identity=Path('/proc',str(sentinel.pid),'stat').read_text().rsplit(')',1)[1].split()[19]
   cases=[('wall','import time;time.sleep(5)','CHILD_WALL_CAP',None),('log','import os;os.write(1,b"x"*8192)','CHILD_LOG_CAP',('LOG_MAX',4096)),('disk','from pathlib import Path;Path("payload").write_bytes(b"x"*8192)','NEW_WORKSPACE_CAP',('WORKSPACE_MAX',4096))]
   results=[]
   for label,source,expected,patch in cases:
    root=self.root/label;root.mkdir();script=root/'child.py';script.write_text(source,encoding='utf-8');evidence=root/'evidence';evidence.mkdir()
    context=mock.patch.object(b,patch[0],patch[1]) if patch else __import__('contextlib').nullcontext()
    with context:
     with self.assertRaisesRegex(ValueError,'^'+expected+'$'):b.run([sys.executable,'-I','-B',str(script)],cwd=root,env={'PATH':'/usr/bin:/bin','HOME':str(root),'LANG':'C.UTF-8'},evidence=evidence,seconds=1,disk_root=root)
    receipt=json.loads((evidence/'process.json').read_bytes());self.assertEqual(receipt['status'],'HOLD_'+expected);self.assertEqual(receipt['parentLimits'],actual);self.assertEqual(receipt['childBeforeExec'],actual)
    self.assertIsNone(sentinel.poll());self.assertEqual(Path('/proc',str(sentinel.pid),'stat').read_text().rsplit(')',1)[1].split()[19],identity)
    with self.assertRaises(ProcessLookupError):os.killpg(receipt['pid'],0)
    if label=='log':self.assertEqual(receipt['savedLogBytes'],0);self.assertEqual((evidence/'stdout.log').stat().st_size,0)
    results.append(dict(case=label,expected=expected,actual=receipt['status'],ownedChildGone=True,separateSentinelUnaffected=True))
   (self.root/'actual-cases.json').write_text(json.dumps(results,indent=2)+'\n')
  finally:
   if sentinel.poll() is None:sentinel.terminate()
   sentinel.wait(timeout=5)
def main():
 global WORK
 parser=argparse.ArgumentParser();parser.add_argument('--work',required=True,type=Path);parser.add_argument('--expected-optimization',required=True,type=int);a=parser.parse_args();b.require(sys.flags.optimize==a.expected_optimization,'ACTUAL_OPTIMIZATION');WORK=b.canonical(a.work.absolute(),exists=False);WORK.mkdir();caps=b.kernel_limits();result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(ResourceControls));receipt=dict(status='PASS' if result.wasSuccessful() and not result.skipped else 'FAIL',tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),skips=len(result.skipped),optimize=sys.flags.optimize,kernelLimits=caps,actualSyntheticChildren=3,candidateSpawns=0,scope='Actual bounded fork-before-exec/cgroup admission; wall/log/fast-exit disk guards and separate sentinel preservation. Test log/disk thresholds are reduced; production limits are unchanged.')
 (WORK/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt));raise SystemExit(0 if receipt['status']=='PASS' else 1)
if __name__=='__main__':main()
