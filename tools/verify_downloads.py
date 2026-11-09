"""Verify a pinned SSH checksum signature, then every present selected archive."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--work',type=Path,required=True);parser.add_argument('--trusted-fingerprint',required=True);parser.add_argument('--archive',required=True);a=parser.parse_args()
    directory=a.directory.resolve();work=a.work.resolve();work.mkdir(parents=True,exist_ok=False)
    assert Path(a.archive).name==a.archive and a.archive.endswith(('.zip','.tar.gz'))
    key=directory/'SIGNING-PUBLIC-KEY.pub';info=subprocess.check_output(['ssh-keygen','-lf',str(key)],text=True).strip().split()
    assert info[1]==a.trusted_fingerprint,'Fingerprint must match the independently trusted value exactly'
    allowed=work/'allowed-signers';allowed.write_text('pouriajamali '+key.read_text().strip()+'\n',encoding='utf-8',newline='\n')
    sums=directory/'SHA256SUMS.txt'
    subprocess.run(['ssh-keygen','-Y','verify','-f',str(allowed),'-I','pouriajamali','-n','file','-s',str(directory/'SHA256SUMS.txt.sig')],input=sums.read_bytes(),capture_output=True,check=True)
    entries={}
    for line in sums.read_text(encoding='utf-8').splitlines():
        match=re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9._-]+)',line);assert match,'Invalid checksum framing'
        digest,name=match.groups();assert name not in entries;entries[name]=digest
    assert a.archive in entries and (directory/a.archive).is_file(),'Explicit archive missing'
    verified=[]
    for name,digest in entries.items():
        path=directory/name
        if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==digest;verified.append(name)
    receipt={'status':'PINNED_SIGNATURE_AND_PRESENT_ARCHIVES_VERIFIED','fingerprint':a.trusted_fingerprint,'archives':verified,'requiredArchive':a.archive}
    (work/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()
