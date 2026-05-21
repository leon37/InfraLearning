# TrainJob 状态机

## 1. 文档定位

本文只记录当前 `AIInfraTrainJob` 代码里的状态机语义。

代码依据：

```text
/home/leon/AIInfraTrainJob/api/v1/trainjob_types.go
/home/leon/AIInfraTrainJob/internal/controller/trainjob_controller.go
```

本文目标：

```text
不看代码时，能说出 worker Pod 状态组合如何影响 TrainJob.status.phase。
能解释 Pending 不等于 Failed。
能解释 rank0 Running、rank1 Pending 时为什么 TrainJob 会卡在 Starting。
能解释当前实现为什么不是真正的 gang scheduling。
```

## 2. Phase 定义

当前 `TrainJobPhase` 有 7 个值：

| Phase | 当前语义 |
| --- | --- |
| `Submitted` | TrainJob 对象已被 controller 看到，刚进入状态机 |
| `Queued` | 过渡态；当前实现里不是严格的队列准入状态 |
| `Starting` | 正在准备或等待 worker Pod 全部进入可运行状态 |
| `Running` | 所有 worker Pod 都已经进入 `Running` 或 `Succeeded`，且整组尚未全部成功 |
| `Retrying` | 当前 attempt 有 worker 失败，且还没超过 `retryLimit`，准备进入下一轮 attempt |
| `Succeeded` | 当前 attempt 中所有 worker Pod 都 `Succeeded` |
| `Failed` | 有 worker Pod `Failed`，并且已经不能继续重试 |

当前代码里的 `Queued` 和 `Retrying` 都不是长期稳定状态。它们更多是 controller 在不同 reconcile 轮次之间推进状态时留下的中间状态。

当前 `ReadyWorkers` 只作为观察字段保留，不再决定 TrainJob 主生命周期。主 phase 更关注 worker 是否已经被拉起、是否已经完成、是否失败，而不是 Pod Ready condition。

## 3. Reconcile 主流程

`Reconcile` 每次先读取 TrainJob，然后按 `status.phase` 分支处理。

核心流转：

```text
phase 为空
-> Submitted
-> Queued
-> Starting
-> 创建/修正 rank0 Service
-> 创建/修正 worker Pods
-> 聚合当前 attempt 的 worker Pod 状态
-> 根据聚合结果进入 Starting / Running / Succeeded / Retrying / Failed
```

终态：

```text
Succeeded
Failed
```

TrainJob 一旦进入 `Succeeded` 或 `Failed`，当前 `Reconcile` 会直接返回，不再创建 Pod，也不再继续更新状态。

## 4. controller 如何持续感知状态变化

当前 controller 不是创建 Pod 后只判断一次。

它通过 controller-runtime 建立监听：

```text
For(&TrainJob{})
Owns(&Pod{})
Watches(&Pod{}, ...)
```

含义：

| 监听入口 | 当前作用 |
| --- | --- |
| `For(&TrainJob{})` | TrainJob 自身创建、更新时触发 reconcile |
| `Owns(&Pod{})` | controller 创建的 worker Pod 状态变化时，重新触发对应 TrainJob 的 reconcile |
| `Watches(&Pod{}, ...)` | 监听 Pod 变化后额外唤醒 `Queued` 状态的 TrainJob |

关键点：

```text
Pod 的调度、启动、运行、成功、失败都是异步发生的。
controller 必须反复 reconcile，才能把底层 Pod 的最新状态聚合回 TrainJob.status。
```

所以不能只在创建 Pod 后立刻判断一次状态。那一刻 Pod 大概率还没被 scheduler 绑定，也没被 kubelet 拉起。

## 5. worker 状态聚合规则

当前聚合函数只统计当前 attempt 的 worker Pod：

```text
label trainjob-name=<TrainJob 名字>
label attempt=<TrainJob.status.attempt>
```

它统计 5 个信息：

| 字段 | 来源 |
| --- | --- |
| `Total` | 当前 attempt 下实际查到的 worker Pod 数量 |
| `RunningWorkers` | `pod.status.phase == Running` 的数量 |
| `ReadyWorkers` | Pod condition 中 `Ready=True` 的数量 |
| `SucceededWorkers` | `pod.status.phase == Succeeded` 的数量 |
| `FailedPod` | 第一个 `pod.status.phase == Failed` 的 Pod |

注意：`Pending` 不会计入 `RunningWorkers`、`SucceededWorkers` 或 `FailedPod`。

这就是为什么 `Pending` 不会直接让 TrainJob 失败。

## 6. nextPhase 判定表

在没有 `FailedPod` 的前提下，当前代码按下面顺序判断：

| 条件 | 结果 Phase |
| --- | --- |
| `SucceededWorkers == worldSize` | `Succeeded` |
| `Total < worldSize` | `Starting` |
| `RunningWorkers + SucceededWorkers < worldSize` | `Starting` |
| 其他情况 | `Running` |

这几个结论很重要：

```text
所有 worker 都 Succeeded，TrainJob 才 Succeeded。
只要有 worker 既不是 Running，也不是 Succeeded，TrainJob 就是 Starting。
只要所有 worker 都已经 Running 或 Succeeded，且没有 Failed，TrainJob 就是 Running。
ReadyWorkers 不参与主 phase 判定。
```

当前实现有一个明确设计选择：

```text
如果一个 worker 已经 Succeeded，另一个 worker 还在 Running，
那么 RunningWorkers + SucceededWorkers == worldSize，当前 TrainJob 会被判为 Running。
```

这表示 TrainJob phase 表达的是“整组训练是否已经越过 Pod 启动阶段并仍未最终完成”，而不是表达“所有 Pod 当前都 Ready”。

## 7. 常见状态组合

假设 `worldSize=2`。

| rank0 Pod | rank1 Pod | 当前 TrainJob phase | 原因 |
| --- | --- | --- | --- |
| 尚未创建 | 尚未创建 | `Starting` | 当前 attempt 查到的 Pod 数量小于 `worldSize` |
| `Pending` | `Pending` | `Starting` | Pod 已创建，但还没有 worker 进入 `Running` |
| `Running` | `Pending` | `Starting` | `RunningWorkers + SucceededWorkers < worldSize` |
| `Running` 且 Ready | `Running` 但未 Ready | `Running` | 两个 worker 都已经被 kubelet 拉起 |
| `Running` 且 Ready | `Running` 且 Ready | `Running` | 所有 worker 都 Running |
| `Succeeded` | `Running` | `Running` | 一个 worker 已完成，另一个仍在运行，整组尚未最终完成 |
| `Succeeded` | `Succeeded` | `Succeeded` | `SucceededWorkers == worldSize` |
| `Failed` | 任意非 Failed | `Retrying` 或 `Failed` | 先看是否还能重试 |

## 8. 失败与重试

只要当前 attempt 中发现任意一个 worker Pod `Failed`，controller 会先进入失败处理，不再走普通的 `nextPhase`。

失败处理逻辑：

```text
记录 LastFailure
读取当前 attempt
如果 status.attempt < spec.retryLimit：
    phase = Retrying
    删除当前 attempt 的 worker Pods
    status.attempt = oldAttempt + 1
否则：
    phase = Failed
```

`LastFailure` 会记录：

| 字段 | 来源 |
| --- | --- |
| `attempt` | 失败 Pod 的 `attempt` label |
| `rank` | 失败 Pod 的 `rank` label |
| `reason` | Pod 或 container terminated reason |
| `message` | Pod 或 container terminated message |
| `exitCode` | container terminated exit code |
| `observedAt` | controller 观察到失败的时间 |

当前重试路径中，代码删除旧 attempt 的 worker Pods，并增加 `status.attempt`。rank0 Service 没有在失败处理里删除，而是在下一轮 reconcile 中由 `ensureMasterService` 更新 selector，使它指向新的 attempt。

## 9. attempt 的作用

`attempt` 是同一个 TrainJob 的第几轮尝试。

它会写入：

```text
worker Pod name
worker Pod labels
rank0 Service selector
TrainJob.status.attempt
LastFailure.attempt
```

它解决的问题：

```text
同一个 TrainJob 重试时，旧 attempt 的 Pod 可能还没完全消失。
如果 Service selector 只按 trainjob-name 和 rank=0 选择，就可能把旧 rank0 和新 rank0 混在一起。
attempt 把不同轮次隔离开。
```

## 10. rank0 Running、rank1 Pending 的解释

这个现象对应：

```text
rank0 Pod phase = Running
rank1 Pod phase = Pending
```

当前聚合结果大致是：

```text
Total = 2
RunningWorkers = 1
SucceededWorkers = 0
FailedPod = nil
```

代入 `nextPhase`：

```text
RunningWorkers + SucceededWorkers < worldSize
-> TrainJob phase = Starting
```

所以 TrainJob 会一直卡在 `Starting`，不会自动失败。

DDP 侧的结果是：

```text
rank0 已经启动，但 DDP process group 需要 worldSize 个 rank 都加入。
rank1 还没运行，rank0 会卡在初始化或等待通信组完成的位置。
```

这类问题优先排查：

```text
rank1 为什么 Pending
```

而不是先怀疑 rank0 训练代码。

## 11. 当前实现不是真正的 gang scheduling

当前 TrainJob controller 做了这些事：

```text
展开 worldSize 个 worker Pod
注入 rank/world_size/master 环境变量
聚合 worker 状态
失败后按 attempt 重试
```

但它没有做到真正的 gang scheduling。

原因：

```text
scheduler 仍然是逐个 Pod 做调度决策。
rank0 可以先被调度并占用资源。
rank1 如果一直 Pending，controller 只是看到整组还没启动完成。
controller 没有让 scheduler 在调度前确认“整组资源是否同时满足”。
controller 也没有在 rank1 长期 Pending 时自动释放 rank0 已占资源。
```

所以当前更准确的说法是：

```text
TrainJob 实现了分布式训练任务的 Pod 展开、启动契约注入、状态聚合和失败重试。
当前没有实现严格 gang scheduling。
```

下一步如果要补 gang scheduling，方向应该在调度侧表达整组约束，而不是只在 controller 里继续卡 `Starting`。

只靠 controller 做超时清理也不等于真正的 gang scheduling。

例如：

```text
rank0 已经 Running
rank1 因资源不足 Pending
controller 发现 TrainJob 长时间 Starting 后删除 rank0
```

这个方案能缓解 rank0 长时间占住资源的问题，但它仍然是事后补偿。

原因：

```text
scheduler 在做 rank0 调度决策时，仍然不知道 rank1 是否也能被同时调度。
下一轮 attempt 仍可能再次出现 rank0 先 Running、rank1 Pending。
```

真正要补的是调度侧准入语义：

```text
在允许任意一个 worker 真正占用资源之前，先判断整组 worker 的资源需求是否能一起满足。
如果不能满足，就让整组等待，而不是先放行其中一部分。
```

## 12. 面试回答底稿

如果被问“你的 TrainJob 状态机是怎么工作的”，可以这样回答：

```text
TrainJob controller 通过 Reconcile 持续观察 TrainJob 和它 owner 下的 worker Pod。
对象刚创建时，phase 会从空值推进到 Submitted、Queued、Starting。
进入 Starting 后，controller 确保 rank0 Service 和 worldSize 个 worker Pod 存在，然后只聚合当前 attempt 的 Pod 状态。

如果所有 worker 都 Succeeded，TrainJob 进入 Succeeded。
如果有 worker Failed，先看 attempt 是否小于 retryLimit；还能重试就记录 LastFailure、删除当前 attempt 的 worker Pod、attempt 加一并进入 Retrying，否则进入 Failed。
如果没有失败，但 Pod 数量不足、有人 Pending，都会保持 Starting。
只要所有 worker 都已经 Running 或 Succeeded，且尚未全部 Succeeded，就会进入 Running。
```

如果被问“rank0 Running、rank1 Pending 会怎样”，可以这样回答：

```text
按当前代码，TrainJob 会停在 Starting。
因为 Pending 不算 Failed，也不算 Running；聚合时 RunningWorkers 小于 worldSize。
DDP 侧 rank0 会等待 rank1 加入通信组，所以训练不会真正开始。
这暴露的是调度或资源问题，应该先排 rank1 Pending 的原因。
```

如果被问“这是不是 gang scheduling”，可以这样回答：

```text
不是严格 gang scheduling。
当前 controller 能表达一组 worker 的生命周期，但 scheduler 仍然逐个 Pod 调度。
它不能在调度前保证整组资源同时满足，也不能自动阻止 rank0 先占资源。
真正要补 gang scheduling，需要在 scheduler 侧引入整组等待、准入或超时释放这类机制。
```
