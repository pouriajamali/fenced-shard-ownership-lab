"""Verify the extracted bytes and execute that package's native apphost."""
import argparse,hashlib,json,os,platform,subprocess
from pathlib import Path,PurePosixPath

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--package',type=Path,required=True);parser.add_argument('--commit',required=True);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    package=a.package.resolve();a.out.parent.mkdir(parents=True,exist_ok=True);assert not a.out.exists()
    manifest=json.loads((package/'BUILD-MANIFEST.json').read_text());assert manifest['sourceCommit']==a.commit
    checks=[];expected=set()
    for record in manifest['files']:
        relative=PurePosixPath(record['path']);assert not relative.is_absolute() and '..' not in relative.parts
        assert record['path'] not in expected;expected.add(record['path']);file=package/relative
        assert file.is_file() and not file.is_symlink() and file.stat().st_size==record['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==record['sha256']
    assert {f.relative_to(package).as_posix() for f in package.rglob('*') if f.is_file()}==expected|{'BUILD-MANIFEST.json'};checks.append('exact-manifest-file-set-and-sha256')
    assert 'MIT License' in (package/'LICENSE').read_text();assert (package/'licenses').is_dir();checks.append('original-and-third-party-notices')
    sbom=json.loads((package/'SBOM.spdx.json').read_text());assert sbom['spdxVersion']=='SPDX-2.3' and sbom['packages'];checks.append('resolved-shipped-sbom-present')
    app=package/('ownership.exe' if platform.system()=='Windows' else 'ownership');assert app.is_file()
    environment=os.environ.copy();environment.pop('OWNERSHIP_LAB_TELEMETRY',None)
    def call(args,code):
        process=subprocess.run([str(app),*args],env=environment,capture_output=True,text=True,timeout=20);assert process.returncode==code,(args,process.returncode,process.stdout,process.stderr);return process.stdout
    assert 'Synthetic literal-loopback only' in call(['--help'],0);checks.append('actual-native-apphost-help')
    version=json.loads(call(['--version'],0));assert a.commit in version['version'];checks.append('actual-apphost-exact-source-version')
    invalid=json.loads(call(['acquire','http://example.com:2379/','worker', '3'],2));assert invalid['code']=='LITERAL_LOOPBACK_ENDPOINT_REQUIRED';checks.append('external-endpoint-rejected-before-network')
    receipt={'status':'PASS','sourceCommit':a.commit,'rid':manifest['rid'],'os':platform.system(),'checks':checks,'checkCount':len(checks),'filesVerified':len(expected)}
    a.out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()
