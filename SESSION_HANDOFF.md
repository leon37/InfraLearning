# Session Handoff

更新时间：2026-05-12

## 1. 当前阶段

当前处于第二阶段 AI Infra 转型路线的第 15 周：

```text
训练数据路径、checkpoint、通信链路与混部扩展点
```

当前目标：

```text
在 TrainJob + Scheduler Plugin + DDP 端到端链路已经跑通的基础上，补齐训练任务的数据路径、checkpoint 恢复、通信链路和混部指标心智。
本阶段不追 CSI、NCCL、RDMA 专家深度，只建立能支撑平台研发和面试表达的边界理解。
```

相关项目：

```text
/home/leon/InfraLearning
/home/leon/AIInfraSchedulerPlugin
/home/leon/AIInfraTrainJob
/home/leon/AIInfraDDPLab
```

## 2. 必读文件

新 session 接手时先读：

```text
/home/leon/InfraLearning/AGENTS.md
/home/leon/InfraLearning/学习进度.md
/home/leon/InfraLearning/LAB_INDEX.md
/home/leon/InfraLearning/转型评估与规划基准.md
/home/leon/AIInfraTrainJob/config/samples/batch_v1_trainjob.yaml
/home/leon/AIInfraDDPLab/experiments/05_ddp_step_time.py
```

如需回顾刚完成的完整链路，再读：

```text
/home/leon/AIInfraSchedulerPlugin/pkg/plugin/node_label_score.go
/home/leon/AIInfraSchedulerPlugin/cmd/scheduler-plugin/scheduler-config.yaml
```

## 3. 已完成内容

第二阶段已完成：

```text
第 1-2 周：最小 scheduler plugin、schedulerName、PluginConfig、缺参失败策略。
第 3-4 周：GPU 资源模型、NUMA、TopologyManager、DeviceManager、GPU 拓扑调度策略文档。
第 5-6 周：TrainJob Controller 原型、gang scheduling、queue、PodGroup、Permit 状态边界。
第 7-8 周：PyTorch DDP 最小训练实验，理解 torchrun、rank、world size、process group、all-reduce、gradient sync。
第 9 周：DDP 通信瓶颈和指标采集，建立 step time、吞吐、数据路径和通信路径的一级归因。
第 10-12 周：TrainJob Operator v2 接入真实 DDP worker，完成 rank0 Service、worker env 注入、attempt 隔离、失败重试与 kind 验证。
第 13-14 周：TrainJob + Scheduler Plugin + DDP 完整链路演示已完成。
```

第 13-14 周最终结论：

```text
TrainJob Controller 能创建 worldSize 个 DDP worker Pod，并写入 schedulerName=my-custom-scheduler。
worker Pod 能写入 resources.requests.aiinfra.leon.com/gpu-capacity。
Node extended resource 通过 patch 写入 status.capacity/status.allocatable，用于模拟 Kubernetes 资源账本。
my-custom-scheduler 通过原生 NodeResourcesFit 判断 extended resource 是否足够。
NodeLabelFilter 原有逻辑本质是简化版 NodeResourcesFit，已从 profile 中移除，避免 label 与 allocatable 双账本。
NodeLabelScore 适配 Kubernetes v1.29 ScorePlugin 接口，通过 framework.Handle 读取 snapshot 中的 NodeInfo，并按 node_topological_hint 打分。
worker Pod 被成功 bind 到 Node 后，DDP worker 完成 init_process_group，输出 rank/world_size/step 指标，TrainJob 最终成功。
```

已形成的关键理解：

```text
requests 必须匹配 Node.status.allocatable，而不是匹配 Node label。
label-only 模拟适合观察插件链路，extended resource 模拟更接近 Kubernetes 真实资源模型。
informer 不是独立进程，而是 scheduler 进程内的 informer/reflector goroutine。
informer cache 保存 API Server 原始对象；scheduler cache 维护 NodeInfo、assumed Pod、nodeTree 等调度视图。
```

## 4. 当前断点

当前不是 scheduler 阻塞，而是进入训练平台的下一个问题：

```text
当前 DDP worker 只验证了进程启动和训练 step。
还没有外部数据集路径。
还没有 checkpoint 输出路径。
还没有验证 attempt 失败重试后 checkpoint 是否能保留。
还没有把训练数据、checkpoint、Pod 生命周期、Volume 生命周期串起来。
```

第 15 周第一步只处理一个问题：

```text
当前 TrainJob worker 如果把 checkpoint 写在容器本地文件系统里，attempt 重试后为什么无法恢复？
```

## 5. 下一步任务

下一步只做观察，不改代码：

```text
观察当前 worker Pod 的 volumes / volumeMounts / 启动参数，确认它是否存在持久化数据路径或 checkpoint 路径。
```

建议命令：

```text
kubectl get pod trainjob-sample-attempt-0-rank-0 -o jsonpath='{.spec.volumes}{"\n"}{.spec.containers[0].volumeMounts}{"\n"}{.spec.containers[0].args}{"\n"}'
kubectl get pod trainjob-sample-attempt-0-rank-1 -o jsonpath='{.spec.volumes}{"\n"}{.spec.containers[0].volumeMounts}{"\n"}{.spec.containers[0].args}{"\n"}'
```

观察字段：

```text
spec.volumes：Pod 声明了哪些卷。
spec.containers[0].volumeMounts：容器把卷挂到哪里。
spec.containers[0].args：worker 是否有 checkpoint 或 data 路径参数。
```

判定标准：

```text
如果 volumes / volumeMounts 为空，并且 args 里没有 checkpoint 路径，说明当前 worker 没有持久化训练状态。
如果 checkpoint 写在容器本地路径，Pod 删除或 attempt 重建后，这份状态会随旧 Pod 消失。
```

## 6. 交互约束

继续遵守：

```text
不要直接替用户完成项目演进代码，除非用户明确要求代改，或当前改动是修复阻塞性错误。
观察任务必须给出命令、字段和判定标准。
设计类问题不能把候选答案提前塞给用户。
文档整理默认由助手负责，用户主要负责观察现象、解释机制和完成关键代码改动。
```
