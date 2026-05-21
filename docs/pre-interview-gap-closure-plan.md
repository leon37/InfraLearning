# 三项目投递前查漏补缺清单

## 1. 文档定位

本文用于回答一个问题：

```text
在把 AIInfraTrainJob、AIInfraSchedulerPlugin、AIInfraDDPLab 写进简历之前，还必须补齐哪些薄弱点？
```

执行进度记录在：

```text
docs/pre-interview-gap-closure-progress.md
```

当前基准来自 2026-05-18 的模拟面试。结论是：已经具备 AI Infra 初级岗位的项目雏形，但表达和底层链路还不够稳。投递前不继续横向扩展太多新功能，先把已有三个项目讲清、跑稳、排障路径补齐。

投递前目标不是把项目包装成真实 GPU 集群平台，而是达到下面这个标准：

```text
能稳定讲清 TrainJob 控制面、Scheduler Plugin 调度面、DDP worker 数据面三条链路。
能说清哪些能力已经验证，哪些只是边界认知。
遇到 Pending、DDP 卡住、PVC 挂载、checkpoint 恢复这类追问时，有明确排查路径。
```

## 2. 当前薄弱点总览

| 方向 | 当前薄弱点 | 对面试的影响 | 补齐方式 |
| --- | --- | --- | --- |
| TrainJob Operator | gang scheduling、状态机、Watch/Reconcile 细节不够稳 | 面试官追问“为什么不是普通 Job”“rank1 Pending 会怎样”时容易失分 | 补状态流转表、失败场景复盘、gang scheduling 边界说明 |
| Scheduler Plugin | device plugin 链路、Filter/Score 边界、拓扑放置策略不够完整 | 面试官追问真实 GPU 资源从哪里来、为什么 label score 偏浅时容易卡住 | 补 Kubernetes 资源账本链路、Pending 排障链路、下一步调度增强路径 |
| DDPLab | checkpoint restore、torchrun 与 controller 职责切分、Gloo 与 NCCL 边界不够清晰 | 面试官追问“重试后怎么恢复”“为什么 CPU demo 有意义”时回答偏浅 | 补 checkpoint 恢复语义、DDP 启动契约、通信链路边界 |
| 端到端排障 | 只会说“看 Pod condition”，缺少对象顺序和字段定位 | 真实平台岗位很看重排障方法 | 补固定排障剧本和最小复现实验 |
| 平台化表达 | queue、quota、priority、指标还停留在概念层 | 面向智算平台岗位时项目显得像 demo | 补最小对象模型和验收现象，不急着实现完整平台 |

## 3. AIInfraTrainJob 查漏补缺

### 3.1 必须补稳的问题

当前要补的是控制面语义，不是再堆 CRD 字段。

必须能解释：

- `TrainJob` 为什么比直接写多个 Pod 更有意义。
- controller 如何通过 Watch 和 Reconcile 持续感知底层 Pod 状态。
- `Starting`、`Running`、`Succeeded`、`Failed` 的边界。
- rank0 已经 `Running`，rank1 一直 `Pending` 时，为什么 TrainJob 会卡住而不是自动失败。
- `retryLimit`、`attempt`、旧 worker Pod 清理、rank0 Service selector 之间的关系。
- 当前实现为什么不是真正的 gang scheduling。

### 3.2 补齐路径

第一步：补一张状态流转表。

位置建议：

```text
docs/trainjob-state-machine.md
```

表里至少覆盖这些输入现象：

- 所有 worker Pod 尚未创建。
- 部分 worker Pod `Pending`。
- 所有 worker Pod `Running` 或部分 `Running`。
- 部分 worker Pod `Succeeded`，部分仍在 `Running`。
- 所有 worker Pod `Succeeded`。
- 任意 worker Pod `Failed`，且未达到 `retryLimit`。
- 任意 worker Pod `Failed`，且达到 `retryLimit`。

验收标准：

```text
不看代码时，能说出每种 Pod 状态组合对应的 TrainJob phase。
能解释为什么 Pending 不等于 Failed。
能解释为什么 Starting 卡住暴露的是调度或资源问题，而不是训练脚本问题。
```

第二步：补一次失败场景复盘。

建议保留一个复盘文档：

```text
docs/failure-case-rank1-pending.md
```

复盘对象：

```text
rank0 Pod Running
rank1 Pod Pending
rank0 日志卡在 DDP 初始化
TrainJob phase 停在 Starting
```

必须记录的观察命令：

```bash
kubectl get trainjob trainjob-sample -o yaml
kubectl get pod -l trainjob-name=trainjob-sample -o wide
kubectl describe pod trainjob-sample-attempt-0-rank-1
kubectl get node -o jsonpath='{range .items[*]}{.metadata.name}{"\tallocatable="}{.status.allocatable.aiinfra\.leon\.com/gpu-capacity}{"\n"}{end}'
kubectl get endpoints trainjob-sample-attempt-0-rank-0
```

字段观察重点：

- `TrainJob.status.phase`
- `TrainJob.status.runningWorkers`
- `Pod.status.phase`
- `describe pod` 输出里的 `Events`、`Reason`、`Message`
- `Node.status.allocatable`
- rank0 Service 的 `Endpoints`

验收标准：

```text
能从 rank1 Pending 推导到 rank0 DDP 卡住。
能先排 scheduler/resource，再排 worker 代码。
能解释 Service endpoints 正确也不代表整个 DDP group 已经齐。
```

第三步：补 gang scheduling 边界。

当前不要求立刻实现完整 gang scheduling，但必须能说清：

```text
当前 controller 只是展开一组 Pod 并聚合状态。
真正的 gang scheduling 需要让 scheduler 在调度阶段知道“这组 Pod 要一起满足”。
只靠 controller 卡在 Starting，不能阻止 rank0 先占资源，也不能自动释放已占资源。
```

验收标准：

```text
能说出当前实现浅在哪里。
能说出下一步应从 scheduler 等待整组资源、准入、超时释放这些方向补。
不需要把 Permit 细节背下来，但要知道这是调度阶段的问题，不是单纯 Pod 创建问题。
```

## 4. AIInfraSchedulerPlugin 查漏补缺

### 4.1 必须补稳的问题

当前最容易被追问的不是 `NodeLabelScore` 怎么写，而是 Kubernetes 资源账本从哪里来。

必须能解释：

- `Pod.spec.schedulerName` 如何让指定 scheduler profile 接管 Pod。
- Filter 阶段判断“能不能调度”，Score 阶段判断“更偏好哪个节点”。
- extended resource 为什么应该通过 `Pod.resources.requests` 和 `Node.status.allocatable` 判断。
- `NodeLabelFilter` 为什么会造成 label 和 allocatable 两套账本。
- `NodeLabelScore` 为什么只是偏好排序，不是资源真实性判断。
- 真实 GPU 资源如何从节点侧进入 Node allocatable。

### 4.2 补齐路径

第一步：补一张资源账本链路图。

位置建议：

```text
docs/scheduler-resource-accounting.md
```

必须覆盖这条链路：

```text
节点侧组件发现设备
-> kubelet 获得该节点可用扩展资源
-> kubelet 更新 Node.status.capacity / Node.status.allocatable
-> scheduler informer/cache 看到 Node 资源账本
-> NodeResourcesFit 比较 Pod.requests 与 Node.allocatable
-> bind 成功后 scheduler cache 里的可用量发生变化
```

注意：这里的“节点侧组件”在真实 GPU 场景中通常是 NVIDIA device plugin 这一类设备插件。不要把它说成 scheduler 自己去机器上探测 GPU。

验收标准：

```text
能回答 scheduler 为什么看 API Server 里的 Node 资源账本，而不是 SSH 到每台机器探测。
能解释 capacity 和 allocatable 的差别。
能解释 Pod Pending 时为什么要同时看 Pod requests 和 Node allocatable。
```

第二步：补 Pending 排障剧本。

位置建议：

```text
docs/scheduler-pending-playbook.md
```

必须覆盖三个层次：

Pod 层：

```bash
kubectl describe pod trainjob-sample-attempt-0-rank-1
```

观察：

```text
Events
Reason
Message
spec.schedulerName
spec.containers[].resources.requests
```

Node 层：

```bash
kubectl get node -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.allocatable.aiinfra\.leon\.com/gpu-capacity}{"\n"}{end}'
```

观察：

```text
目标 extended resource 是否存在
数量是否足够
节点是否 Ready
```

Scheduler 层：

```text
查看 custom scheduler 进程日志
```

观察：

```text
是否接管到 schedulerName=my-custom-scheduler 的 Pod
Filter 是否给出 Unschedulable 原因
Score 是否执行
Bind 是否成功
```

验收标准：

```text
能按 Pod -> Node -> Scheduler 的顺序排查。
能把 Pending 和 DDP 卡住关联起来。
能说清“没有 Events”可能意味着对应 scheduler 没起来或没接管。
```

第三步：补调度增强路线。

当前不要求马上实现复杂调度算法，但必须能讲出下一步怎么变深：

```text
从 NodeLabelScore 这种静态偏好，推进到队列、优先级、配额、等待整组资源、调度延迟指标。
从单 Pod 打分，推进到 TrainJob 级别的资源需求和组调度语义。
从手工 patch extended resource，推进到真实 device plugin 上报链路认知。
```

验收标准：

```text
面试官说“label score 太浅”时，能承认它浅，同时讲清自己已经掌握 scheduler 主线。
能说出下一步不是继续换 label，而是引入平台级调度约束。
```

## 5. AIInfraDDPLab 查漏补缺

### 5.1 必须补稳的问题

DDPLab 现在已经能跑通，但面试里的风险是：只会说“Gloo 能跑”，说不清平台契约。

必须能解释：

- 普通 `torchrun` 在 DDP 启动中负责什么。
- TrainJob controller 替代了 `torchrun` 的哪一部分。
- `MASTER_ADDR`、`MASTER_PORT`、`RANK`、`WORLD_SIZE` 缺任意一个会怎样。
- 为什么 `MASTER_ADDR` 不应该让用户手填 Pod IP。
- rank0 Service selector 为什么必须带 attempt。
- 当前 checkpoint 只是持久化验证，不是完整恢复能力。

### 5.2 补齐路径

第一步：补 DDP 启动契约文档。

位置建议：

```text
docs/ddp-worker-contract.md
```

必须覆盖：

```text
torchrun 模式：启动器在本机拉起多个进程，并分配 rank/world_size/master。
Operator 模式：controller 创建多个 Pod，并把 rank/world_size/master 注入每个 Pod。
worker 脚本只负责读取环境变量并加入 process group。
```

验收标准：

```text
能说明 controller 没有替代完整 torchrun，只替代了跨 Pod 的启动参数分配。
能说明 1 Pod = 1 worker process 时 LOCAL_RANK 为什么是 0。
能说明 DDP 初始化卡住通常表示某些 rank 没有成功进入 group。
```

第二步：补 checkpoint 恢复边界。

位置建议：

```text
docs/checkpoint-restore-boundary.md
```

必须覆盖：

- `latest.pt` 至少应该包含：
  - `model_state_dict`
  - `optimizer_state_dict`
  - `last_step`
  - `world_size`
  - 后续可扩展随机数状态、数据迭代位置、训练参数版本
- `model_state_dict` 应该在 `DDP(model)` 之前加载。
- `optimizer_state_dict` 应该在 optimizer 创建之后加载。
- 当前只有 rank0 挂 PVC，因此 rank1 不能直接从 `/checkpoint/latest.pt` 读文件。
- rank0-only checkpoint 只能证明“能写入持久化存储”，不能证明“多 rank 自动恢复”。

验收标准：

```text
能回答只保存 model_state_dict 的问题：恢复后参数能回来，但优化器动量、学习率调度等训练状态丢失，继续训练不等价于原训练过程。
能回答 RWO PVC 跨 Node 的挂载边界。
能说明完整恢复需要共享存储，或 rank0 读取后广播必要状态。
```

第三步：补通信边界表达。

位置建议：

```text
docs/ddp-communication-boundary.md
```

必须覆盖：

```text
当前验证：kind、CPU tensor、Gloo、Pod 网络。
没有验证：CUDA tensor、NCCL、RDMA、GPUDirect RDMA、多机 GPU scaling。
当前项目的价值：验证平台如何启动、调度、追踪一个 DDP workload，而不是验证 GPU 通信性能。
```

验收标准：

```text
面试官质疑 CPU/Gloo 太弱时，能把价值收回到控制面和启动契约。
不会把项目包装成 GPU 通信优化经验。
能说出真实 GPU 版本下一步要接 NVIDIA device plugin、NCCL、DCGM/Prometheus 指标。
```

## 6. 端到端排障必须补的四个场景

投递前至少完成四份短复盘，每份不需要长，但必须包含现象、命令、关键字段、结论。

### 6.1 scheduler 未启动

现象：

```text
worker Pod Pending
Pod.spec.schedulerName=my-custom-scheduler
describe pod 里可能没有有效调度事件
```

验收：

```text
能判断默认 kube-scheduler 不会接管这个 Pod。
能通过启动 custom scheduler 让 Pod 继续流转。
```

### 6.2 extended resource 不足

现象：

```text
worker Pod Pending
Events 出现资源不足相关信息
```

验收：

```text
能对上 Pod.requests 和 Node.allocatable。
能解释 patch Node.status 只是本地模拟，真实环境由节点侧设备插件链路上报。
```

### 6.3 rank1 Pending 导致 rank0 DDP 卡住

现象：

```text
rank0 Running
rank1 Pending
rank0 日志停在 init_process_group 附近
```

验收：

```text
能解释这是 DDP group 没凑齐，不是 rank0 单独能继续训练。
```

### 6.4 PVC 写入成功但不能自动恢复

现象：

```text
local-path PV 背后能看到 latest.pt
重新创建 TrainJob 后脚本不会自动 load checkpoint
```

验收：

```text
能区分“持久化写入链路已通”和“训练自动恢复已实现”。
```

## 7. 投递前最小通过线

完成下面这些，再开始投初级岗位。

### 7.1 文档产物

至少补齐：

- `docs/trainjob-state-machine.md`
- `docs/failure-case-rank1-pending.md`
- `docs/scheduler-resource-accounting.md`
- `docs/scheduler-pending-playbook.md`
- `docs/ddp-worker-contract.md`
- `docs/checkpoint-restore-boundary.md`
- `docs/ddp-communication-boundary.md`

这些文档不是为了好看，而是为了让面试回答稳定。每份文档都应短，但必须有命令、字段和结论。

### 7.2 口头表达通过线

不看文档，能稳定回答：

```text
1. TrainJob 比普通 Job 多表达了什么训练语义？
2. rank0 Running、rank1 Pending 时为什么 DDP 会卡？
3. 当前为什么不是真正 gang scheduling？
4. schedulerName 如何让自定义 scheduler 接管 Pod？
5. Filter 和 Score 的边界是什么？
6. requests 为什么必须对应 Node allocatable？
7. 真实 GPU allocatable 大致从哪里来？
8. NodeLabelScore 为什么浅，下一步怎么变深？
9. torchrun 和 TrainJob controller 的职责怎么切分？
10. checkpoint latest.pt 里应该保存哪些东西？
11. rank0-only PVC checkpoint 为什么不等于完整恢复？
12. kind + Gloo demo 和真实 GPU/NCCL/RDMA 的边界是什么？
```

### 7.3 实操通过线

从空集群状态开始，能独立完成一次 demo：

```text
清理旧 TrainJob / Pod / Service
准备 Node extended resource
准备 PVC
启动 controller
启动 custom scheduler
创建 TrainJob
观察 worker 调度
观察 DDP 日志
观察 latest.pt 写入
观察 TrainJob 最终状态
```

同时能主动制造并解释一次失败：

```text
让 rank1 Pending，解释 rank0 为什么卡住。
或移除 extended resource，解释 Pod 为什么 Unschedulable。
```

## 8. 暂时不要做的事

投初级前不建议把时间花在这些方向：

- 深挖 NCCL 源码。
- 深挖 RDMA verbs。
- 手写完整 gang scheduler。
- 手写完整 CSI provisioner。
- 做复杂前端平台页面。
- 把 demo 包装成真实 GPU 集群生产经验。

这些方向不是不重要，而是当前收益低。现在更关键的是把已有链路讲稳、排障讲顺、边界讲诚实。

## 9. 完成后的简历表达边界

补齐之后，简历可以这样写：

```text
实现基于 Kubernetes 的分布式训练任务控制面 demo：定义 TrainJob CRD，由 controller 展开多 Pod DDP worker，注入 rank/world size/master 启动契约，通过 schedulerName 接入自定义 scheduler profile，并使用 extended resource 与 NodeResourcesFit 完成资源过滤，使用自定义 Score 插件完成节点偏好排序。worker 使用 Gloo 验证 DDP 启动链路，rank0 将 checkpoint 写入 PVC，controller 聚合 worker 状态。
```

面试中必须主动补充：

```text
当前实验环境是 kind + CPU/Gloo，主要验证 AI workload 控制面和调度接入链路，不等同于真实 GPU/NCCL/RDMA 性能优化经验。真实 GPU 平台下一步需要接入 NVIDIA device plugin、NCCL、GPU 指标采集、队列/配额/优先级和更完整的组调度机制。
```
