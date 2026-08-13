cmake_minimum_required(VERSION 3.16)
project(atom_gripper_description)

find_package(ament_cmake REQUIRED)

install(
  DIRECTORY launch meshes urdf worlds
  DESTINATION share/${PROJECT_NAME}
  PATTERN "__pycache__" EXCLUDE
  PATTERN "*.pyc" EXCLUDE
)

install(
  PROGRAMS
    scripts/demo_motion.py
    scripts/extract_step_meshes.py
    scripts/grasp_lift_test.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(description_test test/test_description.py)
endif()

ament_package()
