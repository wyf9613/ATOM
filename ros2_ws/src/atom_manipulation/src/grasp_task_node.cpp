#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <map>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

#include <geometry_msgs/msg/pose.hpp>
#include <moveit/move_group_interface/move_group_interface.h>
#include <moveit/planning_scene_interface/planning_scene_interface.h>
#include <moveit/trajectory_processing/iterative_time_parameterization.h>
#include <moveit_msgs/msg/collision_object.hpp>
#include <moveit_msgs/msg/robot_trajectory.hpp>
#include <rclcpp/rclcpp.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <shape_msgs/msg/solid_primitive.hpp>
#include <std_msgs/msg/empty.hpp>
#include <std_msgs/msg/string.hpp>
#include <tf2_msgs/msg/tf_message.hpp>

using namespace std::chrono_literals;
using MoveGroup = moveit::planning_interface::MoveGroupInterface;

namespace
{
constexpr double kPi = 3.14159265358979323846;
constexpr double kApproachDistance = 0.050;
constexpr double kAttachDistance = 0.035;
constexpr double kMaxJointSpeedForAttach = 0.020;
constexpr double kMaxObjectSpeedForAttach = 0.020;
constexpr double kMinimumLift = 0.040;
constexpr double kMaximumRetentionDrop = 0.008;

const std::vector<std::string> kArmJoints = {
  "shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
  "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"};
const std::vector<std::string> kFingerJoints = {
  "left_finger_joint", "right_finger_joint"};
const std::vector<double> kPregrasp = {
  0.0, -kPi / 2.0, 1.3358, -1.3358, -kPi / 2.0, 0.0};
const std::vector<double> kTransfer = {
  0.2, -kPi / 2.0, 1.3358, -1.3358, -kPi / 2.0, 0.0};

double distance(const geometry_msgs::msg::Point & a, const geometry_msgs::msg::Point & b)
{
  const double dx = a.x - b.x;
  const double dy = a.y - b.y;
  const double dz = a.z - b.z;
  return std::sqrt(dx * dx + dy * dy + dz * dz);
}
}  // namespace

class GraspTaskNode : public rclcpp::Node
{
public:
  GraspTaskNode()
  : Node("atom_grasp_task")
  {
    mode_ = declare_parameter<std::string>("grasp_mode", "logical");
    planner_id_ = declare_parameter<std::string>("planner_id", "RRTConnectkConfigDefault");
    if (mode_ != "logical" && mode_ != "physical") {
      throw std::runtime_error("grasp_mode must be 'logical' or 'physical'");
    }

    joint_subscription_ = create_subscription<sensor_msgs::msg::JointState>(
      "/joint_states", rclcpp::SensorDataQoS(),
      [this](const sensor_msgs::msg::JointState::SharedPtr message) {
        std::lock_guard<std::mutex> lock(data_mutex_);
        for (std::size_t index = 0; index < message->name.size(); ++index) {
          if (index < message->position.size()) {
            joint_positions_[message->name[index]] = message->position[index];
          }
          if (index < message->velocity.size()) {
            joint_velocities_[message->name[index]] = message->velocity[index];
          }
        }
      });
    pose_subscription_ = create_subscription<tf2_msgs::msg::TFMessage>(
      "/cuvette/pose", 20,
      [this](const tf2_msgs::msg::TFMessage::SharedPtr message) {
        for (const auto & transform : message->transforms) {
          if (transform.child_frame_id != "cuvette") {
            continue;
          }
          geometry_msgs::msg::Point point;
          point.x = transform.transform.translation.x;
          point.y = transform.transform.translation.y;
          point.z = transform.transform.translation.z;
          const auto now = std::chrono::steady_clock::now();
          std::lock_guard<std::mutex> lock(data_mutex_);
          if (cuvette_pose_) {
            const double dt = std::chrono::duration<double>(now - cuvette_time_).count();
            if (dt > 1e-4) {
              object_speed_ = distance(point, *cuvette_pose_) / dt;
            }
          }
          cuvette_pose_ = point;
          cuvette_time_ = now;
        }
      });
    logical_state_subscription_ = create_subscription<std_msgs::msg::String>(
      "/atom_grasp/state", 10,
      [this](const std_msgs::msg::String::SharedPtr message) {
        if (message->data != "attached" && message->data != "detached") {
          RCLCPP_WARN(get_logger(), "Ignoring unknown detachable-joint state '%s'", message->data.c_str());
          return;
        }
        logical_attached_.store(message->data == "attached");
        logical_state_seen_.store(true);
      });
    attach_publisher_ = create_publisher<std_msgs::msg::Empty>("/atom_grasp/attach", 10);
    detach_publisher_ = create_publisher<std_msgs::msg::Empty>("/atom_grasp/detach", 10);
  }

  int run()
  {
    MoveGroup arm(shared_from_this(), "ur_manipulator");
    MoveGroup gripper(shared_from_this(), "atom_gripper");
    arm.setPlannerId(planner_id_);
    arm.setPlanningTime(5.0);
    arm.setNumPlanningAttempts(3);
    arm.setMaxVelocityScalingFactor(0.25);
    arm.setMaxAccelerationScalingFactor(0.20);
    gripper.setPlanningTime(3.0);
    gripper.setMaxVelocityScalingFactor(0.30);
    gripper.setMaxAccelerationScalingFactor(0.20);

    if (!waitForInputs(15s)) {
      return fail("WAIT_FOR_INPUTS", "missing /joint_states or /cuvette/pose");
    }
    if (mode_ == "logical") {
      resetLogicalJoint();
    }

    if (!stage("PREGRASP") || !moveJoints(arm, kArmJoints, kPregrasp)) {
      return fail("PREGRASP", "MoveIt could not reach pregrasp");
    }
    if (!stage("OPEN") || !moveGripper(gripper, 0.0)) {
      return fail("OPEN", "MoveIt could not open the gripper");
    }
    if (!stage("APPROACH") || !moveCartesianZ(arm, -kApproachDistance)) {
      return fail("APPROACH", "Cartesian approach was incomplete");
    }

    const auto start_pose = cuvettePose();
    if (!start_pose) {
      return fail("APPROACH", "cuvette pose was lost");
    }
    if (!stage("CLOSE") || !moveGripper(gripper, -0.015)) {
      return fail("CLOSE", "gripper close trajectory failed");
    }

    if (!stage("ACQUIRE")) {
      return 1;
    }
    if (mode_ == "logical") {
      std::string gate_reason;
      if (!logicalAttachGate(arm, gate_reason)) {
        return fail("ACQUIRE", gate_reason);
      }
      addAndAttachPlanningObject(arm, *start_pose);
      if (!commandLogicalJoint(true, 5s)) {
        arm.detachObject("cuvette");
        return fail("ACQUIRE", "detachable joint did not report attached");
      }
    }

    if (!stage("LIFT") || !moveCartesianZ(arm, kApproachDistance)) {
      return fail("LIFT", "Cartesian lift was incomplete");
    }
    const auto lifted_pose = cuvettePose();
    if (!lifted_pose || lifted_pose->z - start_pose->z < kMinimumLift) {
      return fail("LIFT", "object did not rise by at least 0.040 m");
    }
    const double lift_height = lifted_pose->z - start_pose->z;

    if (!stage("TRANSFER") || !moveJoints(arm, kArmJoints, kTransfer)) {
      return fail("TRANSFER", "OMPL transfer plan or execution failed");
    }
    const auto transfer_pose = cuvettePose();
    if (!transfer_pose || transfer_pose->z < lifted_pose->z - kMaximumRetentionDrop) {
      return fail("TRANSFER", "object was not retained during transfer");
    }

    if (!stage("LOWER") || !moveCartesianZ(arm, -kApproachDistance)) {
      return fail("LOWER", "Cartesian lower was incomplete");
    }
    if (!stage("RELEASE") || !moveGripper(gripper, 0.0)) {
      return fail("RELEASE", "gripper open trajectory failed");
    }
    if (mode_ == "logical") {
      arm.detachObject("cuvette");
      if (!commandLogicalJoint(false, 5s)) {
        return fail("RELEASE", "detachable joint did not report detached");
      }
    }
    std::this_thread::sleep_for(500ms);
    const auto released_pose = cuvettePose();
    if (!released_pose || released_pose->z < start_pose->z - 0.010) {
      return fail("RELEASE", "released object fell below the target fixture");
    }

    if (!stage("RETREAT") || !moveCartesianZ(arm, kApproachDistance)) {
      return fail("RETREAT", "Cartesian retreat was incomplete");
    }
    if (mode_ == "logical") {
      planning_scene_.removeCollisionObjects({"cuvette"});
    }

    const double release_xy_error = std::hypot(
      released_pose->x - 0.2660, released_pose->y - 0.1890);
    const bool passed = release_xy_error <= 0.020;
    RCLCPP_INFO(
      get_logger(),
      "RESULT %s | mode=%s lift=%.4f_m release_xy_error=%.4f_m plans=%zu planning_time=%.3f_s",
      passed ? "PASS" : "FAIL", mode_.c_str(), lift_height, release_xy_error,
      planning_attempts_, planning_time_seconds_);
    return passed ? 0 : 1;
  }

private:
  bool stage(const std::string & name)
  {
    RCLCPP_INFO(get_logger(), "STAGE %s", name.c_str());
    return rclcpp::ok();
  }

  int fail(const std::string & stage_name, const std::string & reason)
  {
    RCLCPP_ERROR(
      get_logger(), "RESULT FAIL | mode=%s stage=%s reason=%s plans=%zu planning_time=%.3f_s",
      mode_.c_str(), stage_name.c_str(), reason.c_str(), planning_attempts_, planning_time_seconds_);
    return 1;
  }

  bool waitForInputs(std::chrono::seconds timeout)
  {
    const auto deadline = std::chrono::steady_clock::now() + timeout;
    while (rclcpp::ok() && std::chrono::steady_clock::now() < deadline) {
      {
        std::lock_guard<std::mutex> lock(data_mutex_);
        const bool all_joints = std::all_of(
          kArmJoints.begin(), kArmJoints.end(),
          [this](const auto & name) {return joint_positions_.count(name) > 0;});
        if (all_joints && cuvette_pose_) {
          return true;
        }
      }
      std::this_thread::sleep_for(50ms);
    }
    return false;
  }

  std::optional<geometry_msgs::msg::Point> cuvettePose()
  {
    std::lock_guard<std::mutex> lock(data_mutex_);
    return cuvette_pose_;
  }

  bool moveJoints(
    MoveGroup & group, const std::vector<std::string> & names,
    const std::vector<double> & values)
  {
    std::map<std::string, double> targets;
    for (std::size_t index = 0; index < names.size(); ++index) {
      targets[names[index]] = values[index];
    }
    if (!group.setJointValueTarget(targets)) {
      return false;
    }
    MoveGroup::Plan plan;
    const auto begin = std::chrono::steady_clock::now();
    ++planning_attempts_;
    const bool planned = static_cast<bool>(group.plan(plan));
    planning_time_seconds_ += std::chrono::duration<double>(
      std::chrono::steady_clock::now() - begin).count();
    return planned && static_cast<bool>(group.execute(plan));
  }

  bool moveGripper(MoveGroup & gripper, double position)
  {
    return moveJoints(gripper, kFingerJoints, {position, position});
  }

  bool moveCartesianZ(MoveGroup & arm, double dz)
  {
    auto target = arm.getCurrentPose("gripper_tcp").pose;
    target.position.z += dz;
    moveit_msgs::msg::RobotTrajectory trajectory;
    const auto begin = std::chrono::steady_clock::now();
    ++planning_attempts_;
    const double fraction = arm.computeCartesianPath({target}, 0.005, 0.0, trajectory, true);
    planning_time_seconds_ += std::chrono::duration<double>(
      std::chrono::steady_clock::now() - begin).count();
    if (fraction < 0.99) {
      RCLCPP_ERROR(get_logger(), "Cartesian path fraction %.3f is below 0.99", fraction);
      return false;
    }

    const auto state = arm.getCurrentState(2.0);
    if (!state) {
      return false;
    }
    robot_trajectory::RobotTrajectory timed(state->getRobotModel(), arm.getName());
    timed.setRobotTrajectoryMsg(*state, trajectory);
    trajectory_processing::IterativeParabolicTimeParameterization parameterization;
    if (!parameterization.computeTimeStamps(timed, 0.25, 0.20)) {
      return false;
    }
    timed.getRobotTrajectoryMsg(trajectory);
    MoveGroup::Plan plan;
    plan.trajectory_ = trajectory;
    return static_cast<bool>(arm.execute(plan));
  }

  bool logicalAttachGate(MoveGroup & arm, std::string & reason)
  {
    const auto pose = cuvettePose();
    if (!pose) {
      reason = "no current cuvette pose";
      return false;
    }
    const auto tcp = arm.getCurrentPose("gripper_tcp").pose.position;
    const double tcp_distance = distance(tcp, *pose);
    double maximum_joint_speed = 0.0;
    double object_speed = 0.0;
    {
      std::lock_guard<std::mutex> lock(data_mutex_);
      for (const auto & joint : kArmJoints) {
        const auto it = joint_velocities_.find(joint);
        if (it != joint_velocities_.end()) {
          maximum_joint_speed = std::max(maximum_joint_speed, std::abs(it->second));
        }
      }
      object_speed = object_speed_;
    }
    if (tcp_distance > kAttachDistance) {
      reason = "TCP-to-object distance exceeds 0.035 m";
      return false;
    }
    if (maximum_joint_speed > kMaxJointSpeedForAttach) {
      reason = "joint speed exceeds 0.020 rad/s";
      return false;
    }
    if (object_speed > kMaxObjectSpeedForAttach) {
      reason = "object speed exceeds 0.020 m/s";
      return false;
    }
    return true;
  }

  bool commandLogicalJoint(bool attach, std::chrono::seconds timeout)
  {
    const auto deadline = std::chrono::steady_clock::now() + timeout;
    std_msgs::msg::Empty message;
    while (rclcpp::ok() && std::chrono::steady_clock::now() < deadline) {
      if (attach) {
        attach_publisher_->publish(message);
      } else {
        detach_publisher_->publish(message);
      }
      std::this_thread::sleep_for(100ms);
      if (logical_state_seen_.load() && logical_attached_.load() == attach) {
        return true;
      }
    }
    return false;
  }

  void resetLogicalJoint()
  {
    // A no-op detach does not always produce a state event in Fortress.
    std_msgs::msg::Empty message;
    detach_publisher_->publish(message);
    std::this_thread::sleep_for(250ms);
  }

  void addAndAttachPlanningObject(
    MoveGroup & arm, const geometry_msgs::msg::Point & object_position)
  {
    moveit_msgs::msg::CollisionObject object;
    object.header.frame_id = "world";
    object.id = "cuvette";
    shape_msgs::msg::SolidPrimitive primitive;
    primitive.type = shape_msgs::msg::SolidPrimitive::BOX;
    primitive.dimensions = {0.014, 0.014, 0.045};
    geometry_msgs::msg::Pose pose;
    pose.orientation.w = 1.0;
    pose.position = object_position;
    object.primitives.push_back(primitive);
    object.primitive_poses.push_back(pose);
    object.operation = moveit_msgs::msg::CollisionObject::ADD;
    planning_scene_.applyCollisionObject(object);
    arm.attachObject("cuvette", "gripper_tcp", {"left_finger", "right_finger", "gripper_base"});
  }

  std::string mode_;
  std::string planner_id_;
  std::mutex data_mutex_;
  std::map<std::string, double> joint_positions_;
  std::map<std::string, double> joint_velocities_;
  std::optional<geometry_msgs::msg::Point> cuvette_pose_;
  std::chrono::steady_clock::time_point cuvette_time_;
  double object_speed_{0.0};
  std::atomic<bool> logical_state_seen_{false};
  std::atomic<bool> logical_attached_{false};
  std::size_t planning_attempts_{0};
  double planning_time_seconds_{0.0};
  moveit::planning_interface::PlanningSceneInterface planning_scene_;
  rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_subscription_;
  rclcpp::Subscription<tf2_msgs::msg::TFMessage>::SharedPtr pose_subscription_;
  rclcpp::Subscription<std_msgs::msg::String>::SharedPtr logical_state_subscription_;
  rclcpp::Publisher<std_msgs::msg::Empty>::SharedPtr attach_publisher_;
  rclcpp::Publisher<std_msgs::msg::Empty>::SharedPtr detach_publisher_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<GraspTaskNode>();
  rclcpp::executors::MultiThreadedExecutor executor;
  executor.add_node(node);
  std::thread spin_thread([&executor]() {executor.spin();});
  const int result = node->run();
  rclcpp::shutdown();
  spin_thread.join();
  return result;
}
