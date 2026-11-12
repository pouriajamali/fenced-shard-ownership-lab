"""Internal owned WSL host-unit entry/stop; no install, config or SDK probes."""
import argparse,json,os,re,stat,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bounded_fixture import canonical,require

def write(path,data):
 temporary=path.with_suffix('.partial');temporary.write_text(json.dumps(data,indent=2)+'\n');os.replace(temporary,path)

def environment():
 uid=os.getuid();require(uid!=0,'NON_ROOT_PROFILE');return {'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','TMPDIR':'/tmp','XDG_RUNTIME_DIR':'/run/user/'+str(uid),'DBUS_SESSION_BUS_ADDRESS':'unix:path=/run/user/'+str(uid)+'/bus'}

def ready(env):
 deadline=time.monotonic()+20
 while time.monotonic()<deadline:
  bus=Path(env['XDG_RUNTIME_DIR'])/'bus'
  if bus.exists() and stat.S_ISSOCK(bus.lstat().st_mode) and bus.lstat().st_uid==os.getuid():
   try:
    p=subprocess.run(['/usr/bin/systemctl','--user','show','--property=Version','--value'],env=env,capture_output=True,timeout=min(3,max(.1,deadline-time.monotonic())))
    if p.returncode==0 and p.stdout.strip():return True
   except subprocess.TimeoutExpired:pass
  time.sleep(min(.25,max(0,deadline-time.monotonic())))
 return False

def group_for(unit):return Path('/sys/fs/cgroup/user.slice/user-'+str(os.getuid())+'.slice/user@'+str(os.getuid())+'.service/app.slice')/(unit+'.service')

def populated(unit):
 root=group_for(unit)
 if not root.exists():return 0
 events=dict(line.split() for line in (root/'cgroup.events').read_text().splitlines());require(events.get('populated') in ('0','1'),'ACTUAL_CGROUP_EVENTS');return int(events['populated'])

def main():
 p=argparse.ArgumentParser();p.add_argument('--unit',required=True);p.add_argument('--token',required=True);p.add_argument('--terminal',required=True,type=Path);p.add_argument('--fixtures',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--stop',action='store_true');a=p.parse_args()
 require(re.fullmatch(r'ownership(?:06|lab)-[a-z0-9-]{8,100}',a.unit) and re.fullmatch(r'[0-9a-f]{64}',a.token),'EXACT_OWN_UNIT_TOKEN');a.terminal=canonical(a.terminal.absolute());a.out=canonical(a.out.absolute(),exists=False);require(a.out.name=='host' and a.terminal.parent==a.out.parent.parent,'OWN_TERMINAL_PATH');old=json.loads(a.terminal.read_bytes());require(old.get('unit')==a.unit and old.get('token')==a.token,'OWN_CONTROLLER_TERMINAL');env=environment()
 def terminal(reason,code,started):write(a.terminal,dict(unit=a.unit,token=a.token,populated=populated(a.unit),terminal=populated(a.unit)==0,reason=reason,exitCode=code,targetStarted=started,bootId=Path('/proc/sys/kernel/random/boot_id').read_text().strip()))
 if a.stop:
  if populated(a.unit)==0:terminal('ACTUAL_NATIVE_GROUP_ALREADY_TERMINAL',0,True);return
  record=json.loads((a.out/'unit.json').read_bytes());require(record['unit']==a.unit and record['token']==a.token and record['group']==str(group_for(a.unit)),'EXACT_OWN_INVOCATION_RECORD')
  require(ready(env),'HOLD_EXISTING_USER_BUS_STOP_DEADLINE');identity=subprocess.run(['/usr/bin/systemctl','--user','show',a.unit,'--property=InvocationID','--value'],env=env,capture_output=True,text=True,timeout=5);require(identity.returncode==0 and identity.stdout.strip()==record['invocationId'],'OWN_ACTIVE_UNIT_INCARCATION')
  stopped=subprocess.run(['/usr/bin/systemctl','--user','stop',a.unit],env=env,timeout=30);require(stopped.returncode==0 and populated(a.unit)==0,'OWN_NATIVE_GROUP_STOP_REQUIRED');terminal('ACTUAL_OWN_INVOCATION_STOPPED',0,True);return
 require(populated(a.unit)==0,'EXISTING_UNIT_NO_START');require(not (a.out/'unit.json').exists(),'FRESH_PROFILE_ONLY')
 if not ready(env):terminal('HOLD_EXISTING_USER_BUS_DEADLINE',125,False);raise SystemExit(125)
 args=['/usr/bin/systemd-run','--user','--wait','--collect','--pipe','--quiet','--slice=app.slice','--unit='+a.unit,'--property=MemoryMax=3221225472','--property=MemorySwapMax=0','--property=CPUQuota=100%','--property=TasksMax=48','--property=RuntimeMaxSec=1080','--property=TimeoutStopSec=5','--property=KillMode=control-group','/usr/bin/python3','-I','-B',str(Path(__file__).with_name('linux_host.py')),'--fixtures',str(canonical(a.fixtures.absolute())),'--out',str(a.out),'--windows-client-unit',a.unit,'--profile-token',a.token]
 code=subprocess.run(args,env=env).returncode
 # --wait/--collect must be backed by actual kernel empty/removed cgroup state.
 terminal('ACTUAL_NATIVE_UNIT_TERMINAL' if populated(a.unit)==0 else 'HOLD_NATIVE_GROUP_NONTERMINAL',code,(a.out/'unit.json').exists());require(populated(a.unit)==0,'NATIVE_GROUP_TERMINAL_REQUIRED');raise SystemExit(code)
if __name__=='__main__':main()
