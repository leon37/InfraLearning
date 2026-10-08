# 资源不足导致 TrainJob worker Pending 复盘

## 1. 复现场景

本次 G11 主动制造失败：

```text
创建 trainjob-fail-resource
将 worker Pod 的 aiinfra.leon.com/gpu-capacity requests/limits 调到超过所有 worker Node 的 allocatable
```

目标：

```text
验证 scheduler Filter 阶段资源不足时，Pod 如何进入 Pending，以及如何从 Events 判断原因。
```

## 2. 关键现象

`kubectl describe pod` 的 Events：

```text
Type     Reason            From                 Message
----     ------            ----                 -------
Warning  FailedScheduling  my-custom-scheduler  0/3 nodes are available: 1 node(s) had untolerated taint {node-role.kubernetes.io/control-plane: }, 2 Insufficient aiinfra.leon.com/gpu-capacity. preemption: 0/3 nodes are available: 1 Preemption is not helpful for scheduling, 2 No preemption victims found for incoming pod.
```

## 3. 判断链路

### 3.1 custom scheduler 是否接管

证据：

```text
From = my-custom-scheduler
Reason = FailedScheduling
```

结论：

```text
custom scheduler 已经接管并处理了这个 Pod。
这不是 scheduler 没启动或 profile 没匹配的问题。
```

### 3.2 失败发生在哪一层

证据：

```text
FailedScheduling
Insufficient aiinfra.leon.com/gpu-capacity
```

结论：

```text
失败发生在 scheduler Filter 阶段。
Pod 尚未绑定到 Node。
这不是 DDP worker 代码问题，也不是 kubelet 镜像拉取问题。
```

### 3.3 为什么 0/3 nodes 不可用

集群有 3 个 Node：

```text
kind-control-plane
kind-worker
kind-worker2
```

Events 中给出的原因：

```text
1 个 control-plane Node 有不可容忍 taint
2 个 worker Node 的 aiinfra.leon.com/gpu-capacity 不足
```

所以：

```text
control-plane 因 taint 不可用。
worker 节点因 extended resource 不足不可用。
```

### 3.4 preemption 为什么无帮助

Events 中有：

```text
Preemption is not helpful for scheduling
No preemption victims found for incoming pod
```

含义：

```text
即使考虑抢占，也找不到能通过驱逐其他 Pod 让当前 Pod 成功调度的方案。
```

在本次实验里，原因是请求值被故意设置得超过 worker Node 的可承载资源。即使清空现有普通 Pod，也无法满足这个超大 request。

## 4. 下一步应查什么

先看 Pod requests：

```bash
kubectl get pod <pending-pod-name> -o jsonpath='{.spec.containers[0].resources.requests}{"\n"}'
```

重点字段：

```text
aiinfra.leon.com/gpu-capacity
```

再看 Node allocatable：

```bash
kubectl get node -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.allocatable.aiinfra\.leon\.com/gpu-capacity}{"\n"}{end}'
```

判定：

```text
如果 Pod request 大于所有可用 worker Node 的 allocatable，调度失败是预期结果。
```

## 5. 面试回答底稿

如果被问：

```text
你怎么判断一个 Pending worker 是 scheduler 没接管，还是资源不足？
```

可以回答：

```text
我会看 describe pod 的 Events。如果 Events 为空，且 schedulerName 指向自定义 scheduler，我会怀疑 custom scheduler 没接管或没运行。

如果 Events 里有 FailedScheduling，From 是 my-custom-scheduler，并且 Message 里出现 Insufficient aiinfra.leon.com/gpu-capacity，说明 custom scheduler 已经接管，失败发生在 Filter 阶段。下一步我会对比 Pod resources.requests 和 Node.status.allocatable。
```

如果被问：

```text
为什么这不是 DDP worker 代码问题？
```

可以回答：

```text
因为 Pod 还没有被绑定到 Node，worker 容器没有启动，Python DDP 代码还没运行。问题发生在调度阶段。
```

