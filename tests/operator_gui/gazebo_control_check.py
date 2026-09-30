"""Real Gazebo-only HTTP/action/stop acceptance; never run against hardware."""
import json
from pathlib import Path
import time
import urllib.request
import urllib.error

base='http://127.0.0.1:8089';records=[]
def state():
    with urllib.request.urlopen(base+'/api/v1/state',timeout=3) as response:return json.load(response)
def wait(check,seconds=30):
    end=time.monotonic()+seconds
    value={'streams':{},'events':[]}
    while time.monotonic()<end:
        try:value=state()
        except urllib.error.URLError:
            time.sleep(.2);continue
        if check(value):return value
        time.sleep(.2)
    raise AssertionError('Condition timed out: '+json.dumps(value['streams'].get('task'))+' events '+json.dumps(value['events'][:3]))
def command(name):
    request=urllib.request.Request(base+'/api/v1/commands',data=json.dumps({'command':name}).encode(),
        headers={'Content-Type':'application/json','X-ATOM-Token':token})
    try:
        with urllib.request.urlopen(request,timeout=4) as response:result=json.load(response)
    except urllib.error.HTTPError as exc:
        print('Rejected',name,exc.read().decode());raise
    records.append({'command':name,'response':result});return result

initial=wait(lambda s:s['metadata']['profile']=='gazebo' and s['commands_enabled'] and s['streams'].get('safety',{}).get('value',{}).get('stop_confirmed'),60)
assert initial['metadata']['profile']=='gazebo' and initial['metadata']['use_sim_time']
assert initial['streams']['safety']['value']['source']=='gazebo'
assert not initial['available']['pick'] and not initial['available']['place'] and not initial['available']['navigate']
with urllib.request.urlopen(base+'/api/v1/session') as response:token=json.load(response)['token']
if not state()['stop_latched']:
    command('stop')
    wait(lambda s:s['streams']['controller']['value']['state']=='inactive' and s['streams']['safety']['value'].get('stop_confirmed') and not s['pending'])
command('reset_stop')
wait(lambda s:s['streams']['safety']['value'].get('motion_allowed') and not s['stop_latched'] and not s['pending'] and 'observe' not in s['command_blocks'])
request=command('observe')['request_id']
finished=wait(lambda s:s['streams'].get('task',{}).get('value',{}).get('request_id')==request and s['streams']['task']['value'].get('state') in ('SUCCEEDED','FAILED','REJECTED','STOPPED'),100)
assert finished['streams']['task']['value']['state']=='SUCCEEDED',finished['events'][:3]
records.append({'observation':finished})
wait(lambda s:'observe' not in s['command_blocks'])
positions=state()['streams']['arm']['value']['position']
request=command('observe')['request_id']
wait(lambda s:s['streams']['task']['value'].get('request_id')==request and s['streams']['task']['value'].get('state')=='EXECUTING')
moving=wait(lambda s:max(abs(a-b) for a,b in zip(s['streams']['arm']['value']['position'],positions))>.003,30)
command('stop')
stopped=wait(lambda s:s['streams']['controller']['value']['state']=='inactive' and s['streams']['safety']['value'].get('stop_confirmed'),12)
assert stopped['stop_latched']
try:command('observe');raise AssertionError('Motion allowed while latched')
except urllib.error.HTTPError as exc:assert exc.code==409
first=state();time.sleep(1);second=state()
max_delta=max(abs(a-b) for a,b in zip(first['streams']['arm']['value']['position'],second['streams']['arm']['value']['position']))
assert max_delta<.01,max_delta
records.append({'stopped':stopped,'standstill_interval_s':1,'max_joint_displacement_rad':max_delta})
wait(lambda s:not s['pending'])
command('reset_stop')
reset=wait(lambda s:not s['stop_latched'] and not s['pending'] and s['streams']['controller']['value']['state']=='active',12)
records.append({'reset':reset})
# Standard action cancellation must interrupt an in-flight task too.
wait(lambda s:'observe' not in s['command_blocks'])
request=command('observe')['request_id']
wait(lambda s:s['streams']['task']['value'].get('request_id')==request and s['streams']['task']['value'].get('state')=='EXECUTING')
command('cancel')
canceled=wait(lambda s:not s['pending'] and s['streams']['safety']['value'].get('software_stop_latched') and s['streams']['safety']['value'].get('stop_confirmed'),15)
assert canceled['streams']['task']['value']['state']=='CANCELED', canceled['streams']['task']
assert any('Action cancellation acknowledged' in e['message'] for e in canceled['events'])
# Reset local GUI latch and supervisor together after cancellation.
command('reset_stop');wait(lambda s:not s['stop_latched'] and not s['pending'] and s['streams']['safety']['value'].get('motion_allowed'),12)
records.append({'cancel':canceled})
Path('tmp/operator_gui/gazebo_control_check.json').write_text(json.dumps(records,indent=2))
print('PASS: HTTP → ExecuteTask → MoveIt/Gazebo observation, stop during motion, inhibited repeat, standstill, reset and cancellation')
