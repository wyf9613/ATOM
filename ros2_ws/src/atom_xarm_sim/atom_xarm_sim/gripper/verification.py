"""Reusable GraspVerification capability; no task-specific node."""
import time
import rclpy

class GraspVerification:
    def _grasp_callback(self, message):
        self.grasp_success = bool(message.data)

    def _wait_for_grasp(self, timeout_sec=20.0):
        self._publish_phase('VERIFY_GRASP')
        if self.simulate_grasp_success:
            self.get_logger().warning(
                'SIMULATION ONLY: accepting a simulated grasp-success result; '
                'no grasp command or object attachment is executed'
            )
            return
        deadline = time.monotonic() + timeout_sec
        while rclpy.ok() and not self.grasp_success and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.2)
        if not self.grasp_success:
            raise RuntimeError('timed out waiting for /atom/gripper/grasp_success')
