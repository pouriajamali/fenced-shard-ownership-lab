"""N04/N07/N08/N14 portable-input controls. No SDK, network or candidate execution."""
import argparse,base64,copy,hashlib,json,os,sys,unittest
from pathlib import Path
from unittest import mock
import build_etcd_fixture as builder
import etcd_inputs as inputs
import prepare_linux as prepare
WORK=None
PREFIX='etcd-0a173d0410a96d01091b484daae81365bbcde57e'
DATA=b'module example.invalid/literal\n'
class InputControls(unittest.TestCase):
 def setUp(self):self.root=WORK/self._testMethodName;self.root.mkdir()
 def graph(self):
  source=self.root/'source';source.mkdir();cache=self.root/'cache';cache.mkdir();mod=cache/'literal.mod';mod.write_bytes(DATA)
  digest=hashlib.sha256(DATA).hexdigest();h1='h1:'+base64.b64encode(hashlib.sha256((digest+'  go.mod\n').encode()).digest()).decode()
  expected=[dict(module='example.invalid/literal',version='v1.2.3',goModBytes=len(DATA),goModSha256=digest,goModH1=h1)]
  graph=[dict(Path='example.invalid/main',Main=True,Dir=str(source)),dict(Path='example.invalid/literal',Version='v1.2.3',GoMod=str(mod),GoModSum=h1)]
  return source,cache,mod,expected,graph,[dict(module='example.invalid/main',relativePath='.')]
 def test_fixed_metadata_control(self):
  source,cache,mod,expected,graph,mains=self.graph();inputs.validate_metadata_graph(graph,expected,mains,source,cache)
 def test_wrong_version_h1_missing_extra_replacement_and_duplicate(self):
  source,cache,mod,expected,graph,mains=self.graph()
  changed=[]
  for key,value in [('Version','v1.2.4'),('GoModSum','h1:forged'),('Replace',{'Path':'attacker.invalid/new'})]:
   rows=copy.deepcopy(graph);rows[1][key]=value;changed.append(rows)
  changed.extend([graph[:1],graph+[dict(Path='extra.invalid/x',Version='v9.9.9',GoMod=str(mod))],graph+[copy.deepcopy(graph[0])]])
  for rows in changed:
   with self.subTest(rows=rows):
    with self.assertRaises((ValueError,KeyError)):inputs.validate_metadata_graph(rows,expected,mains,source,cache)
  missing=copy.deepcopy(expected);missing[0]['goModH1']=''
  with self.assertRaises(ValueError):inputs.validate_metadata_graph(graph,missing,mains,source,cache)
 def test_original_mod_bytes_and_cache_containment(self):
  source,cache,mod,expected,graph,mains=self.graph();mod.write_bytes(b'X'*len(DATA))
  with self.assertRaisesRegex(ValueError,'ORIGINAL_METADATA_BYTES'):inputs.validate_metadata_graph(graph,expected,mains,source,cache)
  mod.write_bytes(DATA);outside=self.root/'outside.mod';outside.write_bytes(DATA);graph[1]['GoMod']=str(outside)
  with self.assertRaisesRegex(ValueError,'ORIGINAL_METADATA_BYTES'):inputs.validate_metadata_graph(graph,expected,mains,source,cache)
 def test_original_workspace_objects_and_forged_local_manifest(self):
  source=self.root/'source';source.mkdir();os.chmod(source,0o755);files={'go.mod':b'module example.invalid/main\n','go.sum':b'original sums\n','go.work':b'go 1.26.0\nuse .\n'};rows=[dict(path=PREFIX,type='directory',mode=0o755)]
  for name,data in files.items():p=source/name;p.write_bytes(data);os.chmod(p,0o644);rows.append(dict(path=PREFIX+'/'+name,type='file',mode=0o644,bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
  builder.verify_tree(source,rows,PREFIX)
  for name in files:
   p=source/name;p.write_bytes(b'X'*len(files[name]));forged=[dict(x,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) if x['path']==PREFIX+'/'+name else x for x in rows]
   self.assertNotEqual(forged,rows)
   with self.assertRaisesRegex(ValueError,'SOURCE_FILE_IDENTITY'):builder.verify_tree(source,rows,PREFIX)
   p.write_bytes(files[name])
 def test_cached_raw_flip_and_size_rejected_before_network(self):
  path=self.root/'source.bin';record=dict(url='https://proxy.golang.org/fixture',bytes=len(DATA),sha256=hashlib.sha256(DATA).hexdigest());path.write_bytes(DATA)
  with mock.patch.object(inputs.urllib.request.OpenerDirector,'open',side_effect=AssertionError('NETWORK_MUST_NOT_RUN')) as network:
   self.assertEqual(inputs.obtain(record,path,[0]),path)
   for payload in [b'X'*len(DATA),DATA+b'X',DATA[:-1]]:
    path.write_bytes(payload)
    with self.assertRaisesRegex(ValueError,'EXISTING_IMMUTABLE_INPUT'):inputs.obtain(record,path,[0])
   network.assert_not_called()
 def test_default_and_direct_before_work_or_children(self):
  for module,argv in [(builder,['build_etcd_fixture.py','--archives',str(self.root),'--out',str(self.root/'build')]),(prepare,['prepare_linux.py','--archives',str(self.root),'--out',str(self.root/'prepared')])]:
   with mock.patch.object(module,'reference',side_effect=ValueError('INDEPENDENT_REFERENCE_REQUIRED')),mock.patch.object(sys,'argv',argv),mock.patch('subprocess.Popen',side_effect=AssertionError('CHILD_MUST_NOT_RUN')) as spawn,mock.patch.object(inputs,'reproduce',side_effect=AssertionError('BUILD_MUST_NOT_RUN')) as build:
    with self.assertRaisesRegex(ValueError,'^INDEPENDENT_REFERENCE_REQUIRED$'):module.main()
    spawn.assert_not_called();build.assert_not_called()
  self.assertFalse((self.root/'build').exists());self.assertFalse((self.root/'prepared').exists())
def main():
 global WORK
 parser=argparse.ArgumentParser();parser.add_argument('--work',required=True,type=Path);parser.add_argument('--expected-optimization',required=True,type=int);parser.add_argument('--only',choices=['test_original_workspace_objects_and_forged_local_manifest']);a=parser.parse_args()
 if sys.flags.optimize!=a.expected_optimization:raise ValueError('ACTUAL_OPTIMIZATION')
 WORK=a.work.absolute();WORK.mkdir(exist_ok=False);suite=unittest.TestSuite([InputControls(a.only)]) if a.only else unittest.defaultTestLoader.loadTestsFromTestCase(InputControls);result=unittest.TextTestRunner(verbosity=1).run(suite);r=dict(status='PASS' if result.wasSuccessful() and not result.skipped else 'FAIL',tests=result.testsRun,errors=len(result.errors),failures=len(result.failures),skips=len(result.skipped),optimize=sys.flags.optimize,networkRequests=0,candidateOrSdkSpawns=0,scope='Independent fixed original metadata/object/raw-input and default/direct admission-before-work controls.')
 (WORK/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));raise SystemExit(0 if r['status']=='PASS' else 1)
if __name__=='__main__':main()
