"""Own a fresh, loopback-only Linux fixture. No system service or package install.

The controller mailbox accepts only named operations on this process's own
children. Keep the private output directory out of Git and release archives.
"""
import argparse,json,os,secrets,socket,subprocess,tempfile,time,urllib.request
from pathlib import Path

def port(used):
    while True:
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));value=sock.getsockname()[1]
        if value not in used:used.add(value);return value

def publish(path,data):
    temp=path.with_suffix('.partial');temp.write_text(json.dumps(data,indent=2)+'\n');os.replace(temp,path)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixtures',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args()
    if os.name!='posix' or os.getuid()==0:raise SystemExit('Existing non-root Linux user required')
    root=a.fixtures.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    scratch=Path(tempfile.mkdtemp(prefix='portfolio-ownership-'));os.chmod(scratch,0o700)
    pg=root/'root/usr/lib/postgresql/18/bin';etcd=root/'etcd-v3.7.3-linux-amd64/etcd'
    env=os.environ.copy();env['LD_LIBRARY_PATH']=str(root/'root/usr/lib/x86_64-linux-gnu');env['GOMAXPROCS']='1'
    password=secrets.token_hex(24);admin=secrets.token_hex(24);run=secrets.token_hex(12)
    private=scratch/'admin-password';private.write_text(admin);os.chmod(private,0o600)
    used=set();pgport=port(used);clients=[port(used) for _ in range(3)];peers=[port(used) for _ in range(3)]
    logs=[];members=[];started=time.monotonic();pg_started=False
    def command(args,extra=None,timeout=30):
        local=env.copy();local.update(extra or {})
        result=subprocess.run([str(x) for x in args],env=local,capture_output=True,text=True,timeout=timeout)
        if result.returncode:raise RuntimeError('Fixture command failed: '+Path(str(args[0])).name+'; '+result.stderr[-1500:].replace(admin,'[redacted]').replace(password,'[redacted]'))
        return result.stdout
    def sql(text,database='postgres'):
        return command([pg/'psql','-X','-A','-t','-v','ON_ERROR_STOP=1','-h','127.0.0.1','-p',pgport,'-U','lab_admin','-d',database,'-c',text],{'PGPASSWORD':admin})
    def start_member(index):
        log=(out/f'etcd-{index}-{time.monotonic_ns()}.log').open('wb');logs.append(log)
        cluster=','.join(f'm{j}=http://127.0.0.1:{peers[j]}' for j in range(3))
        args=[str(etcd),'--name',f'm{index}','--data-dir',str(scratch/f'etcd-{index}'),
              '--listen-client-urls',f'http://127.0.0.1:{clients[index]}','--advertise-client-urls',f'http://127.0.0.1:{clients[index]}',
              '--listen-peer-urls',f'http://127.0.0.1:{peers[index]}','--initial-advertise-peer-urls',f'http://127.0.0.1:{peers[index]}',
              '--initial-cluster',cluster,'--initial-cluster-token',run,'--initial-cluster-state','new',
              '--quota-backend-bytes','67108864','--max-wals','2','--max-snapshots','2','--log-level','error']
        process=subprocess.Popen(args,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        if len(members)<=index:members.append(process)
        else:members[index]=process
    def stop_member(index):
        process=members[index]
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=8)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
    def ready():
        until=time.monotonic()+120
        while time.monotonic()<until:
            try:
                for value in clients:
                    with urllib.request.urlopen(f'http://127.0.0.1:{value}/health',timeout=.5) as response:
                        if json.loads(response.read(8192)).get('health')!='true':raise ValueError('not healthy')
                return
            except (OSError,ValueError):time.sleep(.1)
        raise TimeoutError('Owned cluster readiness failed')
    def start_pg():
        nonlocal pg_started
        options=f'-h 127.0.0.1 -p {pgport} -k {scratch} -c shared_buffers=64MB -c max_connections=16 -c max_wal_size=256MB -c jit=off'
        command([pg/'pg_ctl','-D',scratch/'pg','-l',out/'postgres.log','-o',options,'-w','-t','30','start'],timeout=35);pg_started=True
    def stop_pg():
        nonlocal pg_started
        if pg_started:
            command([pg/'pg_ctl','-D',scratch/'pg','-w','-t','15','-m','fast','stop'],timeout=20);pg_started=False
    try:
        command([pg/'initdb','-D',scratch/'pg','--username=lab_admin','--auth-host=scram-sha-256','--auth-local=peer','--pwfile',private,'--no-locale','--encoding=UTF8'],timeout=60)
        start_pg();sql("CREATE ROLE ownership_lab LOGIN PASSWORD '"+password+"'");sql('CREATE DATABASE ownership_lab OWNER ownership_lab')
        for i in range(3):start_member(i)
        ready()
        publish(out/'connection.private.json',{'run':run,'connection':f'Host=127.0.0.1;Port={pgport};Username=ownership_lab;Password={password};Database=ownership_lab','endpoints':[f'http://127.0.0.1:{x}/' for x in clients]})
        os.chmod(out/'connection.private.json',0o600)
        publish(out/'ready.json',{'status':'READY_OWNED_LOCAL_FIXTURES','run':run,'pgPort':pgport,'etcdClientPorts':clients,'scratch':str(scratch),'pid':os.getpid(),'physicalFaultDomains':1})
        print(json.dumps({'status':'READY','out':str(out)}),flush=True)
        while time.monotonic()-started<15*60:
            if sum(p.stat().st_size for p in out.glob('*.log'))>256*1024*1024:raise RuntimeError('Log cap exceeded')
            request=out/'control.json'
            if not request.exists():time.sleep(.05);continue
            message=json.loads(request.read_text());request.unlink()
            action=message['action'];identity=message['id']
            if not isinstance(identity,str) or not identity.isascii() or not identity.isalnum() or len(identity)>64:raise ValueError('Invalid mailbox identity')
            response={'id':identity,'action':action,'status':'OK'}
            if action=='stop-quorum':stop_member(1);stop_member(2)
            elif action=='start-quorum':start_member(1);start_member(2);ready()
            elif action=='stop-sink':stop_pg()
            elif action=='start-sink':start_pg()
            elif action=='restart-sink':stop_pg();start_pg()
            elif action=='oracle':
                response['state']=json.loads(sql("SELECT row_to_json(s) FROM ownership_lab_v1.state s",'ownership_lab').strip() or 'null')
                response['effects']=json.loads(sql("SELECT COALESCE(json_agg(e ORDER BY e.operation_id),'[]'::json) FROM ownership_lab_v1.effects e",'ownership_lab').strip())
            elif action=='shutdown':publish(out/(identity+'.json'),response);break
            else:raise ValueError('Unsupported owned fixture action')
            publish(out/(identity+'.json'),response)
        else:raise TimeoutError('Bounded fixture profile expired')
    except Exception as error:
        publish(out/'host-error.json',{'status':'FAILED','type':type(error).__name__,'detail':str(error)[:1800]});raise
    finally:
        for i in range(len(members)):stop_member(i)
        try:stop_pg()
        finally:
            for log in logs:log.close()
            publish(out/'stopped.json',{'status':'OWNED_PROCESSES_STOPPED','scratchRetained':str(scratch),'durationSeconds':round(time.monotonic()-started,3)})

if __name__=='__main__':main()
