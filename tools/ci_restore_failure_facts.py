"""Finite safe first-restore facts; no raw paths, console or causal attribution."""
import json,os,re,stat
from pathlib import Path
KNOWN_CODES=frozenset(('NU1101','NU1301','NU1605','NU1900','NETSDK1004','NETSDK1045','MSB1009','MSB4019'))
FIXED_TEMPLATES={"Value cannot be null. (Parameter 'path1')":'ARGUMENT_NULL_PATH1_OBSERVED'}
LOG_MAX=1048576
PROCESS_MAX=131072
FACT_KEYS=frozenset(('schema','stage','commandIndex','intExitCode','classification','codes','fixedFacts','scanState','rootCause','rawConsoleIncluded'))

def checked_info(path,want_file):
 # lstat each component; never resolve/admit a symlink/reparse ancestor.
 if not path.is_absolute() or '..' in path.parts:return None
 for index,node in enumerate((path,*path.parents)):
  info=node.lstat()
  if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:return None
  if index==0 and want_file:
   if not stat.S_ISREG(info.st_mode):return None
  elif not stat.S_ISDIR(info.st_mode):return None
 return path.lstat()

def limited_read(path,limit):
 before=checked_info(path,True)
 if before is None:return None,'MISSING_OR_UNSAFE'
 if before.st_size>limit:return None,'CAP_REACHED'
 with path.open('rb') as source:
  opened=os.fstat(source.fileno())
  if not stat.S_ISREG(opened.st_mode) or (opened.st_dev,opened.st_ino)!=(before.st_dev,before.st_ino):return None,'MISSING_OR_UNSAFE'
  data=source.read(limit+1)
 if checked_info(path,True) is None:return None,'MISSING_OR_UNSAFE'
 if len(data)>limit:return None,'CAP_REACHED'
 return data,'COMPLETE'

def facts(folder):
 value=dict(schema='ci06-first-restore-safe-facts/v2',stage='verify',commandIndex=1,classification='UNCLASSIFIED',codes=[],fixedFacts=[],scanState='MISSING_OR_UNSAFE',rootCause='UNKNOWN',rawConsoleIncluded=False)
 try:
  folder=Path(folder)
  if checked_info(folder,False) is None:return value
  job=folder/'job'
  try:job.lstat();job_exists=True
  except FileNotFoundError:job_exists=False
  base=job if job_exists else folder
  if checked_info(base,False) is None:return value
  raw,state=limited_read(base/'process.json',PROCESS_MAX)
  if raw is None:value['scanState']=state;return value
  record=json.loads(raw)
  if type(record) is not dict:return value
  exit_code=record.get('exitCode')
  if type(exit_code) is not int or not -2147483648<=exit_code<=4294967295:return value
  value['intExitCode']=exit_code;codes=set();fixed=set()
  for name in ('stdout.log','stderr.log'):
   data,state=limited_read(base/name,LOG_MAX)
   if data is None:value['scanState']=state;return value
   text=data.decode('utf-8',errors='replace')
   for code in re.findall(r'(?:^|\s)(?:error|warning)\s+((?:NU|NETSDK|MSB)[0-9]{4})\s*:',text,re.IGNORECASE|re.MULTILINE):
    if code.upper() in KNOWN_CODES:codes.add(code.upper())
   for literal,identifier in FIXED_TEMPLATES.items():
    if re.search(r'(?:^|\s)error\s*:\s*'+re.escape(literal)+r'(?:\s|$)',text,re.MULTILINE):fixed.add(identifier)
  value.update(scanState='COMPLETE',codes=sorted(codes),fixedFacts=sorted(fixed))
  if codes or fixed:value['classification']='KNOWN_DIAGNOSTIC_FACT_OBSERVED'
 except (OSError,ValueError,TypeError,UnicodeError):pass
 return value

def write_facts(folder,out):
 value=facts(folder);payload=(json.dumps(value,ensure_ascii=True,sort_keys=True)+'\n').encode('ascii')
 if set(value)-FACT_KEYS or len(payload)>4096:raise RuntimeError('HOLD_SAFE_RESTORE_FACTS_SCHEMA')
 with Path(out).open('xb') as target:target.write(payload);target.flush();os.fsync(target.fileno())
 return value

if __name__=='__main__':raise SystemExit('Library only; no raw-console CLI')
