# InfraLearning

这是一个面向容器底层、Kubernetes 控制面与 AI Infra 训练平台方向的学习仓库。

## 当前主线

当前阶段是 AI Infra 转型路线，主线收敛为三个项目：

- `../AIInfraTrainJob`：训练任务控制面，负责 TrainJob CRD、controller、worker Pod 编排、状态聚合和 checkpoint 挂载。
- `../AIInfraSchedulerPlugin`：自定义调度面，负责 scheduler profile、extended resource 过滤和节点打分。
- `../AIInfraDDPLab`：DDP worker 数据面，负责训练脚本、DDP 启动契约、指标输出和 checkpoint 写入。

## 重要文档

- [学习进度](./学习进度.md)：当前阶段、最近实验记录和下一步。
- [实验索引](./LAB_INDEX.md)：按周次映射核心概念、代码路径和关键文档。
- [AI Infra 训练平台最小闭环 Demo](./docs/aiinfra-demo.md)：三个项目的端到端 demo 说明、启动顺序、验收命令和边界。
- [AI Infra 项目面试手册](./docs/interview-playbook.md)：项目讲法、高频追问、诚实边界和简历表述草稿。
- [AI Infra 转型路线](./AIInfra转型路线.md)：长期路线和阶段目标。
- [转型评估与规划基准](./转型评估与规划基准.md)：岗位定位、优先级和项目收口原则。
- [第一阶段归档](./archive/progress_stage_1.md)：Docker 与 Kubernetes 基础阶段记录。

## 当前 demo 一句话

用户提交 `TrainJob` 后，controller 展开 DDP worker Pod 并注入启动契约，自定义 scheduler 接管 `schedulerName=my-custom-scheduler` 的 Pod 完成调度，worker 使用 Gloo 跑多 Pod DDP，rank0 将 checkpoint 写入 PVC。

当前本地实验使用 kind + CPU/Gloo，只验证平台控制面和 DDP 契约，不声称覆盖真实 GPU/NCCL/RDMA 性能。
