# TrainJob happy path 复现记录

## 1. 复现目标

从清理后的状态重新跑通：

```text
TrainJob
-> controller 展开 worker Pods
-> custom scheduler 调度 worker Pods
-> DDP worker 完成训练
-> rank0 写 checkpoint 到 PVC
-> TrainJob 进入 Succeeded
```

本次复现时间：

```text
2026-05-21
```

## 2. 初始清理

已清理旧 TrainJob demo 相关对象：

```text
trainjob-sample
trainjob-sample-attempt-* worker Pods
trainjob-sample-master Service
trainjob-checkpoint-pvc
```

无关对象：

```text
my-service
```

本次未处理，和 TrainJob happy path 无关。

## 3. PVC 准备

重新创建：

```text
trainjob-checkpoint-pvc
```

初始观察：

```text
STATUS=Pending
STORAGECLASS=standard
```

判定：

```text
kind local-path 下 PVC Pending 可接受。
它通常会等第一个使用该 PVC 的 Pod 出现并完成调度后再绑定。
```

创建 TrainJob 后，PVC 变为：

```text
STATUS=Bound
VOLUME=pvc-e60fcd5e-4ea5-4f60-946e-16f7b7b1011b
ACCESS MODES=RWO
```

## 4. 控制面进程

本次复现中：

```text
TrainJob controller 正常运行
custom scheduler 正常运行
```

未观察到：

```text
controller 退出
scheduler plugin 初始化失败
```

## 5. TrainJob 创建结果

创建：

```text
trainjob-sample
```

观察到：

```text
rank0 Pod = trainjob-sample-attempt-0-rank-0
rank1 Pod = trainjob-sample-attempt-0-rank-1
rank0 Service = trainjob-sample-master
```

调度结果：

```text
rank0 -> kind-worker
rank1 -> kind-worker2
```

rank0 Service selector：

```text
attempt=0
rank=0
trainjob-name=trainjob-sample
```

判定：

```text
controller 已正确展开 worker Pods 和 rank0 Service。
custom scheduler 已接管 schedulerName=my-custom-scheduler 的 worker Pods 并完成绑定。
```

## 6. 训练结果

worker Pod 最终状态：

```text
trainjob-sample-attempt-0-rank-0   Completed
trainjob-sample-attempt-0-rank-1   Completed
```

TrainJob status：

```text
status.phase=Succeeded
status.attempt=0
```

rank0 日志包含：

```text
rank=0
world_size=2
step=0
step=1
step=2
```

并输出：

```text
step_time_ms
max_step_time_ms
global_batch_size
samples_per_second
data_time_ms
compute_sync_time_ms
```

判定：

```text
DDP worker 已按 worldSize=2 完成 3 step 训练。
Gloo process group 和 Pod 网络下的 collective communication 链路正常。
```

## 7. checkpoint 验证

本次 PVC 对应 PV：

```text
pvc-e60fcd5e-4ea5-4f60-946e-16f7b7b1011b
```

kind node 路径：

```text
/var/local-path-provisioner/pvc-e60fcd5e-4ea5-4f60-946e-16f7b7b1011b_default_trainjob-checkpoint-pvc
```

在 `kind-worker` 中观察：

```text
latest.pt
```

文件信息：

```text
-rw-r--r-- 1 root root 73929 May 21 07:03 latest.pt
```

判定：

```text
rank0 已成功将 checkpoint 写入本次新 PVC 背后的 PV。
```

## 8. 结论

本次 happy path 复现通过：

```text
清理旧对象
-> 重建 PVC
-> 启动 controller 和 scheduler
-> 创建 TrainJob
-> worker Pods 调度成功
-> DDP worker 训练完成
-> TrainJob Succeeded
-> rank0 写入 latest.pt
```

边界仍然不变：

```text
当前验证的是 kind + CPU/Gloo + Pod 网络下的控制面和 DDP 契约。
不代表真实 GPU/NCCL/RDMA 性能验证。
rank0-only checkpoint 仍不等于完整多 rank 自动恢复。
```

