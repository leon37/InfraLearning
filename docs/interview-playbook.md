# AI Infra 项目面试手册

## 1. 当前定位

当前项目适合支撑的岗位方向：

- Kubernetes Operator / Controller 研发
- 训练任务编排平台研发
- 云原生 AI 平台研发
- Scheduler Plugin 入门扩展
- 机器学习平台控制面研发
- 智算平台任务调度 / 资源管理
- 算力资源平台化 / 多集群资源管理的初级岗位

当前不应包装成：

- NCCL / RDMA 性能优化专家
- CUDA / GPU 算子优化工程师
- 真实大规模 GPU 集群调度负责人
- 大模型训练框架内核工程师

推荐对外定位：

```text
我主要从 Go 后端和 Kubernetes 控制面方向切入 AI Infra，当前项目重点是训练任务控制面、调度器扩展和 DDP worker 启动链路。我用本地 kind + Gloo 验证平台语义和 DDP 契约，知道这不能等同于真实 GPU/NCCL/RDMA 性能优化经验。
```

结合国家算力网方向，可以补充：

```text
我关注的不是单点训练脚本，而是 AI workload 如何被平台化管理：任务抽象、资源需求表达、调度策略、队列配额、状态聚合和可观测性。国家算力网强调算力资源统一接入、统一上报、统一调用和跨区域调度，我当前项目是单集群训练任务控制面的最小闭环，后续会向 queue/quota、多集群资源池和 GPU 指标方向补强。
```

## 2. 项目一句话

```text
我实现了一个基于 Kubernetes 的训练任务最小控制面：用户提交 TrainJob 后，controller 展开 DDP worker Pod，自定义 scheduler 接管调度，worker 通过 rank/world_size/master 契约加入 DDP 训练，rank0 将 checkpoint 写入 PVC，controller 聚合任务状态。
```

## 3. 3 分钟讲法

可以按这个顺序讲：

```text
这个项目解决的问题是：普通 Pod 或 Job 很难直接表达分布式训练任务的语义，比如 world size、rank 分配、rendezvous 地址、失败重试、调度器选择和 checkpoint。

我定义了一个 TrainJob CRD，由 controller 把它展开成多个 worker Pod，并为每个 Pod 注入 MASTER_ADDR、MASTER_PORT、RANK、WORLD_SIZE、LOCAL_RANK 等 DDP 启动环境变量。rank0 会通过一个 ClusterIP Service 暴露稳定 rendezvous 入口。

调度侧我实现了一个自定义 scheduler profile，TrainJob worker Pod 会设置 schedulerName=my-custom-scheduler。调度器使用 Kubernetes 原生 NodeResourcesFit 校验 extended resource，再用自定义 Score 插件根据节点标签做打分。

worker 镜像来自 DDP 实验项目，容器启动后运行 PyTorch 脚本，使用 Gloo backend 完成多 Pod DDP 训练，并输出 step time、max step time、吞吐等指标。rank0 还会把最小 checkpoint 写入 PVC。

这个项目验证的是训练平台控制面闭环，不是宣称解决真实 GPU/NCCL/RDMA 性能优化。真实 GPU 集群里还需要接入 NVIDIA device plugin、NCCL backend、RDMA 设备和拓扑感知调度。
```

## 4. 10 分钟展开版

### 4.1 控制面

核心对象：

```text
TrainJob
```

关键字段：

- `worldSize`：DDP worker 数量
- `masterPort`：rank0 rendezvous 端口
- `image` / `command` / `args`：worker 启动方式
- `resources`：每个 worker 的资源请求
- `schedulerName`：交给哪个 scheduler profile
- `checkpointSpec`：rank0 checkpoint PVC 和挂载路径

controller 做的事情：

```text
Watch TrainJob
创建 rank0 Service
创建 worldSize 个 worker Pod
注入 rank/world size/master 环境变量
注入 schedulerName 和 resources
按 attempt 隔离重试轮次
聚合 Pod 状态并更新 TrainJob.status
```

### 4.2 调度面

关键链路：

```text
worker Pod.spec.schedulerName=my-custom-scheduler
-> custom scheduler 接管
-> NodeResourcesFit 检查 resources.requests 与 Node.status.allocatable
-> NodeLabelScore 按 node_topological_hint 打分
-> bind 到目标 Node
```

重要结论：

```text
resources.requests 匹配的是 Node.status.allocatable，不是 Node label。
Node label 适合表达调度策略信号，不应冒充资源账本。
```

### 4.3 数据面

worker 做的事情：

```text
读取 MASTER_ADDR / MASTER_PORT / RANK / WORLD_SIZE
init_process_group(backend="gloo")
构造 DDP(model)
执行训练 step
输出 JSON 指标
rank0 写 checkpoint 到 /checkpoint
```

当前 checkpoint：

```text
rank0 挂 PVC
rank0 写 latest.pt
保存 model_state_dict、optimizer_state_dict、last_step、world_size
```

当前不做自动恢复：

```text
rank1 没有挂 PVC，不能直接读取 latest.pt。
完整恢复需要共享存储或由 rank0 广播参数和必要状态。
```

## 5. 高频追问

### Q1：为什么不用普通 Job？

普通 Job 主要表达 completions / parallelism 这类统计语义，不能直接表达 DDP 的 rank 分配、world size、rendezvous 地址、attempt 隔离和训练状态聚合。

TrainJob 的意义是把分布式训练任务作为一个整体对象管理，而不是让用户手工维护多个 Pod。

### Q2：为什么不用 StatefulSet？

第一版 DDP worker 只需要稳定 rendezvous 入口，不需要每个 worker 都有稳定网络身份。

当前采用：

```text
controller 直接创建 worker Pod
rank0 ClusterIP Service 提供 MASTER_ADDR
```

后续如果需要稳定成员身份、稳定 Pod DNS 或更复杂的重启语义，可以重新评估 StatefulSet。

### Q3：为什么 rank0 Service 用 ClusterIP？

当前 DDP 初始化只需要其他 rank 能通过一个稳定地址连接 rank0。

ClusterIP Service 能隐藏 rank0 Pod IP 变化，并通过 selector 指向当前 attempt 的 rank0 Pod。

### Q4：为什么 attempt 要进 label？

如果只用 `trainjob-name + rank=0` 选择 rank0，旧 attempt 的 rank0 Pod 尚未清理完成时，新 attempt 的 Service 可能误选旧 Pod。

`attempt` label 用于隔离同一 TrainJob 的不同重试轮次。

### Q5：schedulerName 不存在时 Pod 会怎样？

Pod 会保持 Pending。

默认 kube-scheduler 不会处理 `schedulerName=my-custom-scheduler` 的 Pod。只有对应 scheduler profile 启动后，才会接管这些 Pod。

### Q6：requests 为什么必须匹配 allocatable？

Kubernetes 原生资源调度使用的是资源账本：

```text
Pod.resources.requests
Node.status.allocatable
```

Node label 只是调度策略信号，不参与原生资源扣减。

### Q7：为什么移除 NodeLabelFilter？

原来的 `NodeLabelFilter` 用 label 模拟资源过滤，本质是手写简化版 `NodeResourcesFit`。

当项目切到 extended resource 路线后，资源过滤应该交给 Kubernetes 原生 `NodeResourcesFit`。保留 `NodeLabelFilter` 会造成 label 和 allocatable 两套资源账本。

### Q8：PVC 为什么一开始 Pending？

kind 默认 StorageClass 是 `rancher.io/local-path`，`volumeBindingMode=WaitForFirstConsumer`。

这表示 PVC 会等到第一个 Pod 使用它时，再根据 Pod 被调度到哪个 Node 创建并绑定 PV。

### Q9：RWO 为什么影响多节点 checkpoint？

`ReadWriteOnce` 的核心边界是一个卷只能被一个 Node 以读写方式挂载。

如果多个 worker Pod 分布在不同 Node，并且都想挂同一个 RWO PVC，会遇到挂载边界。

当前第一版只让 rank0 挂 PVC 并写 checkpoint，避免多 rank 并发写和 RWO 跨节点挂载问题。

### Q10：当前实验为什么不能证明 NCCL/RDMA 性能？

当前环境是：

```text
kind
CPU tensor
backend=gloo
Pod 网络
```

它能验证 DDP 启动契约和控制面链路，但不能验证：

```text
NCCL
CUDA tensor
RDMA / GPUDirect RDMA
真实多机 GPU scaling efficiency
```

## 6. 诚实边界

面试中需要主动说明：

```text
这个项目是本地 kind 环境下的训练平台控制面 demo。
它验证的是对象模型、controller、scheduler plugin、DDP 启动契约和 checkpoint PVC 链路。
它不等同于真实 GPU 集群性能优化经验。
```

如果被问到真实 GPU 集群下一步怎么做，可以回答：

```text
我会先接入 NVIDIA device plugin，让节点上报 nvidia.com/gpu，并让 Pod 真实请求 GPU。
然后把 worker 从 Gloo 切到 NCCL，使用 CUDA tensor 验证 GPU DDP。
再补 DCGM / Prometheus 指标，观察 GPU utilization、显存、step time、queue latency、job completion time。
调度侧再引入 GPU/NIC/NUMA 拓扑标签或设备信息，优化 worker 放置策略。
```

## 7. 简历项目表述草稿

项目名：

```text
基于 Kubernetes 的分布式训练任务控制面与调度扩展
```

项目描述：

```text
设计并实现 TrainJob CRD 与 controller，将分布式训练任务展开为多 Pod DDP worker，自动注入 rank/world size/master 等启动契约，并通过 schedulerName 接入自定义 scheduler profile。实现基于 extended resource 的资源调度链路和节点打分插件，完成 TrainJob -> Scheduler Plugin -> DDP worker -> checkpoint PVC -> status 聚合的端到端 demo。
```

可写亮点：

- 基于 controller-runtime 实现 TrainJob Reconcile 状态机
- 使用 rank0 ClusterIP Service 提供 DDP rendezvous 入口
- 使用 attempt label 隔离失败重试轮次
- 接入自定义 scheduler profile，验证 `schedulerName` 调度接管
- 使用 extended resource 模拟 GPU 容量资源账本
- 使用自定义 Score 插件实现节点偏好打分
- 支持 rank0 checkpoint PVC 挂载和最小 PyTorch checkpoint 写入
- 明确本地 Gloo/CPU demo 与真实 NCCL/RDMA/GPU 集群的边界

## 8. 当前短板

还需要补强：

- controller-runtime 细节追问
- scheduler framework 各扩展点生命周期
- GPU device plugin / NVIDIA stack 基础链路
- DCGM / Prometheus 指标采集
- queue latency、job completion time、GPU utilization 等平台指标
- 至少一个失败案例的完整复盘文档
- queue / quota / priority 的对象模型和最小实现
- 多集群 / 多资源池调度的基本心智
- 算力网语境下的资源统一接入、统一上报、统一调度表达

不建议继续横向扩展太多新主题。下一步更有价值的是把当前项目 README、架构图和失败案例补齐。

投递前按这份清单收口：

```text
docs/pre-interview-gap-closure-plan.md
```
