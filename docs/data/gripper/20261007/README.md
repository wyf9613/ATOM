# 2026-10-07夹爪测量证据

这些文件是本机tmp采集记录的逐字节副本，供队友直接从Git读取。
manifest.json记录原路径、大小和SHA-256。JSON里的tmp来源路径仍保留，
其对应共享文件在此目录的同名会话子目录中。没有改写测量值或删掉异常。

- stationary_20261007：第一姿态3×30s，900有效样本，原空载基线。
- stationary_pose2_20261007：第二姿态3×30s，900有效样本。
- stationary_pose3_20261007：第三姿态3×30s，901有效样本。
- direct_stationary_20261007：Agent直接连接3×30s，888有效样本，包含启动与状态记录。
- empty_closure_20261007：基线、三个小步闭合平台、回程，每平台10s，各100有效样本；包含全部动作/退出回执。
- motor_20261007_144300_661483.jsonl：用户控制台原会话，包含之前的位置检查和姿态采集。

磁场CSV单位µT，position是encoder counts，load_raw不是N。
样本SD不是总不确定度。没有测力仪器参考或已部署力模型。
平台CSV主动排除运动/停稳间隔；全部间隔数据在controller/console JSONL里。

后续测试和模型接入事项见[交接文档](../../../GRIPPER_NEXT_TESTS.md)。
