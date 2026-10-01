"""Task reuse and fault gates are tested without ROS or simulated hardware."""
import ast
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'ros2_ws/src/atom_xarm_sim'))
from atom_xarm_sim.tasks.recipes import RECIPES, execute_recipe

class CompositionTests(unittest.TestCase):
    def test_observe_is_reused_prefix_of_approach(self):
        self.assertEqual(RECIPES['visual_approach'][:3],RECIPES['visual_observe'])
        called=[]
        capabilities={step:lambda s=step:called.append(s) for step in RECIPES['visual_approach']}
        execute_recipe('visual_observe',capabilities)
        self.assertEqual(tuple(called),RECIPES['visual_observe'])
        self.assertNotIn('align_selected',called)

    def test_missing_final_capability_prevents_any_motion(self):
        called=[]
        capabilities={step:lambda:called.append('moved') for step in RECIPES['visual_approach'][:-1]}
        with self.assertRaises(ValueError):execute_recipe('visual_approach',capabilities)
        self.assertEqual(called,[])

    def test_perception_failure_cannot_trigger_approach(self):
        called=[]
        def fail():raise RuntimeError('fresh same-frame observation unavailable')
        capabilities={step:lambda s=step:called.append(s) for step in RECIPES['visual_approach']}
        capabilities['capture_observation']=fail
        with self.assertRaises(RuntimeError):execute_recipe('visual_approach',capabilities)
        self.assertEqual(called,['prepare_observation','move_observation'])

    def test_unknown_recipe_prevents_motion(self):
        with self.assertRaises(ValueError):execute_recipe('physical_pick_and_place',{})

    def test_completed_steps_survive_a_later_fault(self):
        completed=[]
        capabilities={step:lambda:None for step in RECIPES['visual_approach']}
        def fail():raise RuntimeError('planner rejected path')
        capabilities['align_selected']=fail
        with self.assertRaises(RuntimeError):
            execute_recipe('visual_approach',capabilities,on_complete=completed.append)
        self.assertEqual(completed,list(RECIPES['visual_approach'][:4]))

    def test_capability_modules_do_not_create_new_nodes(self):
        package=ROOT/'ros2_ws/src/atom_xarm_sim/atom_xarm_sim'
        for module in ['perception/depth_fusion.py','perception/observer.py','planning/approach.py','planning/clients.py','simulation/inputs.py','telemetry/task_status.py','tasks/recipes.py']:
            tree=ast.parse((package/module).read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.ClassDef):
                    self.assertNotIn('Node',[ast.unparse(base) for base in node.bases],module)
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
                    self.assertNotEqual(node.func.id,'Node',module)
