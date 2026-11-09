"""Bounded extraction into a NEW directory, preserving native Linux mode."""
import argparse,tarfile,zipfile
from pathlib import Path,PurePosixPath

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    def safe(name,size):
        path=PurePosixPath(name);assert not path.is_absolute() and '..' not in path.parts and ':' not in name and '\\' not in name and size<128*1024*1024
    if a.archive.suffix=='.zip':
        with zipfile.ZipFile(a.archive) as archive:
            infos=archive.infolist();assert len(infos)<1024 and sum(i.file_size for i in infos)<512*1024*1024
            assert len({i.filename for i in infos})==len(infos)
            for info in infos:safe(info.filename,info.file_size)
            archive.extractall(a.out)
    else:
        with tarfile.open(a.archive,'r:gz') as archive:
            infos=archive.getmembers();assert len(infos)<1024 and sum(i.size for i in infos)<512*1024*1024
            assert len({i.name for i in infos})==len(infos)
            for info in infos:assert info.isfile();safe(info.name,info.size)
            archive.extractall(a.out,filter='data')

if __name__=='__main__':main()
