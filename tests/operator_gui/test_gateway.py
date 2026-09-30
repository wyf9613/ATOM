import importlib.util
from pathlib import Path
import threading
import time
import unittest
import json
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer

path = Path(__file__).resolve().parents[2] / 'tools/operator_gui/server.py'
spec = importlib.util.spec_from_file_location('gateway',path)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)

class Adapter:
    def __init__(self): self.calls=[]
    def available(self): return {c:True for c in module.COMMANDS}
    def send(self,*args): self.calls.append(args)

class GatewayTests(unittest.TestCase):
    def test_external_stop_blocks_motion_and_display(self):
        gateway=module.Gateway(False,True);gateway.adapter=Adapter()
        gateway.update('arm',{});gateway.update('diagnostics',[])
        gateway.update('safety',{'hardware_estop':'released','motion_allowed':True,'software_stop_latched':True})
        self.assertTrue(gateway.snapshot()['stop_latched'])
        with self.assertRaises(PermissionError):gateway.command({'command':'observe'})

    def test_simulation_status_cannot_enable_hardware(self):
        gateway=module.Gateway(False,True);gateway.adapter=Adapter();gateway.metadata['profile']='hardware'
        gateway.update('arm',{});gateway.update('diagnostics',[])
        gateway.update('safety',{'source':'gazebo','hardware_estop':'not_applicable','motion_allowed':True})
        with self.assertRaises(PermissionError):gateway.command({'command':'observe'})

    def test_english_and_dom_ids(self):
        import re
        root=path.parent/'static'
        html=(root/'index.html').read_text();js=(root/'app.js').read_text()
        self.assertFalse(re.search(r'[\u4e00-\u9fff]', html+js))
        ids=set(re.findall(r'id="([^"]+)"',html))
        referenced=set(re.findall(r"(?:el|text)\('([^']+)'",js))
        self.assertFalse(referenced-ids, referenced-ids)

    def test_gazebo_clock_required_for_motion(self):
        gateway=module.Gateway(False,True);gateway.adapter=Adapter()
        gateway.metadata['profile']='gazebo'
        gateway.update('arm',{});gateway.update('diagnostics',[])
        gateway.update('safety',{'source':'gazebo','hardware_estop':'not_applicable','motion_allowed':True})
        gateway.update('controller',{'state':'active'})
        with self.assertRaises(PermissionError):gateway.command({'command':'observe'})
        gateway.update('sim_clock',{'seconds':1})
        gateway.command({'command':'observe'})

    def test_stop_latches_and_inhibits_demo_motion(self):
        gateway=module.Gateway()
        gateway.command({'command':'stop'})
        with self.assertRaises(PermissionError): gateway.command({'command':'observe'})
        gateway.command({'command':'reset_stop'})
        self.assertFalse(gateway.stop_latched)

    def test_readonly_rejects_commands(self):
        gateway=module.Gateway(False)
        with self.assertRaises(PermissionError): gateway.command({'command':'observe'})

    def test_stop_inhibits_even_when_service_missing(self):
        gateway=module.Gateway(False,True)
        with self.assertRaises(PermissionError): gateway.command({'command':'stop'})
        self.assertTrue(gateway.stop_latched)

    def test_missing_stale_and_unreleased_safety_block(self):
        gateway=module.Gateway(False,True);gateway.adapter=Adapter()
        with self.assertRaises(PermissionError): gateway.command({'command':'observe'})
        gateway.update('arm',{});gateway.update('diagnostics',[])
        gateway.update('safety',{'hardware_estop':'pressed','motion_allowed':True})
        with self.assertRaises(PermissionError): gateway.command({'command':'observe'})
        gateway.update('safety',{'hardware_estop':'released','motion_allowed':True})
        gateway.streams['arm']['received']=time.monotonic()-3
        with self.assertRaises(PermissionError): gateway.command({'command':'observe'})
        gateway.update('arm',{})
        result=gateway.command({'command':'observe'})
        self.assertEqual(result['status'],'submitted')
        self.assertEqual(len(gateway.adapter.calls),1)
        with self.assertRaises(PermissionError): gateway.command({'command':'observe'})

    def test_bad_parameters_never_execute(self):
        gateway=module.Gateway()
        for parameters in ({'x':float('nan'),'y':0,'yaw':0},{'x':0,'y':0,'yaw':99}):
            with self.assertRaises(ValueError):gateway.command({'command':'navigate','parameters':parameters})
        with self.assertRaises(ValueError):gateway.command({'command':'pick','parameters':{'slot':True}})

    def test_http_token_origin_and_validation(self):
        gateway=module.Gateway();server=ThreadingHTTPServer(('127.0.0.1',0),module.handler_for(gateway))
        threading.Thread(target=server.serve_forever,daemon=True).start()
        base='http://127.0.0.1:'+str(server.server_port)
        try:
            self.assertEqual(json.load(urllib.request.urlopen(base+'/api/v1/state'))['mode'],'demo')
            for headers,code in [({},403),({'X-ATOM-Token':gateway.token,'Origin':'http://evil.invalid'},403)]:
                req=urllib.request.Request(base+'/api/v1/commands',data=b'{"command":"stop"}',headers=headers)
                with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(req)
                self.assertEqual(cm.exception.code,code)
            req=urllib.request.Request(base+'/api/v1/commands',data=b'{"command":"stop"}',headers={'X-ATOM-Token':gateway.token})
            with urllib.request.urlopen(req) as result:self.assertEqual(result.status,202)
            self.assertTrue(gateway.stop_latched)
        finally:server.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
