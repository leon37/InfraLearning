# rank1 Pending 导致 rank0 DDP 卡住排障复盘

## 1. 场景

典型现象：

```text
TrainJob phase = Starting
worldSize = 2
rank0 Pod = Running
rank1 Pod = Pending
rank0 日志卡在 DDP 初始化附近
```

核心判断：

```text
rank0 卡住的直接原因是 DDP group 缺少 rank1 进程加入。
rank1 Pending 的原因需要从 Kubernetes 对象里继续排查。
```

不要先怀疑 DDP worker 代码。rank1 Pod 还没运行时，rank1 的 Python 进程并没有启动。

## 2. 第一层：看 TrainJob 状态

命令：

```bash
kubectl get trainjob trainjob-sample -o yaml
```

重点字段：

```text
spec.worldSize
status.phase
status.attempt
status.runningWorkers
status.readyWorkers
status.lastFailure
```

判定：

```text
phase=Starting 且 lastFailure 为空：
    当前不是失败重试问题，而是 worker 还没全部进入可运行状态。

status.attempt：
    决定下一步应该看哪一轮 worker Pod。
```

## 3. 第二层：列出当前 attempt 的 worker Pods

命令：

```bash
kubectl get pod -l trainjob-name=trainjob-sample,attempt=0 -o wide
```

`-l` 是 label selector，表示按 label 筛选对象。

重点列：

```text
NAME
READY
STATUS
NODE
```

判定：

```text
rank1 STATUS=Pending 且 NODE=<none>：
    Pod 还没被 scheduler 绑定，优先看调度、资源、PVC 等原因。

rank1 STATUS=Pending 但 NODE 是具体节点：
    Pod 已经绑定到节点，优先看 kubelet、镜像、挂载、容器启动。
```

## 4. 第三层：describe Pending Pod

命令：

```bash
kubectl describe pod trainjob-sample-attempt-0-rank-1
```

重点区域：

```text
Status
Node
Conditions
Events
```

尤其看 `Events` 中的：

```text
Reason
Message
```

## 5. 分支一：资源不足

`describe pod` 片段：

```text
Status:         Pending
Node:           <none>

Events:
  Type     Reason             Message
  ----     ------             -------
  Warning  FailedScheduling   0/3 nodes are available: 3 Insufficient aiinfra.leon.com/gpu-capacity.
```

判断：

```text
这是 scheduler 阶段失败。
Pod 尚未绑定到 Node。
这不是 DDP worker 代码问题。
```

下一步看 Pod requests：

```bash
kubectl get pod trainjob-sample-attempt-0-rank-1 -o jsonpath='{.spec.containers[0].resources.requests}{"\n"}'
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
Pod.resources.requests 要和 Node.status.allocatable 对上。
如果所有 Node allocatable 都小于 Pod requests，调度会失败。
```

## 6. 分支二：PVC 未绑定

`describe pod` 片段：

```text
Status:         Pending
Node:           <none>

Events:
  Type     Reason             Message
  ----     ------             -------
  Warning  FailedScheduling   0/3 nodes are available: pod has unbound immediate PersistentVolumeClaims.
```

判断：

```text
这不是 DDP worker 代码问题。
Pod 因为 PVC 问题还没完成调度。
```

先看 PVC 列表：

```bash
kubectl get pvc
```

重点列：

```text
STATUS
VOLUME
CAPACITY
ACCESS MODES
STORAGECLASS
```

如果 PVC 是 `Pending`，再看详情：

```bash
kubectl describe pvc trainjob-checkpoint-pvc
```

重点区域：

```text
Events
StorageClass
Volume
Used By
```

为什么可能只影响 rank0：

```text
当前 TrainJob 实现只有 rank0 挂载 checkpoint PVC。
rank1 没有 checkpoint volumeMount，所以同一个 PVC 问题可能只卡 rank0。
```

## 7. 分支三：Pod 已绑定，但镜像拉取失败

`describe pod` 片段：

```text
Status:         Pending
Node:           kind-worker2/172.18.0.3

Events:
  Type     Reason       Message
  ----     ------       -------
  Normal   Scheduled    Successfully assigned default/trainjob-sample-attempt-0-rank-1 to kind-worker2
  Normal   Pulling      Pulling image "aiinfra-ddp-worker:dev"
  Warning  Failed       Failed to pull image "aiinfra-ddp-worker:dev": image not found
```

判断：

```text
Pod 已经被 scheduler 绑定到 Node。
此时不再优先看 scheduler 日志。
问题发生在 kubelet 拉起容器阶段。
```

最可能原因：

```text
本地镜像没有加载到 kind 集群。
```

对应准备动作：

```bash
kind load docker-image aiinfra-ddp-worker:dev --name infra-learning
```

## 8. 分支四：rank0 Service 没有 endpoint

场景：

```text
rank0 Pod = Running
rank1 Pod = Running
rank1 日志里连接 MASTER_ADDR 失败
```

看 endpoints：

```bash
kubectl get endpoints trainjob-sample-master -o yaml
```

如果输出：

```yaml
subsets: []
```

判断：

```text
Service 当前没有可用后端 endpoint。
rank1 通过 MASTER_ADDR 访问 rank0 Service，但 Service 没有指向 rank0 Pod。
```

下一步看 Service selector：

```bash
kubectl get svc trainjob-sample-master -o jsonpath='{.spec.selector}{"\n"}'
```

重点字段：

```text
trainjob-name
rank
attempt
```

再看 rank0 Pod labels：

```bash
kubectl get pod trainjob-sample-attempt-0-rank-0 --show-labels
```

重点字段：

```text
trainjob-name=...
rank=0
attempt=...
```

判定：

```text
如果 Service selector 和 rank0 Pod labels 对不上，Service 选不中 rank0。
如果 selector 对得上，但 endpoints 还是空，再看 rank0 Pod 是否 Ready、端口是否符合预期。
```

## 9. 固定排障顺序

遇到：

```text
TrainJob Starting
rank0 Running
rank1 Pending
rank0 卡在 DDP 初始化
```

按这个顺序查：

```text
1. kubectl get trainjob trainjob-sample -o yaml
   看 status.phase / status.attempt / status.lastFailure

2. kubectl get pod -l trainjob-name=trainjob-sample,attempt=<attempt> -o wide
   看 STATUS / NODE

3. kubectl describe pod <pending-pod>
   看 Node / Events / Reason / Message

4. 如果 FailedScheduling + Insufficient：
   看 Pod resources.requests 和 Node status.allocatable

5. 如果 unbound PersistentVolumeClaims：
   看 pvc 的 STATUS 和 describe pvc 的 Events

6. 如果 Node 已有值但镜像失败：
   看 image 是否已经加载进 kind

7. 如果两个 Pod 都 Running 但 DDP 连接失败：
   看 rank0 Service endpoints、Service selector 和 rank0 Pod labels
```

## 10. 面试回答底稿

如果面试官问：

```text
rank0 Running，rank1 Pending，rank0 卡在 DDP 初始化，你怎么排查？
```

可以这样回答：

```text
我会先看 TrainJob status，确认当前 phase、attempt 和 lastFailure。
如果 phase 是 Starting 且没有 lastFailure，我会列出当前 attempt 的 worker Pods，看 rank1 是 Pending 且 Node 是否为空。

如果 rank1 Node 是空，我会 describe rank1 Pod，看 Events 里的 FailedScheduling 原因。
如果是 Insufficient extended resource，就对 Pod requests 和 Node allocatable。
如果是 PVC 未绑定，就看 pvc 状态和 describe pvc 的 Events。

如果 rank1 已经有 Node，但仍然 Pending，我会转向 kubelet/container 阶段，看镜像拉取、挂载和容器启动事件。

rank0 卡住不是因为 rank0 自己一定有 bug，而是因为 DDP worldSize=2，需要 rank1 进程也加入 process group。rank1 Pending 时 rank1 进程没有启动，rank0 等不到完整 group。
```

