'use strict';
let token='',lastState=null,healthy=false,latency=null;
const el=id=>document.getElementById(id);
const text=(id,value)=>{el(id).textContent=value;};
const item=(tag,value,className)=>{const node=document.createElement(tag);node.textContent=value;if(className)node.className=className;return node;};
const fmt=value=>Number.isFinite(value)?value.toFixed(2):'—';
function render(state){
 lastState=state;healthy=true;document.querySelectorAll('.offline').forEach(n=>n.classList.remove('offline'));
 text('mode',state.mode==='demo'?'DEMO · Synthetic data':'ROS 2 · Live telemetry');
 text('connection',`Gateway connected · ${latency??'—'} ms`);text('clock',new Date().toLocaleString('en-AU',{hour12:false}));
 const streams=state.streams,arm=streams.arm,base=streams.base,battery=streams.battery,task=streams.task,safety=streams.safety;
 const banner=el('banner');banner.classList.toggle('error',state.stop_latched);
 banner.textContent=state.stop_latched?'Software stop latched · Check stop feedback before reset. Use the physical E-stop for emergencies.':state.mode==='demo'?'Demo mode: telemetry is synthetic; commands simulate responses only.':state.commands_enabled?'ROS 2 commands enabled · Readiness and fresh feedback are required.':'ROS 2 read-only monitoring · Commands disabled.';
 text('arm-status',arm?(arm.fresh?'Receiving telemetry':'Stale data'):'Not connected');
 text('base-status',base?(base.fresh?'Receiving telemetry':'Stale data'):'Not connected');
 text('base-detail',base?`X ${fmt(base.value.x)} / Y ${fmt(base.value.y)} m · ${fmt(base.value.speed)} m/s`:'Waiting for /odom');
 text('battery',battery&&battery.fresh&&Number.isFinite(battery.value.percent)?`${battery.value.percent}%`:'—');
 text('voltage',battery?`${fmt(battery.value.voltage)} V${battery.fresh?'':' · Stale'}`:'Waiting for /battery_state');
 text('task',task?(task.fresh?task.value.source==='transfer_baseline'&&task.value.state==='SUCCEEDED'?'MOTION TEST PASSED':task.value.state||'Unknown':`${task.value.state||'Unknown'} · Last update stale`):'Not connected');text('task-detail',task?.value.detail||'Waiting for task executive');
 text('tool-position',streams.tool?.fresh?`${fmt(streams.tool.value.x)}, ${fmt(streams.tool.value.y)}, ${fmt(streams.tool.value.z)}`:'Unknown');
 text('gripper-position',streams.gripper?.fresh?streams.gripper.value.position.map(fmt).join(' / ')+' rad':'Unknown');
 text('vendor-fault',streams.vendor?.fresh?`${streams.vendor.value.error_code} / ${streams.vendor.value.warning_code}`:'Not connected');
 text('arm-age',arm?`${arm.age_s.toFixed(1)} s ago`:'No feedback');
 el('joints').replaceChildren();
 (arm?.value.names||Array.from({length:6},(_,i)=>`joint${i+1}`)).slice(0,12).forEach((name,i)=>{
  const row=item('div','','joint-row'),value=arm?.value.position[i];row.append(item('span',name));
  const bar=item('div','','bar'),fill=item('i','');fill.style.width=`${Number.isFinite(value)?Math.min(100,Math.abs(value)/Math.PI*100):0}%`;bar.append(fill);row.append(bar,item('b',fmt(value)));el('joints').append(row);
 });
 el('checks').replaceChildren();
 const checks=[['Arm telemetry',arm],['Base telemetry',base],['Safety supervisor',safety],['Diagnostics',streams.diagnostics]];
 checks.forEach(([name,s])=>{const row=item('div','','check-row');row.append(item('span',name),item('b',s?(s.fresh?'Fresh':'Stale'):'Not connected',s?.fresh?'ok':'warn'));el('checks').append(row);});
 const diagnostics=streams.diagnostics?.value||[];
 diagnostics.forEach(d=>{const row=item('div','','check-row');row.append(item('span',d.name),item('span',d.message,d.level>=2?'bad':d.level===1?'warn':'ok'));el('checks').append(row);});
 const camera=streams.camera;el('camera-image').hidden=!camera?.fresh;text('camera-status',camera?(camera.fresh?`Live · ${fmt(camera.value.received?.fps)} received / ${fmt(camera.value.preview?.fps)} preview fps`:'Stale images'):'Waiting for image stream');
 text('health-count',`${diagnostics.length} diagnostics`);
 text('hardware-stop',safety?.fresh?({'released':'Released','pressed':'Pressed','unknown':'Unknown','not_applicable':'Not applicable (simulation)'}[safety.value.hardware_estop]||'Unknown'):'Unknown / Stale');
 text('stop-feedback',safety?.fresh&&safety.value.stop_confirmed?'Confirmed':'Not confirmed');
 renderReadiness(state);renderSensors(state);
 text('command-mode',state.mode==='demo'?'Demo only':state.commands_enabled?'Guarded commands':'Read-only');
 document.querySelectorAll('[data-command]').forEach(button=>{const command=button.dataset.command;button.disabled=!state.commands_enabled||!state.available[command]||state.pending.includes(command)||(state.stop_latched&&!['cancel','reset_stop'].includes(command));button.title=state.command_blocks?.[command]||(!state.available[command]?'Downstream interface not connected':'');if(state.command_blocks?.[command])button.disabled=true;});
 el('stop').disabled=!state.commands_enabled;
 el('events').replaceChildren();state.events.forEach(e=>{const node=item('div','','event '+e.level);node.append(item('small',new Date(e.time*1000).toLocaleTimeString()),item('span',e.message));el('events').append(node);});
}
async function poll(){
 try{const started=performance.now();const response=await fetch('/api/v1/state',{signal:AbortSignal.timeout(2000)});if(!response.ok)throw Error('HTTP '+response.status);latency=Math.round(performance.now()-started);render(await response.json());}
 catch(error){healthy=false;document.querySelectorAll('.stats article,.workspace').forEach(n=>n.classList.add('offline'));text('connection','Gateway disconnected');el('banner').classList.add('error');text('banner','Disconnected · Feedback unavailable. Use on-site controls to stop equipment.');document.querySelectorAll('[data-command],#stop').forEach(b=>b.disabled=true);}
 finally{setTimeout(poll,1000);}
}
async function command(name){
 if(!healthy)return;
 let parameters={};if(['pick','place'].includes(name))parameters={slot:Number(el('slot').value)};
 if(name==='navigate')parameters={x:Number(el('x').value),y:Number(el('y').value),yaw:Number(el('yaw').value),frame:'map'};
 if(name==='reset_stop'&&!confirm('Reset clears the software latch and does not resume the task. Confirm the workspace is ready before continuing.'))return;
 try{const response=await fetch('/api/v1/commands',{method:'POST',headers:{'Content-Type':'application/json','X-ATOM-Token':token},body:JSON.stringify({command:name,parameters}),signal:AbortSignal.timeout(3000)});const result=await response.json();text('command-result',response.ok?`${result.status==='demo_completed'?'Demo response complete':'Request submitted; waiting for service response'} · ${result.request_id}`:result.error);}
 catch(error){text('command-result','Request outcome unknown: '+error.message+'; check feedback before sending again.');}
}
document.querySelectorAll('[data-command]').forEach(button=>button.addEventListener('click',()=>command(button.dataset.command)));
el('stop').addEventListener('click',()=>command('stop'));
el('export').addEventListener('click',()=>{if(!lastState)return;const url=URL.createObjectURL(new Blob([JSON.stringify(lastState,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`atom-state-${Date.now()}.json`;a.click();URL.revokeObjectURL(url);});
async function session(){try{const response=await fetch('/api/v1/session',{signal:AbortSignal.timeout(2000)});if(!response.ok)throw Error('Session unavailable');token=(await response.json()).token;}catch(error){text('command-result','Session connection failed: '+error.message);}}
el('refresh-session').addEventListener('click',session);
session().finally(poll);

function renderReadiness(state){
 const metadata=state.metadata||{};text('profile',metadata.profile||state.mode);
 const task=state.streams.task;const progress=task?.fresh?task.value.progress:null;
 el('task-progress').value=Number.isFinite(progress)?Math.max(0,Math.min(1,progress)):0;
 text('task-progress-label',Number.isFinite(progress)?`${Math.round(progress*100)}%`:'Unknown');
 text('task-request',task?.fresh&&task.value.request_id?`Request ${task.value.request_id}`:'No active request');
 el('device-readiness').replaceChildren();
 const checks=[['Gripper feedback',state.streams.gripper],['Tool pose / TF',state.streams.tool],['Arm controller',state.streams.controller],['Simulated clock',state.streams.sim_clock],['Perception / selected Tag',state.streams.perception],['Vendor controller status',state.streams.vendor]];
 checks.forEach(([name,s])=>{const row=item('div','','check-row');let status=s?(s.fresh?'Receiving':'Stale'):'Not connected';if(s?.fresh&&name==='Arm controller')status=s.value.state||'Unknown';if(s?.fresh&&name==='Tool pose / TF')status=`${s.value.frame} → ${s.value.child}`;if(s?.fresh&&name==='Perception / selected Tag')status=`Tag ${s.value.tag_id??'—'} · ${s.value.phase||'Observed'}`;row.append(item('span',name),item('span',status,s?.fresh?'ok':'warn'));el('device-readiness').append(row);});
 el('gateway-info').replaceChildren();
 const details=[['Source',metadata.profile||state.mode],['ROS domain',metadata.ros_domain_id??'Not applicable'],['Time source',metadata.use_sim_time?'Simulation clock':'System clock'],['HTTP response time',`${latency??'—'} ms`],['Motion interfaces',Object.values(state.available).filter(Boolean).length+' ready'],['Software stop',state.stop_latched?'Latched':'Not latched']];
 details.forEach(([k,v])=>el('gateway-info').append(item('span',k),item('b',v)));
 text('interface-config',JSON.stringify(metadata.interfaces||{},null,2));
}

function renderSensors(state){
 const d=state.streams.depth,t=state.streams.tags,workflow=state.streams.task;
 const live=Boolean(d?.fresh);text('depth-status',d?(live?'Live depth':'Stale depth'):state.metadata?.interfaces.depth_topic?'Waiting for depth':'Not configured');
 el('depth-image').hidden=!live;el('depth-placeholder').hidden=live;
 el('depth-metrics').replaceChildren();const dv=d?.value||{};
 [['Preview rate',live?`${fmt(dv.received?.fps)} received / ${fmt(dv.preview?.fps)} preview fps`:'Unknown'],['Valid pixels',live?`${(dv.valid_fraction*100).toFixed(1)}%`:'Unknown'],['Median depth',live?fmt(dv.median_m)+' m':'Unknown'],['Depth range',live?`${fmt(dv.min_m)}–${fmt(dv.max_m)} m`:'Unknown'],['Frame stamp',live?fmt(dv.source_stamp_s)+' s':'Unknown'],['Sensor frame',dv.frame||'Unknown']].forEach(([k,v])=>el('depth-metrics').append(item('span',k),item('b',v)));
 const w=workflow?.value||{},ids=t?.value.detected_ids||[],selected=w.tag_id??Number(el('slot').value);
 text('tag-result',t?.fresh?(ids.includes(selected)?`Selected Tag ${selected}: DETECTED · Latest detection IDs: ${ids.join(', ')}`:`Selected Tag ${selected}: NOT IN LATEST DETECTION · Latest detection IDs: ${ids.length?ids.join(', '):'none'}`):'Tag detection unavailable / stale');
 el('tag-result').classList.toggle('found',Boolean(t?.fresh&&ids.includes(selected)));
 text('workflow-source',w.source==='transfer_baseline'?'Legacy motion test · targets unrelated to tube slots':w.source==='tube_approach_experiment'?'Visual approach experiment':'No experiment runner');
 const stages=w.task_recipe==='visual_observe'?[['pre_observation_setup','Setup'],['pre_observation_move','Pre-observe'],['pre_observation_capture','Detect Tags'],['complete','Result']]:w.source==='transfer_baseline'?[['INITIALIZING','Setup'],['MOVE_TO_PICK','Move to pick'],['VERIFY_GRASP','Verify grasp'],['VERTICAL_LIFT','Lift'],['CONSTRAINED_TRANSFER','Transfer'],['VERTICAL_DESCENT','Descend'],['COMPLETE','Motion result']]:[['pre_observation_setup','Setup'],['pre_observation_move','Pre-observe'],['pre_observation_capture','Detect Tags'],['alignment','Align 0.40 m'],['realignment','Re-align (if needed)'],['perpendicular','Approach 0.10 m'],['complete','Result']];
 const index=stages.findIndex(([phase])=>phase===w.phase);el('workflow-steps').replaceChildren();
 stages.forEach(([phase,label],i)=>el('workflow-steps').append(item('div',label,'step '+(i<index?'done':i===index?(w.state==='FAILED'?'failed':'active'):'waiting'))));
 const m=w.metrics||{},pose=t?.fresh?t.value.poses_camera_m?.[String(selected)]:null;el('workflow-metrics').replaceChildren();
 [['Experiment phase',w.phase||'Not running'],['Transfer pose error',w.source==='transfer_baseline'?fmt(m.vertical_descent?.final_position_error_m??m.constrained_transfer?.final_position_error_m??m.move_to_pick?.final_position_error_m)+' m':'Not applicable'],['Grasp verification',w.source==='transfer_baseline'?(w.simulate_grasp_success?'SIMULATED · physical transport unvalidated':'External feedback'):'Visual approach only'],['Tags observed by runner',(w.observed_tag_ids||[]).join(', ')||'None'],['Selected Tag pose · camera (m)',pose?pose.map(fmt).join(', '):'Unknown'],['Tag image stamp',t?.fresh?fmt(t.value.source_stamp_s)+' s':'Unknown'],['Front-to-estimated-plane',fmt(m.front_plane_distance_m)+' m'],['Lateral error',fmt(m.ray_lateral_error_m)+' m'],['Physical grasp',w.grasp_completed===true?'Confirmed':w.simulate_grasp_success?'Simulated signal only':'Not implemented'],['Placement',w.place_completed===true?'Confirmed':'Not implemented']].forEach(([k,v])=>el('workflow-metrics').append(item('span',k),item('b',v)));
}

// Image refresh is independent of the 1 Hz telemetry view. Do not queue requests.
async function previewLoop(kind,id){
 let previous=null;
 for(;;){
  const started=performance.now();
  try{
   if(healthy&&lastState?.streams[kind]?.fresh&&!document.hidden){
    const response=await fetch('/api/v1/'+kind,{cache:'no-store',signal:AbortSignal.timeout(2000)});
    if(response.ok){const url=URL.createObjectURL(await response.blob());
     const image=el(id);image.src=url;try{await image.decode();}catch{}
     if(previous)URL.revokeObjectURL(previous);previous=url;}
   }
  }catch{}
  await new Promise(resolve=>setTimeout(resolve,Math.max(10,100-(performance.now()-started))));
 }
}
previewLoop('camera','camera-image');previewLoop('depth','depth-image');
