FROM ros:jazzy-ros-base-noble

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

COPY ros2_ws/atom_xarm_jazzy.repos /tmp/atom_xarm_jazzy.repos
RUN mkdir -p /jazzy_ws/src \
    && vcs import /jazzy_ws/src < /tmp/atom_xarm_jazzy.repos \
    && git -C /jazzy_ws/src/xarm_ros2 submodule update --init --recursive \
    && rm /tmp/atom_xarm_jazzy.repos \
    && rosdep update --rosdistro jazzy \
    && rosdep install \
      --from-paths /jazzy_ws/src \
      --ignore-src \
      --rosdistro jazzy \
      --as-root apt:true \
      -r -y

RUN if getent group "${GROUP_ID}" >/dev/null; then \
      group_name="$(getent group "${GROUP_ID}" | cut -d: -f1)"; \
    else \
      groupadd --gid "${GROUP_ID}" atom; group_name=atom; \
    fi \
    && useradd --uid "${USER_ID}" --gid "${group_name}" --create-home --shell /bin/bash atom \
    && chown -R atom:"${GROUP_ID}" /jazzy_ws /home/atom

COPY docker/jazzy/entrypoint.sh /usr/local/bin/atom-jazzy-entrypoint
RUN chmod 0755 /usr/local/bin/atom-jazzy-entrypoint

USER atom
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/atom-jazzy-entrypoint"]
CMD ["bash"]
