"""Independently hash actual downloaded NuGet files, never trust a normalized contentHash as a file checksum."""
import argparse,base64,hashlib,json
from pathlib import Path
def require(ok,message):
    if not ok:raise ValueError(message)
def verify(package,nuget):
    dependencies=json.loads((package/'DEPENDENCIES.json').read_text())['packages'];sbom=json.loads((package/'SBOM.spdx.json').read_text());components={c['name']+'/'+c['versionInfo']:c for c in sbom['packages'] if c['SPDXID']!='SPDXRef-App'}
    require(len(components)==len(dependencies),'Unique component graph');verified=[]
    for dep in dependencies:
        name=dep['id'].lower();version=dep['version'];directory=nuget/name/version;archive=directory/(name+'.'+version+'.nupkg');require(archive.is_file(),'Missing actual archive '+name)
        digest=hashlib.sha512()
        with archive.open('rb') as stream:
            while True:
                block=stream.read(256*1024)
                if not block:break
                digest.update(block)
        actual=digest.hexdigest();component=components[dep['id']+'/'+version];normalized=json.loads((directory/'.nupkg.metadata').read_text())['contentHash']
        require(dep['nugetContentHash']==normalized and len(base64.b64decode(normalized,validate=True))==64,'Normalized identity mismatch')
        require(dep['rawSignedNupkgSha512']==actual and component['checksums']==[{'algorithm':'SHA512','checksumValue':actual}],'SPDX does not hash actual raw signed archive '+name)
        require(component['downloadLocation']=='https://api.nuget.org/v3-flatcontainer/'+name+'/'+version+'/'+archive.name,'Archive location mismatch')
        verified.append(dict(id=dep['id'],version=version,rawSignedArchiveSha512=actual,normalizedIdentityEqualsRawDigest=base64.b64decode(normalized).hex()==actual))
    return dict(status='PASS_ACTUAL_RAW_NUGET_ARCHIVE_BYTES',components=len(verified),verified=verified,boundary='Hashes the public NuGet cache archive bytes used for build. Not runtime behavior, independent authorship or reproducible build proof.')
def main():
    p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--nuget-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();require(not a.out.exists(),'Receipt exists');result=verify(a.package,a.nuget_root);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'components':result['components']}))
if __name__=='__main__':main()
