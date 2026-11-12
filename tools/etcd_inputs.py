"""Portable exact-input etcd reproduction. No operator receipt or private path is read."""
import base64,hashlib,json,os,shutil,stat,time,urllib.parse,urllib.request
from pathlib import Path
from bounded_fixture import canonical,clean_go_environment,fresh_directory,kernel_limits,require,run,sha256,strict_json
import check_actionlint as archive_guard
INPUT_SHA256='1657bd245d79c1eb8f0691a9e1d0b9065e562e34c2be84a7e311168f5229d785'

def escaped(value):return ''.join('!'+c.lower() if 'A'<=c<='Z' else c for c in value)

def sequence(raw):
 text=raw.decode('utf-8');decoder=json.JSONDecoder();rows=[]
 while text.strip():
  text=text.lstrip();row,n=decoder.raw_decode(text);rows.append(row);text=text[n:]
 return rows

def obtain(record,path,budget):
 path=canonical(path,exists=False);require(type(record['bytes']) is int and 0<record['bytes']<=67108864,'RAW_INPUT_SIZE')
 if path.exists():require(path.stat().st_size==record['bytes'] and sha256(path)==record['sha256'],'EXISTING_IMMUTABLE_INPUT');return path
 url=record['url'];require(urllib.parse.urlsplit(url).scheme=='https' and urllib.parse.urlsplit(url).hostname in ('proxy.golang.org','go.dev','codeload.github.com'),'FINITE_SOURCE_HOST')
 path.parent.mkdir(parents=True,exist_ok=True);start=time.monotonic();count=0;digest=hashlib.sha256();opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 with opener.open(urllib.request.Request(url,headers={'User-Agent':'ownership-etcd-reproduce/1'}),timeout=35) as response,path.open('xb') as output:
  require(response.status==200 and urllib.parse.urlsplit(response.url).scheme=='https' and urllib.parse.urlsplit(response.url).hostname in ('proxy.golang.org','go.dev','codeload.github.com','dl.google.com'),'SOURCE_RESPONSE')
  while True:
   data=response.read(65536)
   if not data:break
   count+=len(data);budget[0]+=len(data);require(count<=record['bytes'] and budget[0]<=1073741824 and time.monotonic()-start<=120,'REAL_INPUT_CAP');digest.update(data);output.write(data)
 require(count==record['bytes'] and digest.hexdigest()==record['sha256'],'EXACT_SOURCE_HELD_RAW_INPUT');return path

def validate_metadata_graph(graph, metadata_modules, workspace_modules, source, cache_root):
 expected={m['module']:m for m in metadata_modules};require(len(expected)==len(metadata_modules),'UNIQUE_SOURCE_HELD_METADATA')
 external=[x for x in graph if not x.get('Main')];require(len(external)==len(expected) and {x['Path'] for x in external}==set(expected),'ORIGINAL_MVS_METADATA_SET')
 for item in external:
  m=expected[item['Path']];require(not item.get('Replace') and item['Version']==m['version'],'ORIGINAL_MVS_VERSION')
  file=canonical(Path(item['GoMod']));require(file.is_relative_to(cache_root) and file.stat().st_size==m['goModBytes'] and sha256(file)==m['goModSha256'],'ORIGINAL_METADATA_BYTES')
  actual='h1:'+base64.b64encode(hashlib.sha256((hashlib.sha256(file.read_bytes()).hexdigest()+'  go.mod\n').encode()).digest()).decode()
  require(actual==m['goModH1'] and (not item.get('GoModSum') or item['GoModSum']==m['goModH1']),'ORIGINAL_METADATA_H1')
 mains={x['Path']:Path(x['Dir']).relative_to(source).as_posix() for x in graph if x.get('Main')};require(len(mains)==len([x for x in graph if x.get('Main')]) and mains=={x['module']:x['relativePath'] for x in workspace_modules},'ORIGINAL_LOCAL_WORKSPACES')

def prepare(archives,work,lock):
 from build_etcd_fixture import materialize,verify_tree,SOURCE_COMMIT
 kernel_limits();work=canonical(work);archives=canonical(archives);p=Path(__file__).with_name('etcd-build.inputs.json');require(sha256(p)==INPUT_SHA256 and lock.get('buildInputsSha256')==INPUT_SHA256,'INDEPENDENT_PORTABLE_INPUT_REFERENCE');inputs=strict_json(p.read_bytes())
 require(inputs['sourceCommit']==SOURCE_COMMIT and len(inputs['metadataModules'])==741 and len(inputs['sourceModules'])==58,'EXACT_ORIGINAL_INPUT_SCOPE');budget=[0];rawRoot=archives/'etcd-source-inputs';rawRoot.mkdir(exist_ok=True)
 sourceRecord=lock['sourceArchive'];compilerRecord=lock['compilerArchive'];sourceArchive=obtain(sourceRecord,rawRoot/'etcd-source.tar.gz',budget);compilerArchive=obtain(compilerRecord,rawRoot/'go-linux-amd64.tar.gz',budget)
 source=work/'source';sourceRows=materialize(sourceArchive,source,work,'etcd-'+SOURCE_COMMIT,sourceRecord['sha256']);go=work/'compiler';sdkRows=materialize(compilerArchive,go,work,'go',compilerRecord['sha256'])
 compilerRows=[dict(path='go/'+r['path'].removeprefix('go/'),bytes=r['bytes'],sha256=r['sha256'],mode=oct(r['mode'])) for r in sdkRows if r['type']=='file']
 # build_once addresses compiler.parent / member.path. Keep the unmodified compiler under a go basename.
 nativeCompiler=work/'sdk'/'go';nativeCompiler.parent.mkdir();go.rename(nativeCompiler);go=canonical(nativeCompiler)
 metadataEnvRoot=work/'metadata-environment';metadataEnvRoot.mkdir();env=clean_go_environment(go,metadataEnvRoot,workspace_file=str(source/'go.work'));env['GOPROXY']='https://proxy.golang.org';folder=work/'metadata';folder.mkdir()
 run([str(go/'bin/go'),'list','-m','-mod=readonly','-json','all'],cwd=source,env=env,evidence=folder,seconds=300,disk_root=work,other_disk_roots=(rawRoot,))
 graph=sequence((folder/'stdout.log').read_bytes());validate_metadata_graph(graph,inputs['metadataModules'],inputs['workspaceMainModules'],source,metadataEnvRoot);verify_tree(source,sourceRows,'etcd-'+SOURCE_COMMIT)
 authRoot=work/'authentication-environment';authRoot.mkdir();authEnv=clean_go_environment(go,authRoot);authEnv['GOPATH']=env['GOPATH'];authEnv['GOMODCACHE']=str(Path(env['GOPATH'])/'pkg/mod');authEnv['GOPROXY']='https://proxy.golang.org';empty=work/'no-main-module';empty.mkdir();captured=[]
 for i,m in enumerate(inputs['sourceModules']):
  name=escaped(m['module']);version=escaped(m['version']);cache=canonical(Path(authEnv['GOMODCACHE'])/'cache/download'/name/'@v',exists=False);cache.mkdir(parents=True,exist_ok=True);require(not (cache/(version+'.ziphash')).exists(),'NO_PREBLESSED_SOURCE_ZIP')
  raws={key:obtain(m[key],rawRoot/('module-'+str(i).zfill(2)+'.'+suffix),budget) for suffix,key in [('zip','rawZip'),('mod','goMod'),('info','info')]}
  rows=archive_guard.archive_inventory(raws['rawZip']);actual={x['path']:(x['bytes'],x['sha256']) for x in rows if x['type']=='file'};require(actual=={x['path']:(x['bytes'],x['sha256']) for x in m['members']},'COMPLETE_ORIGINAL_SOURCE_ARCHIVE')
  hashed=hashlib.sha256()
  for name,(size,digest) in sorted(actual.items()):hashed.update((digest+'  '+name+'\n').encode())
  require('h1:'+base64.b64encode(hashed.digest()).decode()==m['h1'],'NORMALIZED_ORIGINAL_SOURCE_H1')
  prefix=m['module']+'@'+m['version']+'/'
  for name,row in m['capturedText'].items():
   require(hashlib.sha256(row['text'].encode()).hexdigest()==row['sha256'],'SOURCE_HELD_TEXT_BYTES')
   if prefix+name in actual:require(actual[prefix+name][1]==row['sha256'],'FULL_ORIGINAL_NOTICE_OR_SOURCE_DESCRIPTOR')
   else:require(name=='go.mod' and m['goMod']['sha256']==row['sha256'],'ORIGINAL_SEPARATE_CANONICAL_GO_MOD_DESCRIPTOR')
  for suffix,key in [('zip','rawZip'),('mod','goMod'),('info','info')]:
   dest=canonical(cache/(version+'.'+suffix),exists=False)
   if dest.exists():require(dest.stat().st_size==m[key]['bytes'] and sha256(dest)==m[key]['sha256'],'EXISTING_METADATA_SEED')
   else:
    with raws[key].open('rb') as incoming,dest.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing,65536)
  evidence=work/('authenticate-'+str(i).zfill(2));evidence.mkdir();run([str(go/'bin/go'),'mod','download','-json',m['module']+'@'+m['version']],cwd=empty,env=authEnv,evidence=evidence,seconds=90,disk_root=work,other_disk_roots=(rawRoot,))
  observed=strict_json((evidence/'stdout.log').read_bytes());require(not observed.get('Error') and observed['Path']==m['module'] and observed['Version']==m['version'] and observed['Sum']==m['h1'] and observed['GoModSum']==m['goModH1'],'CANONICAL_AUTHENTICATED_SOURCE_H1')
  lookup=canonical(Path(authEnv['GOMODCACHE'])/'cache/download/sumdb/sum.golang.org/lookup'/(escaped(m['module'])+'@'+version));lines=lookup.read_text().splitlines();require(m['module']+' '+m['version']+' '+m['h1'] in lines and m['module']+' '+m['version']+'/go.mod '+m['goModH1'] in lines,'SDK_VERIFIED_CANONICAL_SIGNED_LOOKUP')
  directory=canonical(Path(observed['Dir']));require(directory.is_relative_to(Path(authEnv['GOMODCACHE'])),'OWN_MODULE_CACHE');files={p.relative_to(directory).as_posix():p for p in directory.rglob('*') if not p.is_dir()};expectedFiles={x['path'][len(prefix):]:x for x in m['members']};require(set(files)==set(expectedFiles),'COMPLETE_MATERIALIZED_SOURCE')
  for name,file in files.items():
   canonical(file);s=file.lstat();r=expectedFiles[name];require(stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_uid==os.getuid() and stat.S_IMODE(s.st_mode) in (0o444,0o555) and s.st_size==r['bytes'] and sha256(file)==r['sha256'],'EVERY_MATERIALIZED_SOURCE_INPUT')
  captured.append(dict(module=m['module'],version=m['version'],h1=m['h1'],goModH1=m['goModH1'],signedLookupSha256=sha256(lookup)))
 verify_tree(source,sourceRows,'etcd-'+SOURCE_COMMIT);(work/'authenticated-inputs.json').write_text(json.dumps(captured,indent=2)+'\n')
 return dict(source=source,source_rows=sourceRows,compiler=go,compiler_members=compilerRows,module_cache=Path(authEnv['GOMODCACHE']))

def reproduce(archives,out,work,lock):
 from build_etcd_fixture import build_once
 from check_etcd_fixture import FIELDS,admitted_etcd
 kernel_limits();work=canonical(work,exists=False);work.parent.mkdir(parents=True,exist_ok=True);work=fresh_directory(work,work.parent);os.chmod(work,0o700);out=canonical(out,exists=False);require(not out.exists() and out!=work and not out.is_relative_to(work) and not work.is_relative_to(out),'SEPARATE_FRESH_BUILD_AND_SERVING_ROOTS')
 inputs=prepare(archives,work,lock);records=[]
 for number in (1,2):
  row=build_once(**inputs,work=work/('build-'+str(number)),owned_root=work,number=number,other_disk_roots=(archives,));require(row['binarySha256']==lock['binarySha256'] and row['binaryBytes']==lock['binaryBytes'],'INDEPENDENT_ADMITTED_REPRODUCED_BYTES');records.append(row)
 require(records[0]['binarySha256']==records[1]['binarySha256'],'ACTUAL_TWO_BUILD_EQUALITY');out.mkdir(parents=True,exist_ok=False);target=out/'etcd-source-go1.26.11';target.mkdir()
 with (work/'build-1/etcd').open('rb') as incoming,(target/'etcd').open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing,65536)
 os.chmod(target/'etcd',0o755);proofRoot=Path(__file__).resolve().parents[1]/'vendor/etcd-admission'
 for name,digest in lock['proofs'].items():
  source=canonical(proofRoot/Path(name).name);require(sha256(source)==digest,'SOURCE_HELD_ADMISSION_PROOF');destination=out/name;destination.parent.mkdir(parents=True,exist_ok=True)
  with source.open('rb') as incoming,destination.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing,65536)
 manifest={key:lock[key] for key in FIELDS};(out/'ETCD-BUILD.json').write_text(json.dumps(manifest,indent=2)+'\n');
 with admitted_etcd(out):pass  # Recheck actual copied bytes under the independent serving guard.
 (work/'reproduction.json').write_text(json.dumps(dict(status='TWO_FRESH_BUILDS_MATCH_INDEPENDENT_ADMITTED_IMAGE',binarySha256=lock['binarySha256'],records=records,reusedFrozenSecurityProofs=True,noTargetExecuted=True),indent=2)+'\n')
 return manifest
