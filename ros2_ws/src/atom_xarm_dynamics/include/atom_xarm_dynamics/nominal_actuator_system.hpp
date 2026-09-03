#ifndef ATOM_XARM_DYNAMICS__NOMINAL_ACTUATOR_SYSTEM_HPP_
#define ATOM_XARM_DYNAMICS__NOMINAL_ACTUATOR_SYSTEM_HPP_

#include <map>
#include <memory>
#include <string>
#include <vector>

#include "gz_ros2_control/gz_system_interface.hpp"
#include "rclcpp_lifecycle/node_interfaces/lifecycle_node_interface.hpp"

namespace atom_xarm_dynamics
{

using CallbackReturn = rclcpp_lifecycle::node_interfaces::LifecycleNodeInterface::CallbackReturn;

class NominalActuatorSystemPrivate;

class NominalActuatorSystem : public gz_ros2_control::GazeboSimSystemInterface
{
public:
  CallbackReturn on_init(const hardware_interface::HardwareInfo & system_info) override;
  CallbackReturn on_configure(const rclcpp_lifecycle::State & previous_state) override;
  CallbackReturn on_activate(const rclcpp_lifecycle::State & previous_state) override;
  CallbackReturn on_deactivate(const rclcpp_lifecycle::State & previous_state) override;

  std::vector<hardware_interface::StateInterface> export_state_interfaces() override;
  std::vector<hardware_interface::CommandInterface> export_command_interfaces() override;

  hardware_interface::return_type read(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;
  hardware_interface::return_type write(
    const rclcpp::Time & time, const rclcpp::Duration & period) override;

  bool initSim(
    rclcpp::Node::SharedPtr & model_nh,
    std::map<std::string, sim::Entity> & joints,
    const hardware_interface::HardwareInfo & hardware_info,
    sim::EntityComponentManager & ecm,
    unsigned int update_rate) override;

private:
  std::unique_ptr<NominalActuatorSystemPrivate> data_;
};

}  // namespace atom_xarm_dynamics

#endif  // ATOM_XARM_DYNAMICS__NOMINAL_ACTUATOR_SYSTEM_HPP_
