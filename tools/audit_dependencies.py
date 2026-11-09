"""Record the current NuGet advisory check; not a security certification."""
import argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dotnet',default='dotnet');p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists();a.out.parent.mkdir(parents=True,exist_ok=True)
    reports=[]
    for project in ['src/Ownership.Cli/Ownership.Cli.csproj','tests/Ownership.Tests/Ownership.Tests.csproj']:
        result=subprocess.run([a.dotnet,'package','list','--project',project,'--vulnerable','--include-transitive','--no-restore','--format','json'],cwd=ROOT,capture_output=True,text=True,check=True,timeout=180)
        data=json.loads(result.stdout);assert data.get('version')==1 and len(data.get('projects',[]))==1 and data.get('sources')
        def inspect(value):
            if isinstance(value,dict):
                for key,item in value.items():
                    if key in ['vulnerabilities','errors','problems','logs']:assert not item,(key,item)
                    inspect(item)
            elif isinstance(value,list):
                for item in value:inspect(item)
        inspect(data);reports.append(data)
    receipt={'status':'NO_KNOWN_ADVISORIES_REPORTED','scope':'Current NuGet source advisory query for locked direct/transitive application and test graph; not general vulnerability absence','reports':reports}
    a.out.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8');print(json.dumps({'status':receipt['status'],'projects':len(reports)}))

if __name__=='__main__':main()
