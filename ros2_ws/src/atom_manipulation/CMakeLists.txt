cmake_minimum_required(VERSION 3.16)
project(atom_manipulation)

find_package(ament_cmake REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(moveit_core REQUIRED)
find_package(moveit_msgs REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(shape_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(tf2_msgs REQUIRED)

add_executable(grasp_task_node src/grasp_task_node.cpp)
target_compile_features(grasp_task_node PUBLIC cxx_std_17)
ament_target_dependencies(grasp_task_node
  geometry_msgs
  moveit_core
  moveit_msgs
  moveit_ros_planning_interface
  rclcpp
  sensor_msgs
  shape_msgs
  std_msgs
  tf2_msgs
)

install(TARGETS grasp_task_node DESTINATION lib/${PROJECT_NAME})

ament_package()
