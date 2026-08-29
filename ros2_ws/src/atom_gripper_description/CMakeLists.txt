cmake_minimum_required(VERSION 3.16)
project(atom_gripper_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY meshes urdf
  DESTINATION share/${PROJECT_NAME}
)

install(
  PROGRAMS scripts/extract_step_meshes.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(description_test test/test_description.py)
endif()

ament_package()
