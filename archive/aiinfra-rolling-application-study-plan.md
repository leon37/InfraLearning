# AI Infra 边投边学滚动执行计划

## 1. 文档定位

本文是执行计划，不是长期路线图。

它回答：

```text
AI Infra 版简历已经生成后，接下来 4 周每周具体推进什么？
投递、学习、文档、面试反馈如何形成闭环？
```

对应总路线：

```text
docs/aiinfra-knowledge-gap-roadmap.md
```

当前策略：

```text
不等知识全部补完再投递。
用第一批投递和面试反馈校准学习优先级。
每周只补一个 AI Infra 主问题。
传统后端 FamilySystem / Rank 在另一个窗口处理，本计划不覆盖。
```

## 2. 执行原则

### 2.1 投递不中断

每周至少保留一次投递动作。

```text
第一目标不是马上拿 offer，而是拿真实市场反馈。
```

投递优先级：

```text
AI 平台
机器学习平台
训练平台控制面
算力平台
Kubernetes / Scheduler / Operator
AI SRE
```

暂不优先：

```text
CUDA / Triton 算子岗
NCCL / RDMA 性能优化专家岗
千卡训练框架核心岗
纯 Agent 应用岗
外包或薪资明显不达标岗位
```

### 2.2 学习不扩散

每周只允许一个主学习问题。

如果当周主问题是：

```text
queue / quota / priority
```

就不要同时开：

```text
vLLM
NCCL
DCGM
多集群
CSI
```

### 2.3 产物必须可验证

每周必须留下一个可被面试复用的产物：

```text
设计文档
最小实验
排障记录
面试回答底稿
```

没有产物的学习不计入完成。

### 2.4 反馈可以改计划

如果收到面试反馈，当周计划可以调整。

优先级规则：

```text
真实面试反馈 > JD 高频要求 > 个人兴趣
```

但一次只改下一周，不推翻整条路线。

## 3. 每周固定节奏

不细化到每天，只保留周内节奏。

每周按这个顺序推进：

| 顺序 | 动作 | 目的 | 产物 |
| --- | --- | --- | --- |
| 1 | 选本周主问题 | 防止扩散 | 本周目标一句话 |
| 2 | 先回答设计直觉 | 暴露盲区 | 对话中的原始回答 |
| 3 | 纠偏并形成对象模型 | 把概念落到字段、状态、对象关系 | 设计文档初稿 |
| 4 | 补一个最小实验或验证命令 | 避免纯文档化 | 命令、输出字段或伪代码 |
| 5 | 整理面试回答底稿 | 能投递和面试复用 | 2 分钟回答 |
| 6 | 投递或复盘投递 | 获取真实反馈 | 投递记录或反馈记录 |

## 4. 投递记录格式

后续可独立落为：

```text
docs/job-application-tracker.md
```

每个岗位只记录必要字段：

```text
日期：
公司：
岗位：
城市：
薪资：
入口：
JD 关键词：
为什么我能投：
最可能被问倒的点：
投递状态：
反馈问题：
下一步动作：
```

判断标准：

```text
如果岗位能触发面试或沟通，记录面试问题。
如果无回复，也记录 JD 关键词，用来判断简历关键词是否需要改。
```

## 5. 4 周滚动计划

### Week 1：queue / quota / priority / preemption 对象边界

本周目标：

```text
把“多个用户提交训练任务，资源不够时怎么排队和限制资源”讲清楚。
```

为什么先做：

```text
这是当前 G6 暂存项。
它直接对应算力平台、机器学习平台、训练平台控制面岗位。
它能把项目从“单个 TrainJob demo”推进到“平台调度雏形”。
```

输入：

```text
当前 TrainJob CRD
当前 SchedulerPlugin
docs/scheduler-resource-accounting.md
docs/trainjob-state-machine.md
docs/national-computing-network-response.md
```

本周只解决：

```text
TrainJob 应该声明哪些排队相关字段。
Queue / Tenant 应该保存哪些配额相关字段。
scheduler 调度时需要消费哪些字段。
controller 应该写回哪些 status。
priority 和 preemption 的边界。
当前项目为什么还不是真正 gang scheduling。
```

本周不做：

```text
不实现完整 queue controller。
不手写完整 gang scheduler。
不引入 Volcano / Kueue 代码。
不做抢占真实删除 Pod 的实现。
```

目标产物：

```text
docs/trainjob-queue-quota-priority-design.md
```

文档必须包含：

```text
对象关系图：TrainJob / Queue / Tenant 或 Project / Pod
字段草案：spec.queueName、spec.priority、status.queuedReason、status.queueLatency 等
scheduler 需要消费的信息
controller 需要写回的信息
priority / quota / preemption 的区别
当前项目能补什么，暂时不补什么
```

验收问题：

```text
1. queue 解决什么问题？
2. quota 解决什么问题？
3. priority 解决什么问题？
4. preemption 和 priority 是不是一回事？
5. 为什么 quota 不应该散落在每个 TrainJob 里？
6. 如果只改 controller，不改 scheduler，能不能实现真正 gang scheduling？
```

面试回答目标：

```text
我当前 demo 还没有完整 queue/quota/priority，但我会把它设计成平台对象，而不是继续往 Node label 里堆分数。TrainJob 表达任务诉求，Queue/Tenant 表达资源边界，scheduler 消费 queue 和 priority 做准入与排序，controller 把排队原因和等待时间写回 status。
```

### Week 2：MLOps 对象模型

本周目标：

```text
让当前 TrainJob 项目能嵌入机器学习平台全链路，而不是只像一个调度 demo。
```

为什么做：

```text
机器学习平台岗位不会只问“怎么创建 Pod”。
它会问训练数据、checkpoint、模型产物、模型注册、部署和回滚。
```

输入：

```text
当前 TrainJob 字段
docs/checkpoint-restore-boundary.md
docs/ddp-worker-contract.md
docs/aiinfra-demo.md
```

本周只解决：

```text
Dataset、TrainJob、Checkpoint、Model、ServingEndpoint 的关系。
checkpoint 和 model artifact 的区别。
训练完成后模型如何进入注册和部署链路。
ServingEndpoint 为什么不是 TrainJob phase。
```

本周不做：

```text
不实现完整 Model Registry。
不接对象存储。
不做复杂前端。
不做在线模型灰度发布系统。
```

目标产物：

```text
docs/mlops-object-model.md
```

文档必须包含：

```text
对象关系图
每个对象解决的问题
TrainJob status 和 Model status 的边界
checkpoint 与最终模型产物的区别
最小面试回答底稿
```

验收问题：

```text
1. Dataset 和 PVC 是不是一回事？
2. Checkpoint 和 Model Artifact 是不是一回事？
3. TrainJob Succeeded 后，平台下一步应该产生什么对象？
4. ServingEndpoint 为什么不应该塞进 TrainJob phase？
5. 如果模型回滚，回滚的是 TrainJob 还是 Model / Serving 配置？
```

### Week 3：推理服务最小链路

本周目标：

```text
补上推理平台 JD 的最低沟通门槛。
```

为什么做：

```text
很多 AI Infra 岗位同时覆盖训练和推理。
当前三个项目偏训练任务控制面，推理服务链路为空。
```

输入：

```text
当前 Kubernetes 基础
AIInfraTrainJob 中的 Service / Pod / status 心智
```

本周只解决：

```text
一个最小模型服务如何在 K8s 里运行。
训练任务和推理服务生命周期有什么不同。
推理服务看哪些指标。
Deployment / Service 如何承载推理入口。
```

本周不做：

```text
无 GPU 环境下不追求 vLLM 性能。
不做高性能 KV cache。
不做 PagedAttention 细节。
不做 Triton 算子优化。
```

目标产物：

```text
../AIInfraServingLab
docs/inference-serving-minimal-lab.md
```

最小实验：

```text
启动一个 HTTP 模型服务进程。
用 Kubernetes Deployment 部署。
用 Service 暴露。
发请求验证响应。
记录 latency / error rate 的最小观测方式。
```

验收问题：

```text
1. 训练任务和推理服务的生命周期差异是什么？
2. 训练看 completion，推理为什么看 availability？
3. 推理服务的核心指标有哪些？
4. Deployment 比 Job 更适合推理服务的原因是什么？
5. vLLM 解决的是平台控制面问题，还是推理运行时和调度问题？
```

### Week 4：GPU 资源入口与平台指标

本周目标：

```text
把 patch Node 模拟资源升级为真实 GPU 资源链路认知，并补平台可观测性。
```

为什么做：

```text
调度岗位会追问 nvidia.com/gpu 从哪里来。
平台岗位会追问如何判断排队慢、运行慢、完成慢。
```

输入：

```text
docs/scheduler-resource-accounting.md
docs/ddp-communication-boundary.md
docs/failure-case-insufficient-resource-2026-05-21.md
```

本周只解决：

```text
NVIDIA device plugin 到 kubelet 的注册链路。
Node.status.capacity / allocatable 的更新边界。
scheduler cache 如何消费资源账本。
queue latency / running time / completion time 的定义。
DCGM / Prometheus 在真实 GPU 环境的位置。
```

本周不做：

```text
不要求真实 GPU 实操。
不调 NCCL 性能。
不深入 RDMA。
不安装完整监控平台。
```

目标产物：

```text
docs/gpu-device-plugin-resource-path.md
docs/trainjob-observability-metrics.md
```

验收问题：

```text
1. device plugin 是直接写 apiserver 吗？
2. kubelet 在 GPU 资源上报里负责什么？
3. scheduler 为什么不直接 SSH 到 Node 探测 GPU？
4. queue latency、running time、completion time 分别定位哪类问题？
5. DCGM 指标和 TrainJob status 是不是同一层信息？
```

## 6. 面试反馈分类

每次面试后，把问题归到下面一类：

| 分类 | 例子 | 处理方式 |
| --- | --- | --- |
| 项目主线 | TrainJob 怎么展开 Pod | 更新 `docs/interview-playbook.md` |
| 调度资源 | requests / allocatable / scheduler cache | 更新 `docs/scheduler-resource-accounting.md` |
| 平台对象 | queue / quota / priority | 更新 Week 1 文档 |
| MLOps | Dataset / Model / Serving | 更新 Week 2 文档 |
| 推理服务 | vLLM / KServe / latency | 更新 Week 3 文档 |
| GPU 资源 | device plugin / DCGM / nvidia.com/gpu | 更新 Week 4 文档 |
| 传统后端 | FamilySystem / Rank / Redis / 高并发 | 交给另一个窗口 |
| 基础算法 | TopK / BFS / DP / 链表 | 交给另一个窗口 |

本窗口只处理：

```text
项目主线
调度资源
平台对象
MLOps
推理服务
GPU 资源
```

## 7. 完成判定

4 周计划完成后，应达到：

```text
能投第一批 AI 平台 / 机器学习平台 / 算力平台岗位。
能讲清当前 demo 的边界。
能解释 queue/quota/priority 设计方向。
能把 TrainJob 放进 MLOps 对象模型。
能说清训练任务和推理服务差异。
能解释真实 GPU 资源如何进入 Kubernetes 资源账本。
能用平台指标解释调度慢、运行慢、完成慢。
```

仍然不声称：

```text
真实 GPU 集群生产经验
NCCL/RDMA 性能优化经验
CUDA/Triton 算子经验
完整生产级训练平台经验
```

## 8. 当前下一步

从 Week 1 开始。

本周第一个问题：

```text
多个用户同时提交 TrainJob，集群资源不足。
平台要如何表达“谁属于哪个排队域、谁最多能用多少资源、谁优先级更高、谁应该继续等待”？
```

先不要写代码。

先只设计对象和字段边界：

```text
TrainJob spec 里放什么？
Queue 或 Tenant 对象里放什么？
TrainJob status 里写回什么？
scheduler 调度时要读什么？
```
