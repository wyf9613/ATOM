"""Shared MoveIt/controller interface wiring for all manipulation clients."""
from controller_manager_msgs.srv import ListControllers
from moveit_msgs.action import MoveGroup, ExecuteTrajectory
from moveit_msgs.srv import GetCartesianPath, GetPositionFK, GetPositionIK
from rclpy.action import ActionClient

class MotionClients:
    def __init__(self, node, *, cartesian=False, kinematics=False, execute=True):
        self.move_group_client = ActionClient(node, MoveGroup, '/move_action')
        self.controller_client = node.create_client(ListControllers, '/controller_manager/list_controllers')
        if execute:
            self.execute_client = ActionClient(node, ExecuteTrajectory, '/execute_trajectory')
        if cartesian:
            self.cartesian_client = node.create_client(GetCartesianPath, '/compute_cartesian_path')
        if kinematics:
            self.fk_client = node.create_client(GetPositionFK, '/compute_fk')
            self.ik_client = node.create_client(GetPositionIK, '/compute_ik')

    def bind(self, owner):
        """Keep existing algorithm attributes while sharing interface construction."""
        for name, client in vars(self).items():
            setattr(owner, name, client)
