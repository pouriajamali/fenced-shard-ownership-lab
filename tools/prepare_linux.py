"""Extract verified fixtures into a NEW local directory; never install a package."""
import argparse,hashlib,json,os,platform,shutil,subprocess,tarfile
from pathlib import Path
from check_etcd_fixture import admitted_etcd, identity, reference
from bounded_fixture import canonical, kernel_limits

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--archives',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--etcd-bundle',type=Path);parser.add_argument('--build-work',type=Path);a=parser.parse_args()
    if platform.system()!='Linux':raise SystemExit('Run this step in existing Ubuntu24.04/Linux, including WSL.')
    frozen=reference()  # No old archive/version execution before independent admission.
    kernel_limits()
    out=canonical(a.out.absolute(),exists=False)
    if a.etcd_bundle:
        bundle=canonical(a.etcd_bundle.absolute())
        with admitted_etcd(bundle): pass
    else:
        from etcd_inputs import reproduce
        bundle=out.parent/(out.name+'-etcd')
        work=a.build_work.absolute() if a.build_work else out.parent/(out.name+'-etcd-rebuild')
        reproduce(canonical(a.archives.absolute()),bundle,work,frozen)
    out.mkdir(parents=True,exist_ok=False)
    (out/'etcd-source-go1.26.11').mkdir()
    source=bundle/'etcd-source-go1.26.11/etcd'
    with source.open('rb') as incoming,(out/'etcd-source-go1.26.11/etcd').open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing,65536)
    os.chmod(out/'etcd-source-go1.26.11/etcd',0o755)
    for name in frozen['proofs']:
        source=canonical(bundle/name);destination=out/name;destination.parent.mkdir(parents=True,exist_ok=True)
        with source.open('rb') as incoming,destination.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing,65536)
    with (out/'ETCD-BUILD.json').open('xb') as output:output.write((bundle/'ETCD-BUILD.json').read_bytes())
    identity(out,frozen)
    lock=json.loads(Path(__file__).with_name('upstream.lock.json').read_text())
    root=out/'root';root.mkdir()
    for record in lock['files']:
        file=a.archives/record['name']
        if hashlib.sha256(file.read_bytes()).hexdigest()!=record['sha256']:raise ValueError('Fixture digest changed')
        if file.name.endswith('.deb'):subprocess.run(['dpkg-deb','--extract',str(file),str(root)],check=True,timeout=60)
        else:
            with tarfile.open(file,'r:gz') as archive:archive.extractall(out,filter='data')
    env=os.environ.copy();env['LD_LIBRARY_PATH']=str(root/'usr/lib/x86_64-linux-gnu')
    postgres=root/'usr/lib/postgresql/18/bin/postgres'
    dependencies=subprocess.run(['ldd',str(postgres)],env=env,text=True,capture_output=True,check=True)
    missing=[line.strip() for line in dependencies.stdout.splitlines() if 'not found' in line]
    if missing:raise SystemExit('Required existing Linux libraries missing: '+','.join(missing))
    with admitted_etcd(out) as admitted:
        result=subprocess.run([admitted['executable'],'--version'],pass_fds=admitted['pass_fds'],env=env,text=True,capture_output=True,check=True,timeout=10);print(result.stdout.strip())
    for command in [[str(postgres),'--version']]:
        result=subprocess.run(command,env=env,text=True,capture_output=True,check=True,timeout=10);print(result.stdout.strip())
    (out/'PREPARED.json').write_text(json.dumps({'status':'EXTRACTED_NOT_INSTALLED','root':str(out),'platform':platform.platform(),'upstream':lock},indent=2)+'\n')

if __name__=='__main__':main()
