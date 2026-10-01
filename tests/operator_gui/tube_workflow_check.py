"""Observe the real RGB-D experiment and record UI/API workflow progression."""
import argparse
import json
from pathlib import Path
import time
import urllib.request
import urllib.error
parser=argparse.ArgumentParser();parser.add_argument('--require-success',action='store_true');parser.add_argument('--require-depth-fusion',action='store_true');args=parser.parse_args()
output=Path('tmp/operator_gui');output.mkdir(parents=True,exist_ok=True)
records=[];deadline=time.monotonic()+300
base='http://127.0.0.1:8089'
last_phase=None
while time.monotonic()<deadline:
    try:
        with urllib.request.urlopen(base+'/api/v1/state',timeout=3) as r:state=json.load(r)
    except urllib.error.URLError:time.sleep(.5);continue
    task=state['streams'].get('task',{}).get('value',{})
    if task.get('source')!='tube_approach_experiment':time.sleep(.5);continue
    phase=(task.get('phase'),task.get('state'))
    if phase!=last_phase:
        print('Workflow:',phase,task.get('detail'),flush=True);last_phase=phase
    records.append(state)
    if task.get('state') in ('SUCCEEDED','FAILED'):break
    time.sleep(.5)
else:raise AssertionError('External workflow completion timeout')
(output/'tube_workflow_check.json').write_text(json.dumps(records,indent=2))
if args.require_depth_fusion:
    assert any(s['streams']['task']['value'].get('depth_quality',{}).get('fusion',{}).get('used') for s in records), 'No accepted depth-fused pose reached task state'
depth_configured=bool(state.get('metadata',{}).get('interfaces',{}).get('depth_topic'))
if depth_configured:
    assert any(s['streams'].get('depth',{}).get('fresh') for s in records),'No live depth'
assert any(s['streams'].get('tags',{}).get('fresh') for s in records),'No detection frames'
assert any(s['streams'].get('tags',{}).get('value',{}).get('detected') for s in records),'No Tag detected'
assert any(s['streams'].get('arm',{}).get('fresh') for s in records),'No arm feedback'
image_checks=[('camera',b'\xff\xd8')]
if depth_configured:image_checks.append(('depth',b'\x89PNG'))
for path,magic in image_checks:
    with urllib.request.urlopen(base+'/api/v1/'+path) as r:content=r.read()
    assert content.startswith(magic)
    (output/('tube_'+path+('.jpg' if path=='camera' else '.png'))).write_bytes(content)
assert not task.get('grasp_completed') and not task.get('place_completed')
assert not state['commands_enabled'],'External monitor must not start competing tasks'
print('PASS: workflow state, configured camera previews, Tag results, joints and terminal outcome reach GUI',flush=True)
if task['state']!='SUCCEEDED':
    print('EXPERIMENT FAILED: '+task['detail'])
    if args.require_success:raise AssertionError(task['detail'])
else:
    if task.get('rack_tag_ids'):
        assert set(task['rack_tag_ids']) <= set(task['observed_tag_ids']), 'Incomplete rack observation'
        assert task['tag_id'] in task['observed_tag_ids'], 'Selected target not observed'
        coarse=task.get('coarse_rack_command')
        assert coarse and abs(coarse['position_m']['x'])+abs(coarse['position_m']['y'])>0, 'No coarse rack XY'
    segments=set(task['completed_segments'])
    if task.get('task_recipe')=='visual_observe':
        assert not segments, 'Observation recipe must not execute approach motion'
        assert task.get('completed_capabilities')==['prepare_observation','move_observation','capture_observation']
    else:
        assert {'alignment','perpendicular'} <= segments
        assert all(phase in ('alignment','perpendicular') or phase.startswith('realignment_') for phase in segments)
    print('EXPERIMENT SUCCEEDED: '+task.get('task_recipe','visual_approach')+' completed; no physical grasp claimed')
