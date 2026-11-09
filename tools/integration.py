"""Run the bounded fault demo and independent SQL-history oracle.

Windows uses an EXISTING Ubuntu-24.04 WSL instance for Linux services.
The CLI itself executes natively on the calling OS. No package or OS install.
"""
import argparse,concurrent.futures,hashlib,json,os,platform,subprocess,sys,time
from pathlib import Path

def linux_path(path):
    path=Path(path).resolve()
    if os.name!='nt':return str(path)
    if len(path.drive)!=2 or path.drive[1]!=':':raise ValueError('Local drive required for WSL fixture')
    return '/mnt/'+path.drive[0].lower()+'/'+path.as_posix()[3:]

def atomic(path,data):
    temp=path.with_suffix('.partial');temp.write_text(json.dumps(data)+'\n',encoding='utf-8');os.replace(temp,path)

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--fixtures',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--cli',type=Path,required=True);parser.add_argument('--dotnet',type=Path);a=parser.parse_args()
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);hostdir=out/'host'
    hostscript=Path(__file__).with_name('linux_host.py').resolve()
    hostargs=['python3',linux_path(hostscript),'--fixtures',linux_path(a.fixtures),'--out',linux_path(hostdir)]
    if os.name=='nt':hostargs=['wsl','-d','Ubuntu-24.04','--']+hostargs
    hostlog=(out/'host-console.log').open('wb');host=subprocess.Popen(hostargs,stdout=hostlog,stderr=subprocess.STDOUT)
    own_children=[];history=[];checks=[];expected={};counter=0;started=time.monotonic();configuration=None
    cli=([str(a.dotnet.resolve())] if a.dotnet else [])+[str(a.cli.resolve())]
    def wait_file(path,timeout=120):
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            if path.exists():return
            if (hostdir/'host-error.json').exists():raise RuntimeError('Owned host failed; inspect sanitized host-error.json')
            if host.poll() is not None:raise RuntimeError('Owned Linux host exited before requested fixture result')
            time.sleep(.025)
        raise TimeoutError('Bounded fixture wait: '+path.name)
    def env(extra=None):
        values=os.environ.copy();values['OWNERSHIP_LAB_DB']=configuration['connection'];values['DOTNET_PROCESSOR_COUNT']='1';values.update(extra or {});return values
    def call(*args,allowed=(0,),extra=None):
        process=subprocess.run(cli+list(map(str,args)),env=env(extra),capture_output=True,text=True,timeout=25)
        try:reply=json.loads(process.stdout)
        except json.JSONDecodeError:raise RuntimeError('CLI did not produce one JSON response; code='+str(process.returncode))
        history.append({'arguments':list(args),'exitCode':process.returncode,'reply':reply})
        if process.returncode not in allowed:raise AssertionError('CLI failed: '+str(args[0])+' '+json.dumps(reply))
        return reply
    def control(action):
        nonlocal counter
        counter+=1;identity='c'+str(counter);atomic(hostdir/'control.json',{'id':identity,'action':action});file=hostdir/(identity+'.json');wait_file(file);return json.loads(file.read_text())
    def mark(name):checks.append(name);print('PASS '+name,flush=True)
    def identity(owner):return [owner[k] for k in ['owner','clusterId','fence','leaseId','ttl']]
    def acquire(name,ttl=3):
        until=time.monotonic()+20
        while time.monotonic()<until:
            reply=call('acquire',configuration['endpoints'][0],name,ttl,allowed=(0,3))
            if 'fence' in reply:return reply
            time.sleep(.1)
        raise TimeoutError('Competing acquisition never completed')
    def apply(owner,name,delta,status):
        result=call('apply',configuration['run'],*identity(owner),name,delta,allowed=(0,4))
        assert result['status']==status,(status,result)
        if status=='APPLIED':expected[name]=delta
        return result
    def oracle(owner):
        observed=control('oracle');state=observed['state'];effects=observed['effects']
        actual={e['operation_id']:int(e['delta']) for e in effects}
        assert len(actual)==len(effects) and actual==expected,(actual,expected)
        assert int(state['total'])==sum(actual.values())==sum(expected.values())
        assert int(state['fence'])==int(owner['fence']) and state['owner']==owner['owner']
        assert state['cluster_id']==owner['clusterId'] and state['run_id']==configuration['run']
        for effect in effects:
            digest=hashlib.sha256(('effect-v1\nsynthetic-shard\n'+effect['operation_id']+'\n'+str(effect['delta'])+'\n').encode()).hexdigest()
            assert effect['request_hash']==digest
            receipt=json.loads(effect['receipt']);assert receipt['operationId']==effect['operation_id'] and int(receipt['delta'])==effect['delta']
        history.append({'independentSqlOracle':{'fence':state['fence'],'owner':state['owner'],'total':state['total'],'uniqueEffects':len(effects)}})
    def paused(action,owner,stage,name=None,delta=None):
        folder=out/('pause-'+str(len(own_children)));folder.mkdir();args=[action,configuration['run'],*identity(owner)]
        if name is not None:args += [name,delta]
        extra={'OWNERSHIP_LAB_PAUSE':('activation' if action=='activate' else 'effect')+':'+stage,'OWNERSHIP_LAB_HOOK_DIR':str(folder)}
        process=subprocess.Popen(cli+list(map(str,args)),env=env(extra),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);own_children.append(process)
        wait_file(folder/'ready',20);return process,folder
    def kill(process):
        if process.poll() is None:process.kill()
        process.communicate(timeout=10)
    try:
        wait_file(hostdir/'ready.json');configuration=json.loads((hostdir/'connection.private.json').read_text())
        version=call('--version');run=configuration['run'];endpoint=configuration['endpoints'][0]
        assert call('init',run)['status']=='INITIALIZED_FRESH'
        owner_a=acquire('worker-a',10);assert call('renew',endpoint,*identity(owner_a))['status']=='RENEWED'
        denied=call('acquire',endpoint,'competing-worker',3,allowed=(3,));assert denied['status']=='ACQUISITION_DENIED'
        assert call('activate',run,*identity(owner_a))['status']=='ACTIVATED';mark('real-acquisition-renewal-and-competition')
        original=apply(owner_a,'original',17,'APPLIED')['receipt'];assert apply(owner_a,'original',17,'REPLAYED')['receipt']==original
        apply(owner_a,'original',18,'IDENTITY_CONFLICT');oracle(owner_a);mark('same-identity-replay-and-conflict')
        old,folder=paused('apply',owner_a,'BeforeLock','delayed-old',101)
        owner_b=acquire('worker-b');assert int(owner_b['fence'])>int(owner_a['fence'])
        assert call('activate',run,*identity(owner_b))['status']=='ACTIVATED'
        (folder/'continue').write_text('continue');stdout,_=old.communicate(timeout=20)
        assert old.returncode==0 and json.loads(stdout)['status']=='STALE_FENCE'
        apply(owner_a,'late-old',103,'STALE_FENCE');oracle(owner_b);mark('paused-inflight-application-rejected-after-cutover')
        assert apply(owner_b,'original',17,'REPLAYED')['receipt']==original;oracle(owner_b);mark('idempotency-survives-new-generation')
        def concurrent_apply(_):return call('apply',run,*identity(owner_b),'concurrent',23)['status']
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:statuses=list(executor.map(concurrent_apply,range(4)))
        assert statuses.count('APPLIED')==1 and statuses.count('REPLAYED')==3;expected['concurrent']=23
        oracle(owner_b);mark('concurrent-same-identity-single-effect')
        owner_c=acquire('worker-c');process,_=paused('activate',owner_c,'BeforeCommit');oracle(owner_b)
        kill(process);oracle(owner_b);assert call('activate',run,*identity(owner_c))['status']=='ACTIVATED';oracle(owner_c);mark('activation-crash-before-commit')
        owner_d=acquire('worker-d');process,_=paused('activate',owner_d,'AfterCommit');oracle(owner_d)
        apply(owner_c,'after-cutover',107,'STALE_FENCE');kill(process)
        assert call('activate',run,*identity(owner_d))['status']=='ACTIVATED';oracle(owner_d);mark('activation-commit-before-ack')
        process,_=paused('apply',owner_d,'BeforeCommit','before-commit',31);oracle(owner_d);kill(process)
        assert call('lookup',run,'before-commit',31) is None
        apply(owner_d,'before-commit',31,'APPLIED');oracle(owner_d);mark('effect-crash-before-commit-resolved-by-same-identity')
        process,_=paused('apply',owner_d,'AfterCommit','after-commit',41);expected['after-commit']=41;oracle(owner_d);kill(process)
        stored=call('lookup',run,'after-commit',41);assert stored is not None
        assert apply(owner_d,'after-commit',41,'REPLAYED')['receipt']==stored;oracle(owner_d);mark('effect-commit-before-ack-unknown-resolved')
        wrong=dict(owner_d);wrong['clusterId']='1' if owner_d['clusterId']!='1' else '2'
        assert call('activate',run,*identity(wrong))['status']=='LINEAGE_MISMATCH'
        assert call('activate','wrong-run',*identity(owner_d))['status']=='LINEAGE_MISMATCH'
        assert call('apply',run,*identity(owner_d),'invalid-delta',0,allowed=(2,))['status']=='ERROR';oracle(owner_d);mark('lineage-and-domain-rejections-have-no-effects')
        control('restart-sink');oracle(owner_d);apply(owner_a,'old-after-restart',109,'STALE_FENCE')
        assert apply(owner_d,'after-commit',41,'REPLAYED')['receipt']==stored;oracle(owner_d);mark('ordinary-sink-restart-retains-fence-and-dedup')
        control('stop-sink');assert call('apply',run,*identity(owner_d),'unavailable',53,allowed=(4,))['status']=='UNKNOWN'
        control('start-sink');assert call('lookup',run,'unavailable',53) is None
        apply(owner_d,'unavailable',53,'APPLIED');oracle(owner_d);mark('unavailable-sink-outcome-resolved-without-new-identity')
        control('stop-quorum');failed=call('acquire',endpoint,'no-quorum',3,allowed=(2,));assert failed['status']=='ERROR'
        oracle(owner_d);control('start-quorum');mark('real-two-of-three-quorum-loss-denies-new-acquisition')
        owner_e=acquire('worker-e');assert owner_e['clusterId']==owner_d['clusterId']
        assert call('activate',run,*identity(owner_e))['status']=='ACTIVATED'
        apply(owner_d,'late-after-quorum',113,'STALE_FENCE');assert apply(owner_e,'original',17,'REPLAYED')['receipt']==original
        oracle(owner_e);mark('recovered-quorum-preserves-lineage-and-forward-only-cutover')
        telemetry=subprocess.run(cli+list(map(str,['apply',run,*identity(owner_e),'original',17])),env=env({'OWNERSHIP_LAB_TELEMETRY':'1'}),capture_output=True,text=True,timeout=25)
        assert telemetry.returncode==0 and json.loads(telemetry.stdout)['status']=='REPLAYED'
        trace=json.loads(telemetry.stderr);assert trace['signal']=='trace' and trace['operation']=='ownership.apply' and trace['status']=='Ok'
        assert 'Password' not in telemetry.stderr and configuration['connection'].split('Password=')[1].split(';')[0] not in telemetry.stderr
        oracle(owner_e);mark('stable-otel-trace-redacted-and-business-result-preserved')
        receipt={'schema':1,'status':'PASS','clientOs':platform.system(),'clientArchitecture':platform.machine(),'version':version,'cases':checks,'caseCount':len(checks),'independentSqlOracle':True,'effectCount':len(expected),'total':sum(expected.values()),'durationSeconds':round(time.monotonic()-started,3),'history':history,'limits':['Single physical host; local synthetic fixtures only','BeforeLock is an application pause, not packet-delay measurement','Graceful sink restart; arbitrary storage restore/rollback unsupported','No production HA, exactly-once network delivery, orders or latency claim']}
        atomic(out/'receipt.json',receipt);print(json.dumps({k:receipt[k] for k in ['status','clientOs','caseCount','effectCount','total','durationSeconds']}))
    except Exception as error:
        atomic(out/'failure.json',{'status':'FAIL','type':type(error).__name__,'detail':str(error)[:1200],'completedCases':checks,'history':history});raise
    finally:
        for process in own_children:
            if process.poll() is None:kill(process)
        if configuration is not None and host.poll() is None:
            try:control('shutdown')
            except (OSError,ValueError,RuntimeError,TimeoutError):host.terminate()
        try:host.wait(timeout=35)
        except subprocess.TimeoutExpired:host.terminate();host.wait(timeout=10)
        hostlog.close()

if __name__=='__main__':main()
