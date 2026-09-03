cmake_minimum_required(VERSION 3.16)
project(atom_xarm_dynamics)

find_package(ament_cmake REQUIRED)
find_package(gz_sim_vendor REQUIRED)
find_package(gz-sim REQUIRED)
find_package(gz_ros2_control REQUIRED)
find_package(hardware_interface REQUIRED)
find_package(pluginlib REQUIRED)
find_package(rclcpp REQUIRED)
find_package(rclcpp_lifecycle REQUIRED)

add_library(atom_nominal_actuator_system SHARED
  src/nominal_actuator_system.cpp
)
target_compile_features(atom_nominal_actuator_system PUBLIC cxx_std_17)
target_compile_options(atom_nominal_actuator_system PRIVATE -Wall -Wextra -Wpedantic)
target_include_directories(atom_nominal_actuator_system PUBLIC
  $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
  $<INSTALL_INTERFACE:include>
)
target_link_libraries(atom_nominal_actuator_system PUBLIC
  gz-sim::gz-sim
  gz_ros2_control::gz_ros2_control-system
  hardware_interface::hardware_interface
  rclcpp::rclcpp
  rclcpp_lifecycle::rclcpp_lifecycle
)

pluginlib_export_plugin_description_file(
  gz_ros2_control atom_xarm_dynamics_plugins.xml
)

install(TARGETS atom_nominal_actuator_system
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)
install(DIRECTORY include/ DESTINATION include)
install(DIRECTORY config DESTINATION share/${PROJECT_NAME})

ament_package()
