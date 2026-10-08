# AI Infra 知识补缺列表与学习路线

## 1. 文档定位

本文回答两个问题：

```text
AI Infra 版简历已经生成后，还缺哪些知识？
这些知识应该按什么顺序补，才不会陷入无止境学习？
```

当前原则：

```text
简历和项目闭环已经足够开始保守试水。
后续学习不再阻塞第一批投递，而是围绕 JD 高频追问边投边补。
```

本文不替代：

```text
docs/pre-interview-gap-closure-plan.md
docs/pre-interview-gap-closure-progress.md
AIInfra转型路线.md
```

前两者记录三项目投递前查漏补缺；`AIInfra转型路线.md` 是长期路线。本文是投递开始后的短中期补缺路线。

## 2. 当前能力边界

已经可以稳定表达的能力：

```text
TrainJob 控制面
Scheduler Plugin 接入
extended resource 模拟调度
DDP 启动契约
checkpoint PVC 写入
kind + CPU/Gloo 端到端 demo
Pending / Insufficient resource 排障
```

不能包装成已经具备的能力：

```text
真实 GPU 集群生产经验
NCCL / RDMA 性能优化经验
CUDA / Triton 算子优化经验
完整 gang scheduling 实现
完整 queue / quota / priority 平台对象模型
DCGM / Prometheus GPU 指标采集
vLLM / KServe 推理服务生产经验
多集群 / 多资源池调度经验
```

## 3. 知识补缺列表

| 优先级 | 知识缺口 | 当前状态 | 为什么要补 | 最小补法 | 验收标准 |
| --- | --- | --- | --- | --- | --- |
| P0 | AI Infra 版简历与项目讲法 | 已完成第一版 | 没有这个就无法开始投递 | 已生成 `2026-简历-李涛-AIInfra.pdf` | 能用 3 分钟讲清 TrainJob -> Scheduler -> DDP -> checkpoint |
| P1 | queue / quota / priority / preemption 对象边界 | 暂存 | 智算平台、算力调度、机器学习平台都会追问“资源有限时怎么排队” | 先写对象模型，不急着实现完整调度器 | 能说清哪些字段属于 TrainJob，哪些属于 Queue/Tenant，哪些由 scheduler 消费 |
| P1 | MLOps 对象模型 | 未系统化 | 字节、美团、机器学习平台岗位会问训练任务之外的 Dataset、Model、Serving 关系 | 画出 TrainJob、Dataset、Checkpoint、Model、ServingEndpoint 的关系 | 能解释一次训练产物如何进入模型注册、部署和回滚链路 |
| P1 | vLLM / 推理服务最小链路 | 未做 | 天翼云、米哈游、推理平台岗位高频出现 | 先做最小 HTTP serving + K8s Deployment + 指标观察；无 GPU 时只验证部署和平台语义 | 能说清推理服务和训练任务在生命周期、指标、资源使用上的差异 |
| P1 | NVIDIA device plugin / GPU 资源上报链路 | 只有边界认知 | 当前项目用 patch 模拟 extended resource，真实 GPU 岗位会追问资源从哪里来 | 阅读并复述 device plugin -> kubelet -> Node allocatable 链路，必要时用官方 device plugin YAML 做对象观察 | 能解释为什么 scheduler 不直接探测 GPU，以及 `nvidia.com/gpu` 如何进入 Node.status.allocatable |
| P1 | 平台指标：queue latency / running time / completion time | 未实现 | 项目现在能跑通，但缺少平台运营视角 | 给 TrainJob status 或文档补时间戳语义，先不做复杂 metrics pipeline | 能用指标解释排队慢、运行慢、完成慢分别对应什么层的问题 |
| P2 | DCGM / Prometheus GPU 指标入口 | 未做 | GPU 集群岗位会问利用率、显存、故障观测 | 先理解 DCGM Exporter 暴露什么指标，等有 GPU 环境再实操 | 能说清 GPU utilization、显存、temperature、XID error 等指标属于哪一层 |
| P2 | NCCL / all-reduce / 通信瓶颈 | Gloo/CPU 已验证 | 训练框架、云网络 AI Infra 会追问通信瓶颈 | 基于现有 DDP 实验补 all-reduce payload、bucket、NCCL 日志边界 | 能解释 init_process_group、all_reduce、DDP backward sync 的关系 |
| P2 | GPU 拓扑 / NUMA / NIC locality | 设计认知浅 | 调度策略从 label score 变深必须依赖拓扑和设备位置 | 先做拓扑字段设计，不急着依赖真实硬件 | 能说清为什么同样有 GPU，不同 Node 或同 Node 不同卡的通信成本不同 |
| P2 | controller-runtime 深水区 | 能写基本 controller | Operator 岗位会追问 condition、finalizer、status patch、幂等性 | 针对 TrainJob 补 finalizer / condition / status update 的设计边界文档 | 能解释 Reconcile 为什么必须幂等，status 和 spec 为什么分离 |
| P2 | scheduler framework 深水区 | 已接 Filter/Score | 调度岗位会追问 Reserve、Permit、PreBind、queue sort | 先补扩展点生命周期图，重点理解 Permit 与 gang scheduling 的关系 | 能解释为什么真正 gang scheduling 不是 controller 单独能完成的 |
| P3 | CSI / 训练数据路径 | PVC/checkpoint 已验证 | 训练平台会涉及 dataset、checkpoint、cache、远端存储 | 追踪 PVC -> PV -> StorageClass -> mount 的控制链路，暂不手写 CSI | 能区分 checkpoint、dataset、cache、本地盘、共享存储的角色 |
| P3 | 多集群 / 多资源池调度 | 只有概念 | 算力网、智算平台长期方向 | 先设计对象模型：Cluster、ResourcePool、Queue、TrainJob 的关系 | 能解释单集群 scheduler 与跨集群调度决策的边界 |
| P3 | 英文项目表达 | 未准备 | ByteDance 新加坡、LinkedIn 岗位需要 | 准备 2 分钟英文版项目介绍 | 能准确表达边界，不把 Gloo demo 说成 NCCL/GPU 经验 |
| P4 | RDMA / GPUDirect RDMA | 只有边界认知 | 顶级训练/云网络岗位需要，但短期投入大 | 暂不实操，只保留通信路径层次认知 | 能诚实说明当前没有实操经验，知道它属于多机 GPU 通信路径 |
| P4 | CUDA / Triton 算子 | 未做 | 训练框架内核和推理优化岗位需要 | 暂缓，不作为第一跳主线 | 不把它写进简历能力项 |

## 4. 学习路线

### 4.1 第一阶段：投递启动周

目标：

```text
开始投递，不再把继续学习当作投递前置条件。
```

本阶段只做三件事：

1. 使用 `2026-简历-李涛-AIInfra.pdf` 投第一批保守岗位。
2. 每个 JD 投递前确认团队方向、薪资薪数、是否外包。
3. 记录每个岗位的 JD 关键词和反馈问题。

第一批岗位优先级：

```text
华为 AI Infra
电信AI 机器学习平台 / 算力虚拟化
字节 AI 平台 SRE
芯动微电子 AI Infra
```

不要在本阶段补：

```text
RDMA
CUDA/Triton
完整 gang scheduler
完整 CSI provisioner
复杂前端平台页面
```

验收标准：

```text
完成第一批投递。
每个投递岗位都有一句“为什么我能投”和一句“我当前缺什么”。
```

### 4.2 第二阶段：平台对象模型补强

目标：

```text
把当前 demo 从“能跑通”推进到“像一个训练平台雏形”。
```

最小任务：

```text
设计 queue / quota / priority / preemption 的对象边界。
```

不要一开始写代码。先回答这些设计问题：

- 用户提交 TrainJob 时，应该声明自己属于哪个排队域？
- 资源上限应该挂在每个 TrainJob 上，还是挂在更高层的队列 / 租户对象上？
- scheduler 做决策时至少需要读到哪些信息？
- controller 应该把哪些排队原因和等待时间写回 status？

目标产物：

```text
docs/trainjob-queue-quota-priority-design.md
```

验收标准：

```text
能区分 queue、quota、priority、preemption。
能解释 priority 只影响等待队列顺序，和是否抢占已运行任务不是同一件事。
能说明当前 NodeLabelScore 不是继续堆 label，而是要上升到平台级调度约束。
```

### 4.3 第三阶段：MLOps 对象模型补强

目标：

```text
让项目能对齐机器学习平台岗位，而不是只像一个调度 demo。
```

最小任务：

```text
设计一次训练任务从数据到模型产物再到部署的对象关系。
```

对象至少覆盖：

```text
Dataset
TrainJob
Checkpoint
Model
ServingEndpoint
```

目标产物：

```text
docs/mlops-object-model.md
```

验收标准：

```text
能解释训练输入是什么、训练产物是什么、checkpoint 和 model artifact 的区别是什么。
能解释 ServingEndpoint 为什么不是 TrainJob 的一个 phase。
能把当前 TrainJob 项目嵌入更完整的平台链路里。
```

### 4.4 第四阶段：推理服务最小链路

目标：

```text
补上推理平台 JD 的最低沟通门槛。
```

最小任务：

```text
做一个最小推理服务部署实验。
```

无 GPU 环境下，不追求 vLLM 性能。先验证平台语义：

```text
模型服务进程
Kubernetes Deployment / Service
HTTP 请求
基础延迟和错误率指标
滚动更新或失败恢复
```

目标产物：

```text
../AIInfraServingLab
docs/inference-serving-minimal-lab.md
```

验收标准：

```text
能说清训练任务和推理服务的核心差异：
训练看 completion、checkpoint、step time；
推理看 latency、throughput、error rate、availability。
```

### 4.5 第五阶段：真实 GPU 资源入口认知

目标：

```text
把“patch Node 模拟资源”升级为“理解真实 GPU 如何进入 Kubernetes 资源账本”。
```

最小任务：

```text
补 NVIDIA device plugin 链路文档。
```

重点不是安装 GPU 环境，而是把链路讲清：

```text
device plugin
-> kubelet
-> Node.status.capacity / allocatable
-> scheduler cache
-> NodeResourcesFit
-> Pod bind
-> kubelet 分配设备给容器
```

目标产物：

```text
docs/gpu-device-plugin-resource-path.md
```

验收标准：

```text
面试官问“真实 GPU 资源从哪里来”时，能从节点侧组件讲到 scheduler 消费资源账本。
能承认当前 demo 用 patch 简化了 device plugin 层。
```

### 4.6 第六阶段：指标与可观测性

目标：

```text
把项目从功能闭环推进到平台可运营视角。
```

最小任务：

```text
补 TrainJob 平台指标设计。
```

先从控制面指标开始：

```text
submit_time
scheduled_time
start_time
completion_time
queue_latency
running_time
job_completion_time
retry_count
last_failure_reason
```

GPU 指标暂时只设计接入点：

```text
GPU utilization
显存
XID error
GPU temperature
```

目标产物：

```text
docs/trainjob-observability-metrics.md
```

验收标准：

```text
能解释为什么只看 Pod phase 不够。
能用 queue latency / running time / completion time 分别定位调度、训练运行和整体交付问题。
```

### 4.7 第七阶段：通信与 NCCL 边界补强

目标：

```text
让 DDP 项目在训练通信问题上更能抗追问。
```

最小任务：

```text
补 all-reduce / bucket / NCCL 日志的边界认知。
```

当前没有真实多 GPU 环境时，不追求 NCCL 性能结论。只补：

```text
init_process_group 和 collective operation 的关系
DDP backward 触发梯度同步的位置
bucket 对通信粒度的影响
NCCL 日志能看到哪些信息
为什么 Gloo/CPU 不能证明 NCCL/GPU 性能
```

目标产物：

```text
docs/ddp-nccl-followup.md
```

验收标准：

```text
面试官质疑 CPU/Gloo 太浅时，能把回答收回到启动契约和控制面；
面试官追问 NCCL 时，能说明下一步如何验证，而不是伪装成已经验证。
```

### 4.8 第八阶段：长期方向

目标：

```text
对齐更高阶 AI Infra / 算力平台岗位。
```

长期方向包括：

```text
多集群 / 多资源池调度
GPU/NIC/NUMA 拓扑感知调度
Kueue / Volcano / Koordinator 对象模型
CSI 与训练数据路径
DCGM / Prometheus / Grafana 指标体系
RDMA / GPUDirect RDMA 边界认知
vLLM 调度、KV cache、PagedAttention
```

执行原则：

```text
收到面试反馈后，按反馈选择其中一个点深入。
不要一次同时开多条深水区。
```

## 5. 推荐执行顺序

当前最推荐的顺序：

```text
1. 先投第一批岗位。
2. 补 queue / quota / priority 对象模型。
3. 补 MLOps 对象模型。
4. 补推理服务最小链路。
5. 补 NVIDIA device plugin 资源入口。
6. 补 TrainJob 指标与可观测性。
7. 补 NCCL / all-reduce 边界。
```

不推荐的顺序：

```text
先深挖 RDMA。
先学 CUDA/Triton。
先重写完整 scheduler。
先做复杂平台 UI。
先等全部补完再投递。
```

原因：

```text
这些方向重要，但短期不能最快提升初级 AI Infra / 机器学习平台 / 云原生训练平台岗位的命中率。
```

## 6. 下一件最小任务

下一件事不是再写一份长文档，而是：

```text
创建 docs/trainjob-queue-quota-priority-design.md，
只解决 queue / quota / priority / preemption 的对象边界。
```

验收问题：

```text
一个用户提交 TrainJob 时，哪些信息应该写在 TrainJob spec？
平台如何表达某个队列或租户最多能占多少资源？
priority 只改变等待顺序，还是会影响已经运行的任务？
scheduler 和 controller 分别消费或写回哪些字段？
```

这个问题解决后，当前项目会从“训练任务 demo”明显推进到“训练平台雏形”。
