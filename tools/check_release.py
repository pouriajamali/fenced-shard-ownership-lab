"""Validate already-executed native archives, then create exact Git source/SUMS.

No runtime build, tag change or publication is performed here.
"""
import argparse,hashlib,json,subprocess,tarfile,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--commit',required=True);parser.add_argument('--tag',required=True);a=parser.parse_args()
    directory=a.directory.resolve();names={f'fenced-shard-ownership-lab-{a.tag}-win-x64.zip':'win-x64',f'fenced-shard-ownership-lab-{a.tag}-linux-x64.tar.gz':'linux-x64'}
    assert {p.name for p in directory.iterdir()}==set(names)
    tree=subprocess.check_output(['git','-C',str(ROOT),'rev-parse',a.commit+'^{tree}'],text=True).strip()
    for name,rid in names.items():
        archive=directory/name;files={}
        if name.endswith('.zip'):
            with zipfile.ZipFile(archive) as packed:
                for info in packed.infolist():
                    assert not info.is_dir() and info.filename not in files and info.file_size<128*1024*1024
                    files[info.filename]=packed.read(info)
        else:
            with tarfile.open(archive,'r:gz') as packed:
                for info in packed:
                    assert info.isfile() and info.name not in files and info.size<128*1024*1024
                    files[info.name]=packed.extractfile(info).read()
        assert len(files)<1024 and sum(map(len,files.values()))<512*1024*1024
        assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in files)
        roots={PurePosixPath(n).parts[0] for n in files};assert len(roots)==1;prefix=roots.pop()+'/'
        files={n[len(prefix):]:value for n,value in files.items()};manifest=json.loads(files.pop('BUILD-MANIFEST.json'))
        assert manifest['sourceCommit']==a.commit and manifest['sourceTree']==tree and manifest['version']==a.tag.removeprefix('v')
        assert manifest['rid']==rid and manifest['selfContained'] and not manifest['localCandidate']
        assert manifest['buildHost']==('Windows' if rid=='win-x64' else 'Linux')
        assert set(files)=={item['path'] for item in manifest['files']}
        for item in manifest['files']:assert len(files[item['path']])==item['bytes'] and hashlib.sha256(files[item['path']]).hexdigest()==item['sha256']
        assert a.commit.encode() in files['ownership.dll'] and 'SBOM.spdx.json' in files
    source=directory/f'fenced-shard-ownership-lab-{a.tag}-source.zip';assert not source.exists()
    prefix=f'fenced-shard-ownership-lab-{a.tag}-source/'
    subprocess.run(['git','-C',str(ROOT),'-c','core.autocrlf=false','-c','core.eol=lf','archive','--format=zip','--prefix='+prefix,'--output='+str(source),a.commit],check=True)
    tracked=subprocess.check_output(['git','-C',str(ROOT),'ls-tree','-r','--name-only',a.commit],text=True).splitlines()
    with zipfile.ZipFile(source) as packed:
        assert {i.filename for i in packed.infolist() if not i.is_dir()}=={prefix+n for n in tracked}
        for name in tracked:assert packed.read(prefix+name)==subprocess.check_output(['git','-C',str(ROOT),'show',a.commit+':'+name])
    checks=''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(directory.iterdir()))
    (directory/'SHA256SUMS.txt').write_text(checks,encoding='utf-8',newline='\n')
    print(json.dumps({'status':'NATIVE_ARCHIVES_AND_GIT_SOURCE_VERIFIED','commit':a.commit,'tree':tree,'sourceFiles':len(tracked)}))

if __name__=='__main__':main()
