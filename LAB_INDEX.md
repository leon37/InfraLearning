# 实验索引 (LAB_INDEX)

| 路线周次 | 核心概念 | 实验目录 | 关键笔记/文档 |
| :--- | :--- | :--- | :--- |
| **第一阶段** | | | |
| Week 1-4 | Docker 运行时与存储 | `docker/` | `archive/progress_stage_1.md` |
| Week 5 | Namespace 底层代码 | `docker/uts`, `docker/pid`, `docker/mount` | `archive/progress_stage_1.md` |
| Week 7-12 | K8s 对象与控制面链路 | - | `archive/progress_stage_1.md` |
| **第二阶段** | | | |
| Week 1-4 | Scheduler Plugin & GPU 拓扑 | `../AIInfraSchedulerPlugin` | `GPUTopologicalScheduleStrategy.md` |
| Week 5-6 | Batch Job & Gang Scheduling | `../AIInfraTrainJob` | `学习进度.md` |
| Week 7-8 | DDP 训练实验平台 | `../AIInfraDDPLab` | `../AIInfraDDPLab/docs/stage-01-process-group.md`, `../AIInfraDDPLab/docs/stage-02-ddp-gradient-sync.md`, `../AIInfraDDPLab/docs/stage-03-step-time.md`, `../AIInfraDDPLab/docs/stage-04-ddp-worker-contract.md`, `../AIInfraDDPLab/docs/stage-05-ddp-deepspeed-megatron-boundary.md` |
| Week 9 | DDP 通信瓶颈与指标采集 | `../AIInfraDDPLab` | `../AIInfraDDPLab/docs/stage-06-metric-diagnosis.md`, `../AIInfraDDPLab/experiments/06_all_reduce_payload.py` |
| Week 10-12 | TrainJob Operator v2 接入 DDP worker | `../AIInfraDDPLab`, `../AIInfraTrainJob` | `../AIInfraDDPLab/docs/stage-07-platform-semantics.md`, `学习进度.md` |
| Week 13-14 | Scheduler Plugin + TrainJob + DDP 完整链路 | `../AIInfraSchedulerPlugin`, `../AIInfraTrainJob`, `../AIInfraDDPLab` | `学习进度.md`, `../AIInfraSchedulerPlugin/cmd/scheduler-plugin/scheduler-config.yaml`, `../AIInfraSchedulerPlugin/pkg/plugin/node_label_score.go` |
| Week 15 | checkpoint、PVC、通信链路边界 | `../AIInfraTrainJob`, `../AIInfraDDPLab`, `docs/` | `docs/aiinfra-demo.md`, `学习进度.md` |

## 快速导航
- [主路线图](./AIInfra转型路线.md)
- [当前进度](./学习进度.md)
- [AI Infra Demo](./docs/aiinfra-demo.md)
- [面试手册](./docs/interview-playbook.md)
- [转型评估](./转型评估与规划基准.md)
- [核心指令](./AGENTS.md)
