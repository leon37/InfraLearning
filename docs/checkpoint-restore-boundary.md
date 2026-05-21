# checkpoint 恢复边界

## 1. 文档定位

本文记录当前 checkpoint 能力与完整多 rank 自动恢复之间的边界。

目标：

```text
能解释 latest.pt 至少保存哪些训练状态。
能解释 model_state_dict 与 optimizer_state_dict 的恢复位置。
能解释 rank0-only PVC checkpoint 为什么不等于完整多 rank 自动恢复。
能解释 RWO/local-path 对恢复调度位置的限制。
```

## 2. 当前 checkpoint 能力

当前实现：

```text
rank0 挂载 PVC 到 /checkpoint
rank0 写入 /checkpoint/latest.pt
latest.pt 包含 model_state_dict、optimizer_state_dict、last_step、world_size
```

它证明的是：

```text
rank0 能把训练状态写进持久化存储。
```

它还没有证明：

```text
整组 worker 能在下一轮 attempt 自动从 checkpoint 恢复。
```

## 3. latest.pt 字段语义

| 字段 | 作用 |
| --- | --- |
| `model_state_dict` | 恢复模型参数 |
| `optimizer_state_dict` | 恢复优化器内部状态，例如动量、二阶矩等 |
| `last_step` | 知道从哪个训练步数继续 |
| `world_size` | 校验恢复时的 DDP group 规模是否和保存时一致 |

更完整的 checkpoint 后续还可以考虑：

```text
随机数状态
学习率调度器状态
数据迭代位置
训练参数版本
代码/镜像版本
```

当前不继续扩展这些字段，避免偏离主线。

## 4. model 和 optimizer 的恢复顺序

当前保存的是：

```text
ddp_model.module.state_dict()
```

因此恢复模型参数时，推荐顺序是：

```text
model = build_model()
model.load_state_dict(checkpoint["model_state_dict"])
optimizer = build_optimizer(model.parameters())
optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
ddp_model = DDP(model)
```

关键点：

```text
model_state_dict 建议在 DDP(model) 前加载。
optimizer_state_dict 应在 optimizer 创建之后加载。
```

原因：

```text
model_state_dict 对应原始 model 的参数名。
optimizer state 绑定已经创建好的参数对象，因此要先创建 optimizer，再 load optimizer_state_dict。
```

## 5. 只保存 model_state_dict 的问题

如果 checkpoint 只保存：

```text
model_state_dict
```

程序通常仍然可以继续跑。

但训练语义上会丢失：

```text
optimizer 的动量
二阶矩
其他优化器内部状态
学习率调度等相关状态
```

影响：

```text
恢复后的训练不再等价于从中断点连续训练。
loss 曲线可能抖动。
收敛速度或最终效果可能变差。
极端情况下可能出现不稳定。
```

不要简单说一定会 loss 爆炸，这太绝对。

## 6. rank0-only PVC 的边界

当前只有 rank0 挂载 PVC：

```text
rank0: /checkpoint -> PVC
rank1: 没有 /checkpoint PVC
```

因此：

```text
rank0 能读写 latest.pt。
其他 rank 没有直接读取 latest.pt 的路径。
```

这意味着当前能力只是：

```text
rank0 checkpoint 持久化链路已通。
```

不是：

```text
完整多 rank 自动恢复已实现。
```

## 7. 方向 A：所有 rank 直接读共享 checkpoint

如果选择：

```text
所有 rank 都直接读取 /checkpoint/latest.pt
```

那么 checkpoint 存储必须满足：

```text
所有 rank 都能看到同一份 latest.pt。
```

分情况：

```text
所有 rank 都在同一个 Node：
    RWO PVC 可能够用，因为 ReadWriteOnce 是单 Node 读写挂载边界。

rank 可能分布在多个 Node：
    需要 RWX，也就是 ReadWriteMany，或等价的共享存储。
```

等价共享存储包括：

```text
NFS
CephFS
对象存储
其他能被所有 Node 访问到同一份 checkpoint 的存储
```

关键不是“是否持久化”，而是：

```text
所有 rank 是否看到同一份 latest.pt。
```

## 8. RWO/local-path 的限制

kind 默认 local-path PVC 通常是：

```text
ReadWriteOnce
```

并且 PV 背后路径绑定到具体 kind node。

如果：

```text
PVC/PV 绑定在 kind-worker2
下一次 TrainJob 的 rank0 被调度到 kind-worker
```

那么：

```text
rank0 不能直接读取 kind-worker2 上那份 local-path PV 里的 latest.pt。
```

原因：

```text
RWO 的边界是单 Node 读写挂载。
local-path 的真实文件路径也在绑定的那个 kind node 上。
```

这说明 checkpoint 恢复不只是文件写入问题，还和：

```text
调度位置
PVC access mode
PV 背后存储类型
```

有关。

## 9. 方向 B：rank0 读取后广播

另一条路线是：

```text
只有 rank0 读取 latest.pt
rank0 通过分布式通信把必要状态同步给其他 rank
```

同步时机：

```text
必须发生在 DDP 训练继续之前。
```

需要同步的不只是：

```text
model_state_dict
```

还要考虑：

```text
optimizer_state_dict
last_step
其他会影响继续训练语义的状态
```

因为：

```text
只同步模型权重，不能保证优化器状态连续。
```

这条路线增加的复杂度：

```text
rank0 要读取 checkpoint 并广播状态。
非 rank0 要接收广播并更新内存状态。
需要定义广播哪些字段、什么时机广播、失败时如何处理。
```

## 10. 面试回答底稿

如果被问：

```text
你的 checkpoint 已经支持恢复了吗？
```

可以回答：

```text
当前已经验证 rank0 能把 latest.pt 写入 PVC，latest.pt 里包含 model_state_dict、optimizer_state_dict、last_step 和 world_size。
但这还不是完整自动恢复。因为当前只有 rank0 挂 PVC，其他 rank 没有读取 latest.pt 的路径。
完整恢复要么让所有 rank 都能访问同一份 checkpoint 存储，要么由 rank0 读取后通过分布式通信广播必要状态。
```

如果被问：

```text
model_state_dict 和 optimizer_state_dict 应该什么时候加载？
```

可以回答：

```text
model_state_dict 建议在 DDP(model) 前加载，因为我保存的是 ddp_model.module.state_dict()，对应原始模型参数。
optimizer_state_dict 要在 optimizer 创建之后加载，因为 optimizer state 绑定具体参数对象。
```

如果被问：

```text
RWO PVC 对多 Node checkpoint 有什么限制？
```

可以回答：

```text
RWO 是单 Node 读写挂载边界。如果 checkpoint PV 是 kind local-path 这类本地存储，并且绑定在某个 Node 上，下一轮 rank0 被调度到其他 Node 时，不能直接读取那份 latest.pt。跨 Node 直接共享 checkpoint 通常需要 RWX 或等价共享存储。
```

