#include "atom_xarm_dynamics/nominal_actuator_system.hpp"

#include <algorithm>
#include <cmath>
#include <limits>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include <gz/physics/Geometry.hh>
#include <gz/sim/components/JointAxis.hh>
#include <gz/sim/components/JointForceCmd.hh>
#include <gz/sim/components/JointPosition.hh>
#include <gz/sim/components/JointPositionReset.hh>
#include <gz/sim/components/JointTransmittedWrench.hh>
#include <gz/sim/components/JointType.hh>
#include <gz/sim/components/JointVelocity.hh>
#include <gz/sim/components/JointVelocityReset.hh>

#include "hardware_interface/hardware_info.hpp"
#include "hardware_interface/types/hardware_interface_type_values.hpp"
#include "pluginlib/class_list_macros.hpp"

namespace
{

double initial_value(const hardware_interface::InterfaceInfo & interface_info)
{
  if (interface_info.initial_value.empty()) {
    return 0.0;
  }
  return std::stod(interface_info.initial_value);
}

}  // namespace

struct JointData
{
  std::string name;
  sdf::JointType type{sdf::JointType::INVALID};
  sdf::JointAxis axis;
  double position{0.0};
  double velocity{0.0};
  double effort{0.0};
  double position_command{std::numeric_limits<double>::quiet_NaN()};
  double velocity_command{0.0};
  double kp{0.0};
  double kd{0.0};
  double effort_limit{0.0};
  sim::Entity entity{sim::kNullEntity};
};

class atom_xarm_dynamics::NominalActuatorSystemPrivate
{
public:
  std::vector<JointData> joints;
  std::vector<hardware_interface::StateInterface> state_interfaces;
  std::vector<hardware_interface::CommandInterface> command_interfaces;
  sim::EntityComponentManager * ecm{nullptr};
};

namespace atom_xarm_dynamics
{

bool NominalActuatorSystem::initSim(
  rclcpp::Node::SharedPtr & model_nh,
  std::map<std::string, sim::Entity> & enabled_joints,
  const hardware_interface::HardwareInfo & hardware_info,
  sim::EntityComponentManager & ecm,
  unsigned int /*update_rate*/)
{
  data_ = std::make_unique<NominalActuatorSystemPrivate>();
  nh_ = model_nh;
  data_->ecm = &ecm;
  data_->joints.resize(hardware_info.joints.size());

  if (data_->joints.empty()) {
    RCLCPP_ERROR(nh_->get_logger(), "No joints were supplied to the nominal actuator model");
    return false;
  }

  const std::vector<double> default_kp{1000.0, 1000.0, 1000.0, 800.0, 800.0, 1000.0};
  const std::vector<double> default_kd{30.0, 30.0, 25.0, 15.0, 8.0, 5.0};
  const std::vector<double> default_effort{200.0, 200.0, 90.0, 68.0, 19.0, 19.0};

  auto parameter_vector = [this](
    const std::string & name, const std::vector<double> & defaults)
    {
      if (!nh_->has_parameter(name)) {
        nh_->declare_parameter<std::vector<double>>(name, defaults);
      }
      return nh_->get_parameter(name).as_double_array();
    };

  const auto kp = parameter_vector("atom_actuator_kp", default_kp);
  const auto kd = parameter_vector("atom_actuator_kd", default_kd);
  const auto effort_limits = parameter_vector("atom_actuator_effort_limit", default_effort);
  if (kp.size() != data_->joints.size() || kd.size() != data_->joints.size() ||
    effort_limits.size() != data_->joints.size())
  {
    RCLCPP_ERROR(
      nh_->get_logger(),
      "Nominal actuator kp, kd and effort_limit arrays must each contain %zu values",
      data_->joints.size());
    return false;
  }

  for (std::size_t index = 0; index < hardware_info.joints.size(); ++index) {
    const auto & joint_info = hardware_info.joints[index];
    auto & joint = data_->joints[index];
    joint.name = joint_info.name;
    joint.kp = kp[index];
    joint.kd = kd[index];
    joint.effort_limit = effort_limits[index];

    const auto entity_it = enabled_joints.find(joint.name);
    if (entity_it == enabled_joints.end()) {
      RCLCPP_ERROR(nh_->get_logger(), "Joint '%s' is absent from the Gazebo model", joint.name.c_str());
      return false;
    }
    joint.entity = entity_it->second;

    const auto * type_component = ecm.Component<sim::components::JointType>(joint.entity);
    const auto * axis_component = ecm.Component<sim::components::JointAxis>(joint.entity);
    if (type_component == nullptr || axis_component == nullptr) {
      RCLCPP_ERROR(nh_->get_logger(), "Joint '%s' has no type or axis component", joint.name.c_str());
      return false;
    }
    joint.type = type_component->Data();
    joint.axis = axis_component->Data();

    if (!ecm.EntityHasComponentType(joint.entity, sim::components::JointPosition().TypeId())) {
      ecm.CreateComponent(joint.entity, sim::components::JointPosition());
    }
    if (!ecm.EntityHasComponentType(joint.entity, sim::components::JointVelocity().TypeId())) {
      ecm.CreateComponent(joint.entity, sim::components::JointVelocity());
    }
    if (!ecm.EntityHasComponentType(
        joint.entity, sim::components::JointTransmittedWrench().TypeId()))
    {
      ecm.CreateComponent(joint.entity, sim::components::JointTransmittedWrench());
    }
    if (!ecm.EntityHasComponentType(joint.entity, sim::components::JointForceCmd().TypeId())) {
      ecm.CreateComponent(joint.entity, sim::components::JointForceCmd({0.0}));
    }

    for (const auto & interface_info : joint_info.state_interfaces) {
      if (interface_info.name == hardware_interface::HW_IF_POSITION) {
        joint.position = initial_value(interface_info);
        data_->state_interfaces.emplace_back(
          joint.name, hardware_interface::HW_IF_POSITION, &joint.position);
      } else if (interface_info.name == hardware_interface::HW_IF_VELOCITY) {
        joint.velocity = initial_value(interface_info);
        data_->state_interfaces.emplace_back(
          joint.name, hardware_interface::HW_IF_VELOCITY, &joint.velocity);
      } else if (interface_info.name == hardware_interface::HW_IF_EFFORT) {
        joint.effort = initial_value(interface_info);
        data_->state_interfaces.emplace_back(
          joint.name, hardware_interface::HW_IF_EFFORT, &joint.effort);
      }
    }

    for (const auto & interface_info : joint_info.command_interfaces) {
      if (interface_info.name == hardware_interface::HW_IF_POSITION) {
        joint.position_command = joint.position;
        data_->command_interfaces.emplace_back(
          joint.name, hardware_interface::HW_IF_POSITION, &joint.position_command);
      } else if (interface_info.name == hardware_interface::HW_IF_VELOCITY) {
        joint.velocity_command = 0.0;
        data_->command_interfaces.emplace_back(
          joint.name, hardware_interface::HW_IF_VELOCITY, &joint.velocity_command);
      }
    }

    ecm.CreateComponent(joint.entity, sim::components::JointPositionReset({joint.position}));
    ecm.CreateComponent(joint.entity, sim::components::JointVelocityReset({joint.velocity}));
    RCLCPP_INFO(
      nh_->get_logger(), "%s nominal actuator: kp=%.3f, kd=%.3f, effort_limit=%.3f",
      joint.name.c_str(), joint.kp, joint.kd, joint.effort_limit);
  }

  RCLCPP_WARN(
    nh_->get_logger(),
    "Loaded nominal UF850 actuator dynamics. Gains and limits are simulation assumptions, "
    "not parameters identified from the physical arm.");
  return true;
}

CallbackReturn NominalActuatorSystem::on_init(
  const hardware_interface::HardwareInfo & system_info)
{
  return hardware_interface::SystemInterface::on_init(system_info);
}

CallbackReturn NominalActuatorSystem::on_configure(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  return CallbackReturn::SUCCESS;
}

CallbackReturn NominalActuatorSystem::on_activate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  for (auto & joint : data_->joints) {
    joint.position_command = joint.position;
    joint.velocity_command = 0.0;
  }
  return CallbackReturn::SUCCESS;
}

CallbackReturn NominalActuatorSystem::on_deactivate(
  const rclcpp_lifecycle::State & /*previous_state*/)
{
  for (const auto & joint : data_->joints) {
    auto * command = data_->ecm->Component<sim::components::JointForceCmd>(joint.entity);
    if (command != nullptr) {
      *command = sim::components::JointForceCmd({0.0});
    }
  }
  return CallbackReturn::SUCCESS;
}

std::vector<hardware_interface::StateInterface>
NominalActuatorSystem::export_state_interfaces()
{
  return std::move(data_->state_interfaces);
}

std::vector<hardware_interface::CommandInterface>
NominalActuatorSystem::export_command_interfaces()
{
  return std::move(data_->command_interfaces);
}

hardware_interface::return_type NominalActuatorSystem::read(
  const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
{
  for (auto & joint : data_->joints) {
    const auto * positions =
      data_->ecm->Component<sim::components::JointPosition>(joint.entity);
    const auto * velocities =
      data_->ecm->Component<sim::components::JointVelocity>(joint.entity);
    if (positions == nullptr || positions->Data().empty() ||
      velocities == nullptr || velocities->Data().empty())
    {
      return hardware_interface::return_type::ERROR;
    }
    joint.position = positions->Data()[0];
    joint.velocity = velocities->Data()[0];

    const auto * wrench =
      data_->ecm->Component<sim::components::JointTransmittedWrench>(joint.entity);
    if (wrench != nullptr) {
      gz::physics::Vector3d force_or_torque;
      if (joint.type == sdf::JointType::PRISMATIC) {
        force_or_torque = {
          wrench->Data().force().x(), wrench->Data().force().y(), wrench->Data().force().z()};
      } else {
        force_or_torque = {
          wrench->Data().torque().x(), wrench->Data().torque().y(), wrench->Data().torque().z()};
      }
      const auto axis = joint.axis.Xyz();
      joint.effort = force_or_torque.dot(
        gz::physics::Vector3d{axis[0], axis[1], axis[2]});
    }
  }
  return hardware_interface::return_type::OK;
}

hardware_interface::return_type NominalActuatorSystem::write(
  const rclcpp::Time & /*time*/, const rclcpp::Duration & /*period*/)
{
  for (const auto & joint : data_->joints) {
    const double desired_position = std::isfinite(joint.position_command) ?
      joint.position_command : joint.position;
    const double desired_velocity = std::isfinite(joint.velocity_command) ?
      joint.velocity_command : 0.0;
    const double raw_effort =
      joint.kp * (desired_position - joint.position) +
      joint.kd * (desired_velocity - joint.velocity);
    const double effort = std::clamp(raw_effort, -joint.effort_limit, joint.effort_limit);

    auto * command = data_->ecm->Component<sim::components::JointForceCmd>(joint.entity);
    if (command == nullptr) {
      data_->ecm->CreateComponent(joint.entity, sim::components::JointForceCmd({effort}));
    } else {
      *command = sim::components::JointForceCmd({effort});
    }
  }
  return hardware_interface::return_type::OK;
}

}  // namespace atom_xarm_dynamics

PLUGINLIB_EXPORT_CLASS(
  atom_xarm_dynamics::NominalActuatorSystem,
  gz_ros2_control::GazeboSimSystemInterface)
