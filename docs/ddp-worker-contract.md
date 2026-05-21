# DDP Worker 启动契约

## 1. 文档定位

本文记录 `AIInfraTrainJob` controller 与 `AIInfraDDPLab` worker 之间的启动契约。

目标：

```text
能解释 torchrun 在普通 DDP 启动里做什么。
能解释 TrainJob controller 替代了 torchrun 的哪一部分。
能解释 MASTER_ADDR、MASTER_PORT、RANK、WORLD_SIZE、LOCAL_RANK 的来源和含义。
能解释 rank0 Service 和 attempt label 为什么是 DDP rendezvous 的关键。
```

## 2. 普通 torchrun 模式

普通 DDP 启动中，`torchrun` 扮演启动器角色。

它主要负责：

```text
拉起 worker 进程
分配 RANK / LOCAL_RANK / WORLD_SIZE
提供 MASTER_ADDR / MASTER_PORT 等 rendezvous 信息
管理 worker 进程退出
```

但真正加入 DDP 通信组的不是 `torchrun` 自己，而是 worker 进程里调用：

```text
dist.init_process_group(...)
```

边界：

```text
torchrun 提供启动和 rendezvous 参数。
init_process_group 使用这些参数加入通信组。
DDP(model) 把梯度同步挂到 backward 路径上。
```

## 3. TrainJob 模式

当前 TrainJob 模式不使用 `torchrun` 拉起多个本地进程。

controller 替代的是：

```text
跨 Pod 创建 worker
为每个 worker 分配 rank
注入 world size
注入 rank0 rendezvous 地址和端口
```

它没有替代：

```text
dist.init_process_group
PyTorch 通信库
DDP 梯度同步逻辑
```

当前模型：

```text
1 Pod = 1 worker process
```

因此：

```text
LOCAL_RANK=0
```

因为每个 Pod 内只有一个本地 worker 进程。

## 4. 环境变量契约

worker 脚本依赖这些环境变量：

| 环境变量 | 来源 | 含义 |
| --- | --- | --- |
| `MASTER_ADDR` | controller 根据 rank0 Service 生成 | rank0 rendezvous 入口地址 |
| `MASTER_PORT` | TrainJob spec 或默认值 | rank0 rendezvous 入口端口 |
| `WORLD_SIZE` | TrainJob `spec.worldSize` | DDP group 中 rank 总数 |
| `RANK` | controller 按 worker 序号分配 | 当前 worker 在全局 group 中的 rank |
| `LOCAL_RANK` | 当前固定为 `0` | 当前进程在本 Pod 内的本地 rank |

`env://` 初始化方式依赖这些环境变量完成 rendezvous 参数读取。

注意：

```text
LOCAL_RANK 不一定是 PyTorch env:// rendezvous 本身的必需字段。
但当前 worker 脚本把它作为启动契约的一部分。
```

## 5. MASTER_ADDR 为什么不能手填 Pod IP

Pod IP 是临时地址。

这些情况都会导致 Pod IP 变化：

```text
Pod 删除重建
失败重试
新的 attempt
Pod 被重新调度到其他 Node
```

如果用户在 TrainJob YAML 里手填 rank0 Pod IP：

```text
下一轮 attempt 可能继续连接旧 IP。
其他 rank 可能找不到新的 rank0。
DDP group 初始化会失败或卡住。
```

因此 `MASTER_ADDR` 不应由用户填写 Pod IP，而应由 controller 根据 rank0 Service 派生。

## 6. rank0 Service 的作用

rank0 Service 提供稳定 rendezvous 入口。

当前形式：

```text
<trainjob-name>-master.<namespace>.svc
```

worker 看到的是稳定的 Service DNS，而不是 rank0 Pod IP。

Service 再通过 selector 指向当前 attempt 的 rank0 Pod。

这解决的是：

```text
rank0 Pod IP 会变
其他 rank 仍然需要一个稳定入口
```

## 7. Service selector 为什么必须带 attempt

rank0 Service selector 不能只写：

```text
trainjob-name=<job>
rank=0
```

它必须包含：

```text
attempt=<current-attempt>
```

原因：

```text
失败重试时，旧 attempt 的 rank0 Pod 可能还没完全删除。
如果 selector 不区分 attempt，新 Service 可能同时选中旧 rank0 和新 rank0。
甚至可能选中即将被删除的旧 rank0。
```

这会导致：

```text
新的 DDP group 找到错误的 rendezvous 后端。
rank 间连接混乱。
rank0 后端被删除时，其他 rank 继续等待或失败。
```

因此当前 selector 至少包含：

```text
trainjob-name=<job>
rank=0
attempt=<current-attempt>
```

## 8. DDP 初始化卡住时的判断

如果：

```text
worldSize=2
rank0 Running
rank1 Pending
rank0 日志卡在 init_process_group 附近
```

直接原因是：

```text
DDP group 需要 worldSize 个 rank 进程都加入。
rank1 Pending 表示 rank1 进程还没启动。
rank0 等不到完整 group。
```

这时应先排查：

```text
rank1 为什么 Pending
```

而不是先怀疑 rank0 worker 代码。

## 9. 面试回答底稿

如果被问：

```text
TrainJob controller 和 torchrun 的关系是什么？
```

可以回答：

```text
普通 torchrun 是启动器，它负责拉起 worker 进程，并注入 RANK、LOCAL_RANK、WORLD_SIZE、MASTER_ADDR、MASTER_PORT 等信息。真正加入通信组的是 worker 进程里的 init_process_group。

我的 TrainJob controller 替代的是跨 Pod 启动器这部分职责：它创建 worldSize 个 worker Pod，为每个 Pod 分配 RANK，注入 WORLD_SIZE、MASTER_ADDR、MASTER_PORT 和 LOCAL_RANK。它没有替代 PyTorch 的 init_process_group，也没有替代 DDP 的梯度同步。
```

如果被问：

```text
为什么 MASTER_ADDR 不让用户填？
```

可以回答：

```text
因为 Pod IP 会随 Pod 重建、失败重试和重新调度变化。用户手填 Pod IP 很容易在下一轮 attempt 里变成旧地址。controller 用 rank0 Service 生成 MASTER_ADDR，让其他 rank 通过稳定 DNS 找到当前 attempt 的 rank0。
```

如果被问：

```text
rank0 Service selector 为什么要带 attempt？
```

可以回答：

```text
因为失败重试时旧 attempt 的 rank0 Pod 可能还没完全删除。如果 selector 只按 trainjob-name 和 rank=0 选择，Service 可能选中旧 rank0，导致新的 DDP group 连接到错误后端。attempt 用来隔离不同重试轮次。
```

