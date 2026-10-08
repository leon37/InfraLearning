# DDP 通信边界：Gloo / NCCL / RDMA

## 1. 文档定位

本文记录当前 `AIInfraDDPLab` 在 kind + CPU/Gloo 环境下验证了什么，以及没有验证什么。

目标：

```text
能把当前 demo 的价值收回到平台控制面和 DDP 启动契约。
不把 kind + CPU/Gloo 包装成真实 GPU/NCCL/RDMA 性能经验。
能说出进入真实 GPU 环境后的第一批补齐项。
```

## 2. 当前实验实际验证了什么

当前环境：

```text
kind 集群
Pod 网络
CPU tensor
backend=gloo
```

实际验证了：

```text
TrainJob controller 能展开 DDP worker Pod。
controller 能注入 MASTER_ADDR / MASTER_PORT / RANK / WORLD_SIZE / LOCAL_RANK。
rank0 Service 能作为 rendezvous 稳定入口。
worker 能通过 init_process_group(backend="gloo") 加入同一个 process group。
CPU tensor 能在 Pod 网络下执行 collective communication。
慢 rank 会拖住同步 DDP group。
Pod / TrainJob 状态能反映训练任务生命周期。
```

一句话：

```text
当前 demo 验证的是 AI workload 控制面和 DDP 启动契约，不是 GPU 通信性能。
```

## 3. 当前实验没有验证什么

当前没有验证：

```text
CUDA tensor 通信
NCCL backend
真实 GPU 到 GPU 的 collective communication
多机 GPU scaling
NCCL 拓扑选择
NCCL 性能调优
RDMA / GPUDirect RDMA
真实 GPU 集群网络排障
```

不要说：

```text
这只是换硬件。
```

更准确的说法是：

```text
GPU/NCCL/RDMA 引入了新的设备、后端、显存、网卡、驱动、拓扑和性能路径。
当前实验只能类比 DDP 的启动语义，不能类比真实 GPU 通信性能。
```

## 4. Gloo 和 NCCL 的最小区别

当前 Gloo 实验：

```text
主要跑 CPU tensor。
适合验证 process group、rendezvous、collective communication 的基本语义。
```

NCCL：

```text
主要面向 GPU tensor 的高性能 collective communication。
真实训练中常用于多 GPU / 多机 GPU 的 DDP 梯度同步。
```

关键边界：

```text
init_process_group 成功，只说明 rank 完成 rendezvous，并初始化了 process group。
具体 all_reduce 是否成功，还依赖 backend、tensor 所在设备、rank 到 GPU 的映射、CUDA/NCCL 环境和底层网络路径。
```

因此：

```text
init_process_group 成功不代表 NCCL all_reduce 一定成功。
```

## 5. RDMA / GPUDirect RDMA 的边界

RDMA 是：

```text
Remote Direct Memory Access，远程直接内存访问。
```

它不是用来解决：

```text
Pod 创建
rank 分配
schedulerName
TrainJob 状态机
```

这些控制面问题。

它更接近：

```text
多机 GPU 训练通信路径性能优化。
```

GPUDirect RDMA 关注的是：

```text
网卡尽量直接访问 GPU 显存，减少 CPU 主机内存和内核网络栈中转。
```

当前 kind + CPU/Gloo demo：

```text
完全没有验证 RDMA / GPUDirect RDMA。
```

面试表达：

```text
RDMA 我没有实操经验。我知道它属于真实多机 GPU 训练通信路径优化，和 Kubernetes 控制面不是一个层次。我的本地 demo 没验证 RDMA，只验证了 DDP 启动契约和 Pod 网络下的 Gloo collective。
```

## 6. 真实 GPU 环境第一批补齐项

进入真实 GPU 环境后，第一批补齐顺序：

```text
1. NVIDIA device plugin
2. CUDA tensor
3. NCCL backend
4. GPU 指标
```

### 6.1 NVIDIA device plugin

目的：

```text
让真实 GPU 以 nvidia.com/gpu 这类资源进入 Node.status.allocatable。
```

它解决的是：

```text
Kubernetes 资源上报和分配入口。
```

没有这个入口，scheduler 没有真实 GPU 资源账本。

### 6.2 CUDA tensor

目的：

```text
确认 worker 真的在 GPU 上训练，而不是继续跑 CPU tensor。
```

### 6.3 NCCL backend

目的：

```text
把 backend 从 gloo 切到 nccl，验证 GPU tensor collective communication。
```

### 6.4 GPU 指标

建议接：

```text
DCGM
Prometheus
```

观察：

```text
GPU 利用率
显存
step time
通信/等待相关指标
```

RDMA / GPUDirect RDMA：

```text
先保持边界认知，不作为第一批实操项。
```

## 7. 面试回答底稿

如果被问：

```text
你的项目是否验证了真实 GPU 集群里的 NCCL/RDMA 性能？
```

可以回答：

```text
没有验证真实 GPU/NCCL/RDMA 性能。当前 demo 验证的是训练平台控制面和 DDP 启动契约：controller 展开 worker，scheduler 绑定 Pod，worker 通过 MASTER_ADDR/RANK/WORLD_SIZE 加入 process group，并在 Pod 网络下用 Gloo 跑 CPU tensor collective。

如果进入真实 GPU 环境，我第一步会接 NVIDIA device plugin，让 GPU 资源进入 Node allocatable；然后用 CUDA tensor 和 NCCL backend 验证 GPU DDP；再接 DCGM/Prometheus 看 GPU 利用率、显存和 step time。RDMA/GPUDirect RDMA 我目前只有边界认知，不会包装成已经做过性能优化。
```

