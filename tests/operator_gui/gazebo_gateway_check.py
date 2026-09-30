"""Acceptance check against the running Gazebo gateway; no motion commands."""
import json
from pathlib import Path
import time
import urllib.request

base='http://127.0.0.1:8089'
output=Path('tmp/operator_gui');output.mkdir(parents=True,exist_ok=True)
def snapshot():
    with urllib.request.urlopen(base+'/api/v1/state',timeout=3) as response:
        return json.load(response)
first=snapshot();time.sleep(1);second=snapshot()
assert second['metadata']['profile']=='gazebo'
assert second['metadata']['use_sim_time']
assert not second['commands_enabled']
for key in ('arm','gripper','tool','controller','diagnostics','camera','sim_clock'):
    assert second['streams'][key]['fresh'],key+' is missing or stale'
assert set(second['streams']['arm']['value']['names'])=={'joint'+str(i) for i in range(1,7)}
assert second['streams']['controller']['value']['state']=='active'
assert second['streams']['sim_clock']['value']['seconds']>first['streams']['sim_clock']['value']['seconds']
assert second['streams']['arm']['value']['source_stamp_s']>first['streams']['arm']['value']['source_stamp_s']
assert second['streams']['tool']['value']['frame']=='link_base'
assert 'base' not in second['streams'] and 'safety' not in second['streams'], 'Unexpected devices: verify the configured domain'
with urllib.request.urlopen(base+'/api/v1/camera',timeout=3) as response:
    content=response.read();assert content.startswith(b'\xff\xd8')
    (output/'gazebo_wrist_camera.jpg').write_bytes(content)
(output/'gazebo_gateway_check.json').write_text(json.dumps({'samples':2,'interval_s':1,'first':first,'second':second},indent=2))
print('PASS: advancing Gazebo joint feedback/clock, gripper, TF, controllers, diagnostics and JPEG; commands disabled')
