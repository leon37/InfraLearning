# AI Infra 转型路线

## 1. 文档定位

这份路线不是替代现有的 `学习路线.md`，而是建立在当前已完成的 Docker / Kubernetes / 容器底层主线之上，面向以下目标岗位继续转型：

- 大规模 GPU 集群全局资源调度
- RDMA 高速网络、分布式存储与训练任务协同优化
- 基于 Kubernetes 的训练/推理平台建设
- 调度器、CSI、CRD、混部、容灾与高可用能力建设

默认前置条件：

- 已完成当前仓库中的 12 周 Docker / Kubernetes 基础主线
- 已能解释 `kubectl -> apiserver -> etcd -> scheduler -> kubelet -> containerd -> runc -> CNI / kube-proxy -> Linux 内核`

这份路线的核心目标不是“再学一遍 K8s”，而是补齐 AI Infra 岗位真正要求的三条能力：

1. 调度能力：从会用调度器，升级到能设计和实现调度策略
2. 训练能力：从会跑容器，升级到能定位训练任务的通信/存储/计算瓶颈
3. 平台能力：从会做实验，升级到能设计训练平台的对象模型、控制面与数据面

## 2. 总体阶段图

### Phase A：GPU 与调度器深化

目标：

- 把通用 K8s 调度理解推进到 GPU / NUMA / topology-aware 调度
- 能读懂并实现 scheduler framework 插件
- 建立 batch job / gang scheduling / queue / preemption 的系统心智

### Phase B：分布式训练与 HPC 基础

目标：

- 理解 PyTorch DDP / DeepSpeed / Megatron 这类训练框架到底在协调什么
- 建立通信、并行、同步、all-reduce、checkpoint 的性能心智
- 理解 RDMA / NCCL / MPI / OpenMP 在 AI 训练里的位置

### Phase C：存储、数据路径与 CSI

目标：

- 理解训练任务为什么经常被存储拖慢
- 理解 CSI controller / node plugin、VolumeAttachment、挂载链
- 理解 checkpoint、dataset cache、本地 NVMe 与远端分布式存储的取舍

### Phase D：AI 平台控制面与混部

目标：

- 用 CRD + controller + scheduler plugin 搭训练任务控制面
- 理解训练/推理混部、配额、优先级、抢占、容灾、重试
- 建立“集群利用率优化”而不是“只把任务跑起来”的平台视角

### Phase E：大规模集群优化与面试收口

目标：

- 形成 GPU 集群利用率优化、网络拓扑优化、存储协同优化的方法论
- 收敛成可讲可演示的 3 个核心项目
- 为 AI Infra 岗位技术面试准备系统化输出

## 3. 16 周详细路线

### 第 1-2 周：Kubernetes 调度器框架与 GPU 调度入口

应用目标：

- 跑通 scheduler framework 的最小插件
- 理解 `Filter`、`Score`、`Reserve`、`Permit`、`Bind`
- 理解默认调度与扩展调度的边界

底层目标：

- 理解 scheduler cache、node info、pod info、framework plugin 调用链
- 理解 device plugin、extended resource、GPU 资源上报的基本路径

输出要求：

- 用自己的话解释“默认 scheduler 为什么不够支撑大规模 GPU 集群”

建议项目：

- 项目 A1：最小 scheduler plugin
  功能：基于节点标签、GPU 数量或显存余量做打分
  验收：能解释每个 Pod 为什么调度到当前节点

### 第 3-4 周：GPU 资源模型、NUMA、拓扑感知调度

应用目标：

- 理解 GPU、CPU、内存、NUMA、PCIe、网卡拓扑如何一起影响训练性能
- 理解 MIG、拓扑感知、binpack/spread、碎片化问题

底层目标：

- 理解 `TopologyManager`、`DeviceManager`、NUMA affinity 等基本机制
- 建立“显卡不是整数资源”这件事的心智

输出要求：

- 能解释“为什么 GPU 利用率低，不一定是训练代码问题，也可能是调度问题”

建议项目：

- 项目 A2：GPU 拓扑感知调度策略设计文档
  功能：针对单机多卡和跨机通信，定义节点标签、打分项、反亲和策略
  验收：能把策略翻译成 scheduler plugin 的 `Filter/Score` 逻辑

### 第 5-6 周：批任务调度、队列、抢占与 Gang Scheduling

应用目标：

- 理解训练任务为什么常常不是普通 Deployment 语义
- 理解 queue、priority、preemption、gang scheduling 的必要性

底层目标：

- 理解 Volcano / Kueue / Koordinator 这类框架的对象模型和控制逻辑
- 理解“资源足够但任务不该立刻启动”的调度语义

输出要求：

- 能解释训练任务为什么需要“整组副本同时就绪”的调度模型

建议项目：

- 项目 A3：训练任务队列 CRD
  功能：支持 `queue`、`priority`、`minAvailable`、`retryPolicy`
  验收：能表达一个最小的 gang scheduling 任务语义

### 第 7-8 周：PyTorch DDP / DeepSpeed / Megatron 训练栈

应用目标：

- 跑通最小 DDP 训练
- 理解 DeepSpeed / Megatron 解决的问题边界
- 理解 data parallel / model parallel / pipeline parallel 的差异

底层目标：

- 理解 process group、rank、world size、all-reduce、gradient sync
- 理解训练吞吐、step time、通信占比、checkpoint 开销

输出要求：

- 能解释训练性能瓶颈落在计算、通信、存储中的哪一段

建议项目：

- 项目 B1：最小分布式训练实验框架
  功能：同一模型分别跑单机、DDP、DeepSpeed
  验收：至少输出吞吐、step time、GPU 利用率、通信耗时

### 第 9-10 周：RDMA / NCCL / MPI / OpenMP 基础

应用目标：

- 建立 HPC 基础心智，不再把 RDMA 只当“更快的网卡”
- 理解 NCCL、MPI、OpenMP 分别处在哪一层

底层目标：

- 理解零拷贝、低延迟通信、collective communication 的本质
- 理解 RoCE / InfiniBand / GPUDirect RDMA 在训练里的意义

输出要求：

- 能解释“为什么训练任务在多节点扩展后吞吐不升反降”

建议项目：

- 项目 B2：通信瓶颈定位实验
  功能：对比不同 world size / batch size / gradient accumulation 下的训练效率
  验收：形成一份通信瓶颈归因报告

### 第 11-12 周：CSI、分布式存储与训练数据路径

应用目标：

- 理解 CSI 的 controller / node 分工
- 理解训练任务中的 dataset、checkpoint、cache、远端存储路径

底层目标：

- 理解 `PVC/PV/StorageClass/VolumeAttachment`
- 理解本地 NVMe、共享文件系统、对象存储、分布式缓存的不同角色

输出要求：

- 能解释训练数据和 checkpoint 为什么不能简单等同于“挂一个 volume”

建议项目：

- 项目 C1：最小 CSI 心智实验
  功能：追踪一次 volume create / attach / mount 的完整链路
  验收：能说明 controller 插件和 node 插件为什么分开

### 第 13-14 周：训练平台控制面、CRD 与任务编排

应用目标：

- 设计训练任务 CRD
- 用 controller 落任务状态机
- 理解失败重试、作业恢复、任务生命周期管理

底层目标：

- 理解 CRD、controller-runtime、reconcile loop、finalizer、conditions
- 理解“训练任务不是一个 Pod，而是一组对象状态机”

输出要求：

- 能给出一个最小训练平台控制面的对象模型

建议项目：

- 项目 D1：训练任务平台最小控制面
  功能：`TrainJob` CRD + controller + 状态流转
  验收：能表达 Submitted / Queued / Scheduling / Running / Failed / Retrying / Succeeded

### 第 15 周：在线/离线混部、优先级、容灾与可观测性

应用目标：

- 理解在线推理与离线训练的冲突点
- 理解配额、优先级、抢占、重试、容灾
- 理解监控指标如何反过来驱动调度优化

底层目标：

- 理解 GPU utilization、queue latency、job completion time、fragmentation 这些指标的意义
- 理解节点故障、网络抖动、存储异常时任务该如何恢复

输出要求：

- 能解释“高可用调度框架”到底高可用在哪里

建议项目：

- 项目 D2：训练/推理混部仿真
  功能：模拟在线低延迟服务与离线训练任务共享 GPU 资源
  验收：用指标说明调度策略前后差异

### 第 16 周：项目收口与面试表达

应用目标：

- 把前面项目压缩成 3 个最强项目
- 形成可用于技术面试的系统表达

底层目标：

- 训练“从现象 -> 指标 -> 归因 -> 机制 -> 优化策略”的表达链
- 避免只会讲对象名词，不会讲调度与系统约束

输出要求：

- 能完整讲清一条 AI Infra 训练任务从提交到运行再到优化的链路

## 4. 核心项目组合

如果只做 3 个项目，优先做这 3 个：

### 项目 P1：GPU 调度器插件

目标：

- 证明你不是只会用 Kubernetes，而是真的能扩展调度器

建议能力点：

- scheduler framework
- 节点打分
- GPU / NUMA / topology-aware
- queue / priority / preemption 基础

最终交付：

- 插件代码
- 调度决策说明
- 指标对比结果

### 项目 P2：分布式训练实验平台

目标：

- 把云原生和训练栈真正接起来

建议能力点：

- PyTorch DDP / DeepSpeed
- 多机训练启动
- 吞吐与通信瓶颈分析
- 网络 / 存储 / 资源约束下的实验对比

最终交付：

- 训练实验脚本与部署清单
- 指标采集
- 训练性能分析报告

### 项目 P3：训练任务控制面

目标：

- 证明你具备平台 owner 视角

建议能力点：

- `TrainJob` CRD
- controller
- 队列、重试、优先级、状态机
- 与调度器、运行时、存储链路协作

最终交付：

- CRD 设计
- controller 原型
- 一份完整任务生命周期演示

## 5. 与当前基础路线的衔接关系

你当前已经完成的内容，对应转型路线中的前置能力如下：

- Docker / namespace / cgroup / OverlayFS
  对应 AI Infra 中的 runtime、rootfs、隔离与资源限制理解
- Pod / Deployment / Service / kube-proxy / CNI
  对应训练平台中的对象模型、网络模型、服务发现与调度基础
- scheduler / kubelet / containerd / runc / pause sandbox
  对应训练任务在控制面与节点执行面之间的实际落地路径

因此你接下来不需要再回头补通用 K8s 入门，而应直接切入：

1. 调度器扩展
2. 分布式训练
3. RDMA / 通信
4. CSI / 存储
5. 训练平台控制面

## 6. 学习方式要求

这一阶段不再适合只靠“读概念”推进，必须改成三线并行：

- 机制线：scheduler / kubelet / CNI / CSI / runtime 源码与调用链
- 实验线：训练任务、性能指标、网络/存储瓶颈实验
- 项目线：调度器插件、训练任务 CRD、平台控制面

每一阶段都必须输出：

- 一个最小可运行实验
- 一个可讲清楚的机制链
- 一个能放在简历里的项目成果

## 7. 第二阶段进度模板

建议新增独立进度文件，例如：

- `AIInfra学习进度.md`

每次记录至少包含：

### 本次主题

- 实验目标：
- 关键入口：
- 观察到的现象：
- 当前结论：
- 卡点：
- 下一步：

## 8. 当前缺口判断

基于你现在的基础，和目标 JD 的差距主要是：

- 还没有真正做过 GPU 调度器扩展
- 还没有真正跑过分布式训练栈并量化性能
- 还没有碰 RDMA / NCCL / MPI 这条高性能通信主线
- 还没有追 CSI / 分布式存储链路
- 还没有做出训练平台级 CRD + controller + queue + retry 的项目闭环

但你已经具备继续打这条线的前置基础，不需要再回到 Docker / K8s 入门重学。
