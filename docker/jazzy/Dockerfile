FROM ros:jazzy-ros-base-noble@sha256:2589a8fba5257307857890173c069852c2abf913a0be7970f172478baecb09e4

ARG DEBIAN_FRONTEND=noninteractive
ARG USER_ID=1000
ARG GROUP_ID=1000

ENV ROS_DISTRO=jazzy
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates \
      git \
      liburdfdom-tools \
      locales \
      python3-colcon-common-extensions \
      python3-rosdep \
      python3-vcstool \
      ros-jazzy-gz-ros2-control \
      ros-jazzy-joint-state-publisher \
      ros-jazzy-moveit \
      ros-jazzy-robot-state-publisher \
      ros-jazzy-ros-gz \
      ros-jazzy-ros2-controllers \
      ros-jazzy-ros2controlcli \
      ros-jazzy-rviz2 \
      ros-jazzy-tf2-tools \
      ros-jazzy-urdf \
      ros-jazzy-xacro \
    && locale-gen en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

# Ubuntu 24.04 images can already contain an `ubuntu` user with UID 1000.
# Reuse that account when its UID matches the invoking host user.
RUN existing_user="$(getent passwd "${USER_ID}" | cut -d: -f1 || true)" \
    && if [ -n "${existing_user}" ] && [ "${existing_user}" != "atom" ]; then \
      usermod --login atom --home /home/atom --move-home "${existing_user}"; \
    fi \
    && if getent group "${GROUP_ID}" >/dev/null; then \
      group_name="$(getent group "${GROUP_ID}" | cut -d: -f1)"; \
    else \
      groupadd --gid "${GROUP_ID}" atom; group_name=atom; \
    fi \
    && if getent passwd atom >/dev/null; then \
      usermod --gid "${group_name}" --shell /bin/bash atom; \
    else \
      useradd --uid "${USER_ID}" --gid "${group_name}" --create-home --shell /bin/bash atom; \
    fi

COPY ros2_ws/atom_xarm_jazzy.repos /tmp/atom_xarm_jazzy.repos
RUN mkdir -p /jazzy_ws/src \
    && vcs import /jazzy_ws/src < /tmp/atom_xarm_jazzy.repos \
    && git -C /jazzy_ws/src/xarm_ros2 submodule update --init --recursive \
    && rm /tmp/atom_xarm_jazzy.repos \
    && chown -R atom:"${GROUP_ID}" /jazzy_ws /home/atom

ENV ROS_HOME=/home/atom/.ros

RUN su -s /bin/bash atom -c 'rosdep update --rosdistro jazzy' \
    && rosdep install \
      --from-paths \
        /jazzy_ws/src/xarm_ros2/uf_ros_lib \
        /jazzy_ws/src/xarm_ros2/xarm_msgs \
        /jazzy_ws/src/xarm_ros2/xarm_sdk \
        /jazzy_ws/src/xarm_ros2/xarm_description \
        /jazzy_ws/src/xarm_ros2/xarm_api \
        /jazzy_ws/src/xarm_ros2/xarm_controller \
        /jazzy_ws/src/xarm_ros2/xarm_gazebo \
        /jazzy_ws/src/xarm_ros2/xarm_moveit_config \
      --ignore-src \
      --rosdistro jazzy \
      --as-root apt:true \
      -r -y

COPY docker/jazzy/entrypoint.sh /usr/local/bin/atom-jazzy-entrypoint
RUN chmod 0755 /usr/local/bin/atom-jazzy-entrypoint

USER atom
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/atom-jazzy-entrypoint"]
CMD ["bash"]
