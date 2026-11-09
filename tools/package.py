"""Build clean exact-commit self-contained archives; never publish or overwrite."""
import argparse,base64,datetime,hashlib,json,os,platform,shutil,subprocess,tarfile,uuid,xml.etree.ElementTree as ET,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args],text=True).strip()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['commit','rid','work','out']:parser.add_argument('--'+name,required=True)
    parser.add_argument('--dotnet',default='dotnet');parser.add_argument('--local-candidate',action='store_true');a=parser.parse_args()
    assert a.rid in ['win-x64','linux-x64'] and git('rev-parse','HEAD')==a.commit
    assert not git('status','--porcelain'),'Exact clean source required'
    if not a.local_candidate:assert platform.system()==('Windows' if a.rid=='win-x64' else 'Linux'),'Public build OS must match RID'
    work=Path(a.work).resolve();work.mkdir(parents=True,exist_ok=False);out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    published=work/'published';log=work/'build.log'
    commands=[[a.dotnet,'restore','src/Ownership.Cli/Ownership.Cli.csproj','--runtime',a.rid,'--locked-mode'],
      [a.dotnet,'publish','src/Ownership.Cli/Ownership.Cli.csproj','-c','Release','-r',a.rid,'--self-contained','true','--no-restore',
       '-p:RuntimeFrameworkVersion=10.0.14','-p:PublishTrimmed=false','-p:PublishAot=false','-p:PublishReadyToRun=false',
       '-p:DebugType=None','-p:DebugSymbols=false','-p:SourceRevisionId='+a.commit,'-o',str(published)]]
    with log.open('wb') as output:
        for command in commands:subprocess.run(command,cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,check=True,timeout=300)
    assert not git('status','--porcelain'),'Build changed frozen source/locks'
    version=ET.parse(ROOT/'Directory.Build.props').findtext('.//Version')
    name=f'fenced-shard-ownership-lab-v{version}-{a.rid}';package=work/name;shutil.copytree(published,package)
    assert a.commit.encode() in (package/'ownership.dll').read_bytes(),'Source commit absent from binary metadata'
    for file in ['README.md','LICENSE','NOTICE.md','PROVENANCE.md','SIGNING-PUBLIC-KEY.pub','CONTRIBUTING.md']:shutil.copy2(ROOT/file,package/file)
    for directory in ['docs','tools']:shutil.copytree(ROOT/directory,package/directory,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    assets=json.loads((ROOT/'src/Ownership.Cli/obj/project.assets.json').read_text(encoding='utf-8'))
    folders=[Path(p) for p in assets['packageFolders']];dependencies=[];licenses=package/'licenses';licenses.mkdir()
    for identity,entry in sorted(assets['libraries'].items()):
        if entry['type']!='package':continue
        identifier,version_id=identity.split('/')
        directory=next(p/identifier.lower()/version_id for p in folders if (p/identifier.lower()/version_id).is_dir())
        metadata=ET.parse(next(directory.glob('*.nuspec'))).find('{*}metadata');license_element=metadata.find('{*}license')
        assert license_element is not None and license_element.attrib.get('type')=='expression'
        declared=license_element.text;assert declared in ['MIT','Apache-2.0','PostgreSQL','BSD-3-Clause'],(identity,declared)
        dependencies.append({'id':identifier,'version':version_id,'license':declared,'nugetContentHash':entry.get('sha512')})
        for file in directory.iterdir():
            if file.is_file() and (file.name.upper().startswith('LICENSE') or file.name.upper().startswith('THIRD-PARTY-NOTICES')):shutil.copy2(file,licenses/(identifier+'-'+file.name))
    locks=json.loads((ROOT/'src/Ownership.Cli/packages.lock.json').read_text(encoding='utf-8'))['dependencies']
    locked={(key,value['resolved'],value['contentHash']) for graph in locks.values() for key,value in graph.items() if 'contentHash' in value}
    actual={(d['id'],d['version'],d['nugetContentHash']) for d in dependencies}
    assert actual==locked,'Resolved/shipped library graph differs from source lock'
    runtime_id='Microsoft.NETCore.App.Runtime.'+a.rid
    runtime=next(p/runtime_id.lower()/'10.0.14' for p in folders if (p/runtime_id.lower()/'10.0.14').is_dir())
    notices=[f for f in runtime.iterdir() if f.is_file() and (f.name.upper().startswith('LICENSE') or f.name.upper().startswith('THIRD-PARTY-NOTICES'))]
    assert any(f.name.upper().startswith('LICENSE') for f in notices) and any(f.name.upper().startswith('THIRD-PARTY-NOTICES') for f in notices)
    for file in notices:shutil.copy2(file,licenses/(runtime_id+'-'+file.name))
    dependencies.append({'id':runtime_id,'version':'10.0.14','license':'MIT','notice':'Bundled runtime retains its own third-party notices'})
    (package/'DEPENDENCIES.json').write_text(json.dumps({'packages':dependencies,'externalFixtures':'Six pinned upstream archives in tools/upstream.lock.json are REFERENCES, not bundled servers/libraries.'},indent=2)+'\n',encoding='utf-8')
    spdx=[{'name':'Fenced Shard Ownership Lab','SPDXID':'SPDXRef-App','versionInfo':version,'downloadLocation':'NOASSERTION','filesAnalyzed':False,'licenseDeclared':'MIT','licenseConcluded':'NOASSERTION'}]
    relationships=[{'spdxElementId':'SPDXRef-DOCUMENT','relationshipType':'DESCRIBES','relatedSpdxElement':'SPDXRef-App'}]
    for i,dep in enumerate(dependencies):
        item={'name':dep['id'],'SPDXID':'SPDXRef-Package'+str(i),'versionInfo':dep['version'],'downloadLocation':'https://api.nuget.org/v3-flatcontainer/'+dep['id'].lower()+'/'+dep['version']+'/'+dep['id'].lower()+'.'+dep['version']+'.nupkg','filesAnalyzed':False,'licenseDeclared':dep['license'],'licenseConcluded':'NOASSERTION'}
        if dep.get('nugetContentHash'):item['checksums']=[{'algorithm':'SHA512','checksumValue':base64.b64decode(dep['nugetContentHash']).hex()}]
        spdx.append(item);relationships.append({'spdxElementId':'SPDXRef-App','relationshipType':'DEPENDS_ON','relatedSpdxElement':item['SPDXID']})
    sbom={'spdxVersion':'SPDX-2.3','dataLicense':'CC0-1.0','SPDXID':'SPDXRef-DOCUMENT','name':name,'documentNamespace':'https://github.com/pouriajamali/fenced-shard-ownership-lab/spdx/'+str(uuid.uuid4()),'creationInfo':{'creators':['Tool: ownership-lab-package.py'],'created':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},'packages':spdx,'relationships':relationships}
    (package/'SBOM.spdx.json').write_text(json.dumps(sbom,indent=2)+'\n',encoding='utf-8')
    files=[]
    for file in sorted(package.rglob('*')):
        assert not file.is_symlink()
        if not file.is_file():continue
        relative=file.relative_to(package).as_posix();assert not relative.lower().endswith(('.pdb','.db','.sqlite','.private.json'))
        files.append({'path':relative,'bytes':file.stat().st_size,'sha256':sha(file)})
    manifest={'schema':1,'version':version,'rid':a.rid,'sourceCommit':a.commit,'sourceTree':git('rev-parse','HEAD^{tree}'),'selfContained':True,'localCandidate':a.local_candidate,'buildHost':platform.system(),'files':files}
    (package/'BUILD-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    archive=out/(name+('.zip' if a.rid=='win-x64' else '.tar.gz'));assert not archive.exists()
    if a.rid=='win-x64':
        with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as zipped:
            for file in sorted(package.rglob('*')):
                if file.is_file():zipped.write(file,file.relative_to(work).as_posix())
    else:
        with tarfile.open(archive,'x:gz') as packed:
            for file in sorted(package.rglob('*')):
                if file.is_file():
                    info=packed.gettarinfo(str(file),arcname=file.relative_to(work).as_posix());info.mode=0o755 if file.name in ['ownership','createdump'] else 0o644;info.uid=info.gid=0;info.uname=info.gname=''
                    with file.open('rb') as content:packed.addfile(info,content)
    result={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'sourceCommit':a.commit,'sourceTree':manifest['sourceTree'],'rid':a.rid,'payloadFiles':len(files),'localCandidate':a.local_candidate}
    (work/'archive.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))

if __name__=='__main__':main()
