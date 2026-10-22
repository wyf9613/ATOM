# RGB 与 RGB-D 各一例成功运行的精度对比

试验于 2026-09-25 在名义试管架场景下运行。预观察距离 0.35 m；任务为 Tag1 / pick，前端参考点距 `link_eef` 0.20 m，终点期望距 Tag 平面 0.10 m。每个模式按运行序号取第一例完整成功的运行；RGB 为第 4 次（种子 2026092504），RGB-D 为第 2 次（种子 2026092502）。两次种子不同，本报告仅描述样例，不估计方案成功率或跨运行稳定性。

另有团队实际完成的 10 次 RGB 测试，报告其中 4 次因规划失败终止（4/10，40%）；该组的逐次日志和条件尚未存入本仓库，故此结果作为独立的重复测试记录，不与下方两例成功运行的精度数据合并，也不据此比较 RGB 与 RGB-D 的成功率。

最终误差相对**独立理论几何**计算：理论 Tag1/Tag2 中心确定机架平面与水平切线，比较实际前端点与理论 Tag1 法线前方 0.10 m 目标；横向误差是沿机架切线的绝对偏移，前后误差是距平面 0.10 m 的绝对偏差。控制残差则相对第二段规划冻结的视觉估计目标，不能替代真实误差。

| 运行 | 真实横向误差 (mm) | 真实前后误差 (mm) | 真实水平位置误差 (mm) | 视觉目标控制残差 (mm) |
| --- | ---: | ---: | ---: | ---: |
| RGB | 1.431 | 12.491 | 12.573 | 0.008 |
| RGB-D | 4.684 | 10.598 | 11.587 | 1.896 |

过程定位误差对每一条有效选定 Tag 观测计算：`e = ||p_observed − p_theoretical||₂`，单位为 3D 位置距离。方差是**单次运行内各观测点**的样本方差（分母 `N−1`），单位 mm²；相邻帧相关，不能把 N 当作独立重复试验次数。

| 运行 | 接近段 | 有效观测点 N | 3D 误差均值 (mm) | 样本方差 (mm²) | RMSE (mm) | 最大误差 (mm) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| RGB | 对准 | 100 | 10.512 | 8.056 | 10.884 | 29.544 |
| RGB | 垂直接近 | 40 | 6.200 | 12.823 | 7.137 | 19.398 |
| RGB-D | 对准 | 98 | 9.494 | 7.890 | 9.897 | 20.564 |
| RGB-D | 垂直接近 | 40 | 5.255 | 10.035 | 6.115 | 16.694 |

两例观测在 `link_base` 的 y 方向均有正偏差：对准段 RGB / RGB-D 分别约 +9.6 / +8.8 mm；垂直接近段分别约 +6.2 / +5.2 mm。这与终点约 10–12 mm 的前后误差一致，提示应检查仿真 Tag 几何、相机外参和 PnP 标定。RGB-D 当前仍用 RGB 的 AprilTag PnP 求位姿，深度只记录质量；因此这些数字不能证明深度带来了定位增益。

原始运行目录：
- RGB：`/home/xinkai/Projects/ros2_ws/src/ATOM/tmp/camera_experiment/benchmark_20260925_10x/rgb_04`
- RGB-D：`/home/xinkai/Projects/ros2_ws/src/ATOM/tmp/camera_experiment/benchmark_20260925_10x/depth_02`

逐点误差：`/home/xinkai/Projects/ros2_ws/src/ATOM/tmp/camera_experiment/single_success_comparison_20260925/per_observation_errors.csv`。结构化结果：`/home/xinkai/Projects/ros2_ws/src/ATOM/tmp/camera_experiment/single_success_comparison_20260925/comparison.json`。
