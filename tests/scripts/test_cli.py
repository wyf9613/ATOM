"""Validate public routing and quoted Docker commands without starting a simulation."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
CLI=ROOT/'scripts/atom.sh'

class CliTests(unittest.TestCase):
    def run_cli(self,*args,**kwargs):
        return subprocess.run([str(CLI),*args],cwd='/tmp',text=True,capture_output=True,**kwargs)

    def route(self,*args):
        result=self.run_cli(*args,'--dry-run')
        self.assertEqual(result.returncode,0,result.stderr)
        return shlex.split(result.stdout)

    def test_default_sim_and_explicit_transfer(self):
        self.assertEqual(self.route('sim')[-5:],['workflow','depth','','approach','visual_approach'])
        self.assertEqual(self.route('sim','--recipe','visual_observe')[-1],'visual_observe')
        self.assertEqual(self.route('sim','--camera','rgb','--restart','--workflow','transfer')[-5:],
                         ['workflow','rgb','--restart','transfer','visual_approach'])

    def test_attach_and_observation_are_distinct(self):
        self.assertEqual(self.route('attach')[-2:],['attach','depth'])
        self.assertEqual(self.route('observe','--control')[-3:],['observe','depth','control'])

    def test_stop_only_targets_named_sessions(self):
        for session,container in [('tube','atom-tube-workflow'),('observe','atom-operator-gazebo'),('monitor','atom-operator-monitor')]:
            self.assertEqual(self.route('stop','--session',session),['docker','stop','--timeout','5',container])
        self.assertNotEqual(self.run_cli('stop','--session','another-container').returncode,0)

    def test_all_demo_routes(self):
        for name in ('arm','dynamics','transfer','smoke'):
            self.assertEqual(self.route('demo',name)[-1],name)
        self.assertIn('desktop.sh',self.route('demo','arm','--gui')[1])
        self.assertEqual(self.route('demo','approach','--gui','--distance','.4')[-1],'.4')
        self.assertEqual(self.route('demo','camera','--rack-dx','.01')[-3:],['.01','0.0','0.0'])

    def test_invalid_options_fail_before_routing(self):
        for args in [('sim','--camera','bad'),('sim','--camera'),('build','--restart'),
                     ('demo','arm','--camera','depth'),('demo','camera','--rack-dx','nan'),
                     ('demo','camera','--rack-dx','.1'),('demo','approach'),('sim','--unknown'),('sim','--recipe','unsupported'),('sim','--workflow','transfer','--recipe','visual_observe')]:
            self.assertNotEqual(self.run_cli(*args,'--dry-run').returncode,0,args)

    def test_benchmark_help_uses_moved_tools(self):
        for tool in ('run','analyze'):
            result=self.run_cli('benchmark',tool,'--help')
            self.assertEqual(result.returncode,0,result.stderr)

    def test_shared_baseline_passes_valid_container_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);trace=directory/'commands.jsonl'
            fake=directory/'docker'
            fake.write_text('#!/usr/bin/env python3\nimport sys,os,json\nwith open(os.environ["ATOM_TEST_DOCKER_TRACE"],"a") as f: f.write(json.dumps(sys.argv[1:])+"\\n")\n')
            fake.chmod(0o755)
            env=dict(os.environ,PATH=str(directory)+os.pathsep+os.environ['PATH'],ATOM_TEST_DOCKER_TRACE=str(trace))
            result=self.run_cli('demo','transfer',env=env)
            self.assertEqual(result.returncode,0,result.stderr)
            commands=[json.loads(line) for line in trace.read_text().splitlines()]
            self.assertEqual(len(commands),3)
            self.assertIn('ATOM_BASELINE=transfer',commands[-1])
            for command in commands:
                if '-lc' in command:
                    syntax=subprocess.run(['bash','-n','-c',command[-1]],capture_output=True,text=True)
                    self.assertEqual(syntax.returncode,0,syntax.stderr)
