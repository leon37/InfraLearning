# AI Infra 训练平台最小闭环 Demo

## 1. 文档定位

本文记录当前三个实验项目如何组成一个最小 AI 训练平台闭环：

- `AIInfraTrainJob`：训练任务控制面
- `AIInfraSchedulerPlugin`：自定义调度面
- `AIInfraDDPLab`：DDP worker 数据面

当前 demo 的目标不是证明真实 GPU / NCCL / RDMA 性能，而是证明：

```text
用户提交 TrainJob
-> controller 展开 DDP worker Pod
-> custom scheduler 接管并调度这些 Pod
-> worker 通过 DDP 启动契约完成多进程训练
-> rank0 checkpoint 写入 PVC
-> TrainJob 聚合最终状态
```

## 2. 三个项目职责

### 2.1 AIInfraTrainJob

路径：

```text
/home/leon/AIInfraTrainJob
```

职责：

- 定义 `TrainJob` CRD
- 通过 controller 把一个 TrainJob 展开成 `worldSize` 个 worker Pod
- 创建 rank0 Service，提供 DDP rendezvous 入口
- 给 worker Pod 注入：
  - `MASTER_ADDR`
  - `MASTER_PORT`
  - `RANK`
  - `WORLD_SIZE`
  - `LOCAL_RANK`
- 给 worker Pod 写入：
  - `schedulerName`
  - `resources.requests`
  - checkpoint PVC volume / volumeMount，当前只挂 rank0
- 聚合 worker Pod 状态并更新 TrainJob status

当前样例：

```text
/home/leon/AIInfraTrainJob/config/samples/batch_v1_trainjob.yaml
```

### 2.2 AIInfraSchedulerPlugin

路径：

```text
/home/leon/AIInfraSchedulerPlugin
```

职责：

- 启动一个独立 kube-scheduler 二进制
- profile 名称为 `my-custom-scheduler`
- 只接管 `spec.schedulerName=my-custom-scheduler` 的 Pod
- 使用 Kubernetes 原生 `NodeResourcesFit` 检查 extended resource
- 使用自定义 `NodeLabelScore` 插件读取 `node_topological_hint` 做节点打分

当前 demo 中，`NodeLabelFilter` 已从 profile 中移除。原因：

```text
NodeLabelFilter 原有逻辑本质是用 label 手写简化版资源过滤。
在 extended resource 路线中，资源过滤应交给 NodeResourcesFit。
否则会出现 label 与 Node.status.allocatable 两套资源账本。
```

### 2.3 AIInfraDDPLab

路径：

```text
/home/leon/AIInfraDDPLab
```

职责：

- 提供 DDP worker 脚本
- 构建 `aiinfra-ddp-worker:dev` 镜像
- worker 容器启动后执行：

```text
python experiments/05_ddp_step_time.py
```

当前 worker 能力：

- 使用 `env://` 读取 controller 注入的 DDP 环境变量
- 使用 `backend=gloo` 初始化 process group
- 输出 step time、吞吐、data time、compute sync time 等 JSON 日志
- rank0 将 marker 和最小 PyTorch checkpoint 写入 `/checkpoint`

## 3. 组件关系

三个组件通过 Kubernetes API Server 解耦：

```text
AIInfraTrainJob controller
    监听 TrainJob
    创建 worker Pod / rank0 Service

AIInfraSchedulerPlugin
    监听待调度 Pod
    只处理 schedulerName=my-custom-scheduler 的 Pod
    选择 Node 并 bind

AIInfraDDPLab worker
    作为 Pod 容器主进程运行
    根据环境变量加入 DDP process group
```

`AIInfraDDPLab` 不是在 Pod 运行之后才“额外启动”的组件。它的脚本已经被打进 worker 镜像，kubelet 拉起容器时就会执行该脚本。

## 4. Demo 启动顺序

理论上 controller 和 custom scheduler 谁先启动都可以，因为它们通过 API Server 解耦。

推荐 demo 顺序如下：

```text
1. 构建并加载 DDPLab worker 镜像
2. 准备 Node extended resource
3. 准备 checkpoint PVC
4. 启动 TrainJob controller
5. 启动 custom scheduler
6. 创建 TrainJob
7. 观察调度、训练、checkpoint 和 TrainJob status
```

这样排是为了减少无意义的中间错误：

- 镜像没准备好：Pod 可能 `ImagePullBackOff` 或运行旧脚本
- Node resource 没准备好：Pod 会 `Unschedulable`
- PVC 没准备好：rank0 checkpoint 挂载会失败或等待绑定
- controller 没准备好：TrainJob 不会展开 worker Pod
- scheduler 没准备好：worker Pod 会保持 `Pending`

## 5. 关键命令

### 5.1 构建并加载 worker 镜像

```bash
cd /home/leon/AIInfraDDPLab
docker build -t aiinfra-ddp-worker:dev .
kind load docker-image aiinfra-ddp-worker:dev --name infra-learning
```

### 5.2 准备 Node extended resource

当前 demo 用 patch 模拟节点资源账本：

```bash
kubectl patch node kind-worker --subresource=status --type=json \
  -p='[{"op":"add","path":"/status/capacity/aiinfra.leon.com~1gpu-capacity","value":"1500000"}]'

kubectl patch node kind-worker2 --subresource=status --type=json \
  -p='[{"op":"add","path":"/status/capacity/aiinfra.leon.com~1gpu-capacity","value":"3000000"}]'
```

观察：

```bash
kubectl get nodes -o jsonpath='{range .items[*]}{.metadata.name}{"\tcapacity="}{.status.capacity.aiinfra\.leon\.com/gpu-capacity}{"\tallocatable="}{.status.allocatable.aiinfra\.leon\.com/gpu-capacity}{"\n"}{end}'
```

判定：

```text
worker 节点必须能看到 allocatable。
Pod.resources.requests 会匹配 Node.status.allocatable，而不是匹配 Node label。
```

### 5.3 准备 checkpoint PVC

```bash
kubectl apply -f - <<'EOF'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: trainjob-checkpoint-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
EOF
```

kind 默认 `standard` StorageClass 使用 `rancher.io/local-path`，`volumeBindingMode=WaitForFirstConsumer`。因此 PVC 可能在没有消费者 Pod 前保持 `Pending`，这是正常现象。

观察：

```bash
kubectl get pvc,pv
```

### 5.4 启动 TrainJob controller

```bash
cd /home/leon/AIInfraTrainJob
make run
```

### 5.5 启动 custom scheduler

```bash
cd /home/leon/AIInfraSchedulerPlugin
GOCACHE=/tmp/go-build-cache go run ./cmd/scheduler-plugin \
  --config=cmd/scheduler-plugin/scheduler-config.yaml \
  --secure-port=10359 \
  --v=3
```

### 5.6 创建 TrainJob

```bash
cd /home/leon/AIInfraTrainJob
kubectl apply -f config/samples/batch_v1_trainjob.yaml
```

## 6. 验收点

### 6.1 TrainJob 展开 worker Pod

```bash
kubectl get pod,svc -l trainjob-name=trainjob-sample -o wide
```

预期：

```text
出现 worldSize 个 worker Pod
出现 rank0 Service
```

### 6.2 worker Pod 调度成功

```bash
kubectl get pod -l trainjob-name=trainjob-sample -o wide
```

预期：

```text
Pod 不再是 Pending
NODE 字段有值
```

### 6.3 rank0 挂载 checkpoint PVC

```bash
kubectl get pod trainjob-sample-attempt-0-rank-0 \
  -o jsonpath='{.spec.volumes}{"\n"}{.spec.containers[0].volumeMounts}{"\n"}'

kubectl get pod trainjob-sample-attempt-0-rank-1 \
  -o jsonpath='{.spec.volumes}{"\n"}{.spec.containers[0].volumeMounts}{"\n"}'
```

预期：

```text
rank0 有 checkpoint PVC 和 /checkpoint mount
rank1 只有 kube-api-access projected volume
```

### 6.4 DDP worker 正常运行

```bash
kubectl logs trainjob-sample-attempt-0-rank-0
kubectl logs trainjob-sample-attempt-0-rank-1
```

观察字段：

```text
rank
world_size
step
step_time_ms
max_step_time_ms
samples_per_second
```

预期：

```text
rank0 日志中 rank=0
rank1 日志中 rank=1
world_size 均为 2
能输出 step 指标
```

### 6.5 checkpoint 文件写入 PV

查询 PVC 绑定的 PV、节点和路径：

```bash
PV_NAME=$(kubectl get pvc trainjob-checkpoint-pvc -o jsonpath='{.spec.volumeName}')
NODE_NAME=$(kubectl get pv "$PV_NAME" -o jsonpath='{.spec.nodeAffinity.required.nodeSelectorTerms[0].matchExpressions[0].values[0]}')
PV_PATH=$(kubectl get pv "$PV_NAME" -o jsonpath='{.spec.hostPath.path}')

echo "$NODE_NAME"
echo "$PV_PATH"
```

进入 kind node 容器观察：

```bash
docker exec "$NODE_NAME" ls -lh "$PV_PATH"
```

预期：

```text
marker.txt
latest.pt
```

说明：

```text
这里看到的是 local-path PV 背后的 kind node 容器内路径。
kind 的 Node 本质是 Docker 容器，不是真实物理机。
```

### 6.6 TrainJob 状态成功

```bash
kubectl get trainjob trainjob-sample -o yaml
```

观察：

```text
status.phase
status.runningWorkers
status.readyWorkers
status.lastFailure
```

预期：

```text
TrainJob 最终进入成功状态
lastFailure 为空或不再更新
```

## 7. 当前边界

### 7.1 GPU / NCCL / RDMA 边界

当前 demo 使用：

```text
kind
CPU tensor
backend=gloo
Kubernetes Pod 网络
```

它能验证：

```text
TrainJob 控制面
DDP 启动契约
Pod 网络下的 Gloo collective communication
慢 rank 对同步训练的影响
checkpoint PVC 写入链路
```

它不能验证：

```text
GPU 训练通信链路
NCCL 性能
RDMA / GPUDirect RDMA
真实多机 GPU scaling efficiency
真实 GPU 拓扑感知收益
```

真实 GPU 多机训练链路会多出：

```text
NVIDIA device plugin
GPU 设备暴露
backend=nccl
CUDA tensor
RDMA device plugin
NCCL 环境变量
GPU / NIC / NUMA / PCIe 拓扑
```

### 7.2 checkpoint 恢复边界

当前实现：

```text
只让 rank0 挂 checkpoint PVC
rank0 写 marker.txt
rank0 写 latest.pt
```

`latest.pt` 当前保存：

```text
model_state_dict
optimizer_state_dict
last_step
world_size
```

当前不支持完整自动恢复。原因：

```text
rank1/rank2 没有挂 checkpoint PVC，不能直接读取 /checkpoint/latest.pt。
如果要完整多 rank 恢复，需要共享存储，或由 rank0 读取后通过分布式通信广播参数和必要状态。
恢复训练还需要考虑随机数状态、数据迭代位置、optimizer state、world_size 变化等问题。
```

当前 checkpoint 目标是：

```text
验证 checkpoint 能跨 Pod 生命周期落到 PVC 背后的 PV。
暂不实现完整恢复训练状态机。
```

### 7.3 local-path 边界

kind 默认 `local-path` 适合本地实验，不适合作为真实多节点共享 checkpoint 方案。

原因：

```text
local-path PV 背后是某个 Node 的本地路径。
ReadWriteOnce 只保证一个 Node 读写挂载。
如果 rank0 下一次被调度到另一个 Node，可能读不到上一次 rank0 写出的本地 checkpoint。
```

真实环境可以考虑：

```text
RWX 共享文件系统
对象存储
固定 rank0 调度位置
rank0 上传 checkpoint，启动时下载
```

这些属于后续演进，不是当前 demo 的验收项。

## 8. 面试版表达

可以这样概括当前项目：

```text
我实现了一个基于 Kubernetes 的训练任务最小控制面。用户提交 TrainJob CR 后，controller 会按 worldSize 展开 DDP worker Pod，注入 rank/world_size/master 等启动契约，并把 Pod 交给自定义 scheduler profile。scheduler 通过 Kubernetes 原生 extended resource 模型做资源过滤，再通过自定义 Score 插件按节点策略打分。worker 启动后使用 Gloo 完成多 Pod DDP 训练，rank0 将 checkpoint 写入 PVC。这个 demo 验证了 TrainJob 控制面、调度器扩展、DDP 启动契约和 checkpoint 持久化链路。
```

边界表达：

```text
本地实验使用 kind + CPU/Gloo，只验证平台控制面和 DDP 契约，不声称覆盖真实 GPU/NCCL/RDMA 性能。真实 GPU 集群中还需要接入 NVIDIA device plugin、DCGM 指标、NCCL backend、GPU/RDMA 设备暴露和拓扑感知调度。
```
