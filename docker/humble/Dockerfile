FROM ros:humble-ros-base-jammy

ARG DEBIAN_FRONTEND=noninteractive
ARG USER_ID=1000
ARG GROUP_ID=1000

ENV ROS_DISTRO=humble
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8
ENV GZ_VERSION=fortress
ENV IGNITION_VERSION=fortress

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      git \
      locales \
      python3-ament-package \
      python3-colcon-common-extensions \
      python3-pytest \
      python3-rosdep \
      python3-vcstool \
      liburdfdom-tools \
      ros-humble-ament-cmake-pytest \
      ros-humble-joint-state-publisher \
      ros-humble-joint-state-publisher-gui \
      ros-humble-ign-ros2-control \
      ros-humble-ros2-controllers \
      ros-humble-ros2controlcli \
      ros-humble-launch-testing-ament-cmake \
      ros-humble-launch-testing-ros \
      ros-humble-moveit \
      ros-humble-robot-state-publisher \
      ros-humble-ros-gz \
      ros-humble-rviz2 \
      ros-humble-tf2-tools \
      ros-humble-urdf \
      ros-humble-xacro \
    && locale-gen en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

RUN if getent group "${GROUP_ID}" >/dev/null; then \
      group_name="$(getent group "${GROUP_ID}" | cut -d: -f1)"; \
    else \
      groupadd --gid "${GROUP_ID}" atom; group_name=atom; \
    fi \
    && useradd --uid "${USER_ID}" --gid "${group_name}" --create-home --shell /bin/bash atom

COPY ros2_ws/atom_sim_humble.repos /tmp/atom_sim_humble.repos
RUN mkdir -p /humble_ws/src \
    && vcs import /humble_ws/src < /tmp/atom_sim_humble.repos \
    && rm /tmp/atom_sim_humble.repos \
    && chown -R atom:"${GROUP_ID}" /humble_ws /home/atom

COPY docker/humble/entrypoint.sh /usr/local/bin/atom-humble-entrypoint
RUN chmod 0755 /usr/local/bin/atom-humble-entrypoint

USER atom
RUN rosdep update --rosdistro humble

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/atom-humble-entrypoint"]
CMD ["bash"]
