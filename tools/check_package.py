"""Verify the extracted bytes and execute that package's native apphost."""
import argparse,hashlib,json,os,platform,subprocess
from pathlib import Path,PurePosixPath

def require(condition,message='Validation failed'):
    if not condition:raise ValueError(message)

def verify_profile_helpers(package,commit):
    require(len(commit)==40 and all(c in '0123456789abcdef' for c in commit),'EXACT_SOURCE_COMMIT_FORMAT')
    for name in ['bounded_fixture.py','linux_host.py','integration.py','profile_limits.py','test_profile_limits.py','check_package.py']:
        original=subprocess.check_output(['git','-C',str(Path(__file__).resolve().parents[1]),'show',commit+':tools/'+name])
        require((package/'tools'/name).read_bytes()==original,'Exact native-runtime helper Git blob differs: '+name)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--package',type=Path,required=True);parser.add_argument('--commit',required=True);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    package=a.package.resolve();a.out.parent.mkdir(parents=True,exist_ok=True);require(not a.out.exists(), 'Validation failed: check_package.py:7')
    manifest=json.loads((package/'BUILD-MANIFEST.json').read_text());require(manifest['sourceCommit']==a.commit, 'Validation failed: check_package.py:8')
    checks=[];expected=set()
    for record in manifest['files']:
        relative=PurePosixPath(record['path']);require(not relative.is_absolute() and '..' not in relative.parts, 'Validation failed: check_package.py:11')
        require(record['path'] not in expected, 'Validation failed: check_package.py:12');expected.add(record['path']);file=package/relative
        require(file.is_file() and not file.is_symlink() and file.stat().st_size==record['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==record['sha256'], 'Validation failed: check_package.py:13')
    require({f.relative_to(package).as_posix() for f in package.rglob('*') if f.is_file()}==expected|{'BUILD-MANIFEST.json'}, 'Validation failed: check_package.py:14');checks.append('exact-manifest-file-set-and-sha256')
    external_helpers={
        'tools/build_etcd_fixture.py','tools/check_etcd_fixture.py','tools/bounded_fixture.py',
        'tools/test_etcd_fixture.py','tools/test_etcd_inputs.py','tools/test_fixture_resources.py',
        'tools/etcd_inputs.py','tools/profile_limits.py','tools/wsl_host_entry.py','tools/test_profile_limits.py','tools/etcd-build.inputs.json','tools/etcd-build.lock.json','docs/ETCD-FIXTURE-BUILD.md',
        'vendor/notices/ETCD-FIXTURE-SOURCES.json','tools/build_actionlint.py',
        'tools/check_actionlint.py','tools/run_actionlint.py','tools/bounded_actionlint.py',
        'tools/test_actionlint_admission.py','tools/actionlint-build.lock.json',
        'tools/actionlint-notices.json','docs/ACTIONLINT-BUILD.md'}
    external_helpers |= {'vendor/etcd-admission/'+name for name in ('source-audit.jsonl','binary-audit.jsonl','module-graph.json','licenses.json','buildinfo.json','reproducibility.json','advisory-snapshot.json')}
    require(external_helpers <= expected, 'External build/admission helpers missing from actual package')
    fixture=json.loads((package/'tools/etcd-build.lock.json').read_text(encoding='utf-8-sig'))
    tooling=json.loads((package/'tools/actionlint-build.lock.json').read_text(encoding='utf-8-sig'))
    require(fixture.get('status')=='ADMITTED_MAINTAINER_BUILD' and
            tooling.get('admission',{}).get('state')=='ADMITTED',
            'Unadmitted fixture/tooling source is not a complete local candidate')
    checks.append('complete-external-reproduction-helpers-and-admitted-reference-states')
    verify_profile_helpers(package,a.commit)
    checks.append('independent-exact-git-blob-binding-of-six-runtime-profile-helpers')
    require('MIT License' in (package/'LICENSE').read_text(), 'Validation failed: check_package.py:15');require((package/'licenses').is_dir(), 'Validation failed: check_package.py:15');checks.append('original-and-third-party-notices')
    dependencies=json.loads((package/'DEPENDENCIES.json').read_text(encoding='utf-8'))['packages']
    require(manifest['rid'] in ('win-x64','linux-x64'), 'Supported native RID required')
    runtime_id='Microsoft.NETCore.App.Runtime.'+manifest['rid']
    runtime=[d for d in dependencies if d['id'].startswith('Microsoft.NETCore.App.Runtime.')]
    require(len(runtime)==1 and runtime[0]['id']==runtime_id and runtime[0]['version']=='10.0.15',
            'Exact serviced Core runtime/RID required')
    runtimeconfig=json.loads((package/'ownership.runtimeconfig.json').read_text(encoding='utf-8'))
    options=runtimeconfig['runtimeOptions']
    require(options.get('tfm')=='net10.0' and options.get('includedFrameworks')==
            [{'name':'Microsoft.NETCore.App','version':'10.0.15'}],
            'Self-contained runtimeconfig must record Core10.0.15')
    shipped=json.loads((package/'ownership.deps.json').read_text(encoding='utf-8'))['libraries']
    runtimepacks={name.removeprefix('runtimepack.') for name,entry in shipped.items()
                  if entry['type']=='runtimepack' or name.startswith('runtimepack.')}
    require(runtimepacks=={runtime_id+'/10.0.15'}, 'Shipped runtimepack identity mismatch')
    checks.append('actual-self-contained-core-runtime-10.0.15-and-native-rid')
    for dep in dependencies:
        relative=PurePosixPath(dep['licenseFile']);require(not relative.is_absolute() and '..' not in relative.parts, 'Validation failed: check_package.py:18')
        license_file=package/relative;require(license_file.stat().st_size>=300 and hashlib.sha256(license_file.read_bytes()).hexdigest()==dep['licenseSha256'] and dep['copyright'], 'Validation failed: check_package.py:19')
        if 'copyrightFile' in dep:
            copyright_path=PurePosixPath(dep['copyrightFile']);require(not copyright_path.is_absolute() and '..' not in copyright_path.parts, 'Validation failed: check_package.py:21')
            require((package/copyright_path).read_text(encoding='utf-8').strip()==dep['copyright'], 'Validation failed: check_package.py:22')
    checks.append('every-shipped-component-full-license-and-copyright')
    sbom=json.loads((package/'SBOM.spdx.json').read_text());require(sbom['spdxVersion']=='SPDX-2.3' and sbom['packages'], 'Validation failed: check_package.py:24');checks.append('resolved-shipped-sbom-present')
    components={c['name']+'/'+c['versionInfo']:c for c in sbom['packages'] if c['SPDXID']!='SPDXRef-App'}
    require(set(components)=={d['id']+'/'+d['version'] for d in dependencies},'SBOM graph mismatch')
    for dep in dependencies:
        require(len(dep['rawSignedNupkgSha512'])==128 and components[dep['id']+'/'+dep['version']]['checksums']==[{'algorithm':'SHA512','checksumValue':dep['rawSignedNupkgSha512']}],'Raw archive checksum relationship')
    checks.append('raw-signed-archive-checksum-distinct-from-normalized-restore-identity')
    app=package/('ownership.exe' if platform.system()=='Windows' else 'ownership');require(app.is_file(), 'Validation failed: check_package.py:25')
    environment=os.environ.copy();environment.pop('OWNERSHIP_LAB_TELEMETRY',None)
    def call(args,code):
        process=subprocess.run([str(app),*args],env=environment,capture_output=True,text=True,timeout=20);require(process.returncode==code, (args,process.returncode,process.stdout,process.stderr));return process.stdout
    require('Synthetic literal-loopback only' in call(['--help'],0), 'Validation failed: check_package.py:29');checks.append('actual-native-apphost-help')
    version=json.loads(call(['--version'],0));require(a.commit in version['version'], 'Validation failed: check_package.py:30');checks.append('actual-apphost-exact-source-version')
    invalid=json.loads(call(['acquire','http://example.com:2379/','worker', '3'],2));require(invalid['code']=='LITERAL_LOOPBACK_ENDPOINT_REQUIRED', 'Validation failed: check_package.py:31');checks.append('external-endpoint-rejected-before-network')
    receipt={'status':'PASS','sourceCommit':a.commit,'rid':manifest['rid'],'os':platform.system(),'checks':checks,'checkCount':len(checks),'filesVerified':len(expected)}
    a.out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()
