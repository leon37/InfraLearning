# Kubernetes 调度资源账本链路

## 1. 文档定位

本文记录 `AIInfraSchedulerPlugin` 当前使用的 Kubernetes 资源账本模型。

目标：

```text
能解释 Pod requests 为什么要和 Node allocatable 对应。
能解释 Node label 为什么不适合做硬性资源判断。
能解释真实 GPU 资源如何进入 Node.status.allocatable。
能解释 scheduler 为什么还需要自己的 cache / NodeInfo 计算已分配 requests。
```

## 2. 当前 demo 的资源模型

TrainJob worker Pod 会声明 extended resource：

```text
resources.requests.aiinfra.leon.com/gpu-capacity
```

scheduler 判断这个 Pod 能否放到某个 Node 时，硬性资源判断应该走：

```text
Pod.spec.containers[].resources.requests
Node.status.allocatable
```

当前 demo 中，节点资源是通过 patch 模拟出来的：

```text
kubectl patch node ... --subresource=status ...
```

这只是本地实验手段。它模拟的是：

```text
Node.status.capacity / Node.status.allocatable 中已经出现某种扩展资源。
```

它不是生产环境里真实 GPU 资源进入 Kubernetes 的方式。

## 3. 为什么不用 Node label 做硬性资源判断

Node label 适合表达策略信号，例如：

```text
node_topological_hint=high
zone=...
disk=ssd
```

但它不适合表达可扣减资源，例如：

```text
gpu-capacity=3000000
```

原因：

```text
label 不参与 Kubernetes 原生资源扣减。
label 没有 requests / allocatable 的账本语义。
label 和 Node.status.allocatable 同时表达资源时，会出现两套账本。
两套账本很容易不一致。
```

因此当前项目中：

```text
NodeResourcesFit 负责资源硬约束。
NodeLabelScore 只负责偏好排序。
NodeLabelFilter 不再作为资源过滤插件使用。
```

## 4. 真实 GPU 资源进入 Kubernetes 的链路

真实 GPU 集群里，资源链路大致是：

```text
节点上有 GPU
-> 节点侧 device plugin 发现和管理 GPU
-> device plugin 向 kubelet 注册扩展资源
-> kubelet 更新本 Node 的 status.capacity / status.allocatable
-> apiserver 保存 Node 对象
-> scheduler 通过 informer/cache 看到 Node.status.allocatable
-> NodeResourcesFit 比较 Pod requests 和 Node allocatable
```

关键纠偏：

```text
不要说 device plugin 直接写 apiserver。
更准确的说法是：device plugin 和 kubelet 交互，最终由 kubelet 更新 Node status。
```

## 5. 为什么 scheduler 不直接探测 GPU

scheduler 不应该直接去每台机器探测 GPU。

职责划分：

```text
节点侧组件：负责发现硬件、检查健康、向 kubelet 报告资源。
kubelet：负责维护本 Node 的状态并更新 Node status。
apiserver：保存统一资源账本。
scheduler：消费资源账本并做调度决策。
```

这样做的好处：

```text
scheduler 不需要理解每种硬件的探测细节。
scheduler 不需要远程探测所有节点。
scheduler 可以通过 watch apiserver 中的对象变化维护本地调度视图。
新增资源类型时，主要扩展节点侧上报链路，而不是改 scheduler 去探测硬件。
```

一句话：

```text
节点负责上报，apiserver 负责存账本，scheduler 负责消费账本。
```

## 6. capacity、allocatable 和剩余量

`Node.status.capacity`：

```text
节点总资源量。
```

`Node.status.allocatable`：

```text
节点可分配给 Pod 的资源上限。
```

注意：

```text
Node.status.allocatable 不是实时剩余资源。
```

例子：

```text
Node.status.allocatable.gpu = 4
podA requests.gpu = 1
podB requests.gpu = 1
```

通常不会因为 podA、podB 已经运行，就把 Node 对象上的：

```text
Node.status.allocatable.gpu
```

改成：

```text
2
```

scheduler 判断新 Pod 能不能放时，需要在调度视图里计算：

```text
剩余可用量 = Node.status.allocatable - 该 Node 上已分配 Pod requests 总和
```

这也是 scheduler cache / NodeInfo 的价值之一：

```text
它不只保存 Node 对象，还维护调度语义下的节点视图，包括这个 Node 上已经被调度的 Pod 及其 requests。
```

## 7. 本项目里的具体例子

假设：

```text
Node.status.allocatable.aiinfra.leon.com/gpu-capacity = 3000000
```

该 Node 上已有两个 Pod：

```text
podA requests = 1024000
podB requests = 1024000
```

新 Pod：

```text
podC requests = 1024000
```

计算：

```text
剩余可用量 = 3000000 - 1024000 - 1024000
          = 952000
```

判断：

```text
952000 < 1024000
```

因此：

```text
podC 不能放到这个 Node。
```

此时 Node 对象上的 `allocatable` 仍然可能显示为 `3000000`。不能把 `allocatable` 当成实时剩余量。

## 8. 排障时看什么

当 Pod 因 extended resource 不足 Pending：

```text
FailedScheduling
Insufficient aiinfra.leon.com/gpu-capacity
```

先看 Pod requests：

```bash
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[0].resources.requests}{"\n"}'
```

再看 Node allocatable：

```bash
kubectl get node -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.allocatable.aiinfra\.leon\.com/gpu-capacity}{"\n"}{end}'
```

如果 Node allocatable 看起来够，但 scheduler 仍说不足，需要继续考虑：

```text
该 Node 上已有 Pod 的 requests。
scheduler cache 中的 assumed Pod。
是否有其他调度约束排除了部分 Node。
```

## 9. 面试回答底稿

如果被问：

```text
Pod 请求 GPU 资源后，scheduler 到底看什么？
```

可以这样回答：

```text
scheduler 的硬性资源判断不是看 Node label，而是看 Pod resources.requests 和 Node.status.allocatable。
在真实 GPU 集群里，GPU 资源一般由节点侧 device plugin 发现并向 kubelet 注册，最终由 kubelet 更新到 Node.status.capacity 和 allocatable。scheduler 通过 informer/cache 消费 apiserver 里的 Node 资源账本。

同时，Node.status.allocatable 不是实时剩余量。scheduler 还要结合自己调度视图里这个 Node 上已经分配的 Pod requests，计算 allocatable 减去已分配 requests 后是否还能容纳新 Pod。
```

