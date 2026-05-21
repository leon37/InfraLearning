# 三项目投递前查漏补缺进度

## 1. 文档定位

本文只记录投递前查漏补缺的执行进度。

对应计划文档：

```text
docs/pre-interview-gap-closure-plan.md
```

使用规则：

```text
计划文档回答“要补什么、为什么补、怎么验收”。
进度文档回答“补到哪了、证据在哪、下一步是什么”。
```

不要在本文里重复大段原理。每完成一个补缺点，只记录状态、产物路径和验收结果。

## 2. 总体状态

当前阶段：

```text
投递前查漏补缺
```

当前目标：

```text
补齐 TrainJob Operator、Scheduler Plugin、DDPLab 三个项目中面试最容易被追问的薄弱点。
```

投递门槛：

```text
完成状态机、Pending 排障、资源账本、DDP 启动契约、checkpoint 恢复边界、通信边界六类材料，并能从空集群复现一次 happy path 和一次失败排障。
```

## 3. 补缺项进度表

| 编号 | 方向 | 补缺项 | 目标产物 | 状态 | 验收结果 |
| --- | --- | --- | --- | --- | --- |
| G1 | TrainJob Operator | TrainJob 状态机 | `docs/trainjob-state-machine.md` | 已完成 | 已完成状态组合、混合 Running/Succeeded、失败重试和耗尽重试四类验收 |
| G2 | TrainJob Operator | rank1 Pending 失败复盘 | `docs/failure-case-rank1-pending.md` | 暂存 | 文档初稿已完成；完整命令口述验收跳过，后续结合真实故障实操验收 |
| G3 | TrainJob Operator / Scheduler | gang scheduling 边界说明 | `docs/trainjob-state-machine.md` | 已完成 | 已能区分当前状态聚合/重试与真正 gang scheduling；能说明 controller 补偿和 scheduler 准入边界 |
| G4 | Scheduler Plugin | Kubernetes 资源账本链路 | `docs/scheduler-resource-accounting.md` | 已完成 | 已能说清 requests/allocatable、device plugin/kubelet 上报链路、allocatable 非实时剩余量 |
| G5 | Scheduler Plugin | Pending 排障剧本 | `docs/scheduler-pending-playbook.md` | 已完成 | 已能区分 scheduler 未接管、Filter 失败、绑定后 kubelet 阶段失败和 Score 不符合预期 |
| G6 | Scheduler Plugin | 调度增强路线：queue/quota/priority | 可放入 `docs/scheduler-resource-accounting.md` 或独立文档 | 暂存 | queue/quota/priority 与 preemption 边界仍有表达分歧，先暂存后续复核 |
| G7 | DDPLab | DDP worker 启动契约 | `docs/ddp-worker-contract.md` | 已完成 | 已能说清 torchrun/controller/init_process_group、rank0 Service、attempt selector、LOCAL_RANK 边界 |
| G8 | DDPLab | checkpoint 恢复边界 | `docs/checkpoint-restore-boundary.md` | 已完成 | 已能说清 latest.pt 字段、恢复顺序、optimizer 状态、rank0-only PVC 与 RWO/local-path 边界 |
| G9 | DDPLab | Gloo/NCCL/RDMA 通信边界 | `docs/ddp-communication-boundary.md` | 未开始 | - |
| G10 | 端到端 | 从空集群复现 happy path | 记录到对应复盘文档 | 未开始 | - |
| G11 | 端到端 | 主动制造一次失败并完成排障 | 记录到对应复盘文档 | 未开始 | - |
| G12 | 面试表达 | 二次模拟面试复测 | 更新 `docs/interview-playbook.md` | 未开始 | - |

## 4. 当前任务

当前只推进一个最小任务：

```text
G9：Gloo/NCCL/RDMA 通信边界。
```

目标产物：

```text
docs/ddp-communication-boundary.md
```

验收标准：

```text
能说清当前 kind + CPU/Gloo 实验验证了什么。
能说清它没有验证 GPU/NCCL/RDMA 哪些能力。
能把当前项目价值收回到 AI workload 控制面和 DDP 启动契约。
```

## 5. 完成记录

### 2026-05-18

- 新建投递前查漏补缺计划：`docs/pre-interview-gap-closure-plan.md`
- 新建投递前查漏补缺进度表：`docs/pre-interview-gap-closure-progress.md`
- G1 文档初稿完成：新增 `docs/trainjob-state-machine.md`
- 纠正执行方式：文档完成不等于用户查漏补缺完成，G1 需要先做理解验收
- G1 验收题 1：
  - 场景：`worldSize=2`，rank0 `Running` 且 Ready，rank1 `Pending`，无 Pod `Failed`
  - 用户不看代码判断：TrainJob 为 `Starting`，因为不是所有 Pod 都 `Running`
  - 用户看代码后修正：TrainJob 为 `Starting`，因为不是所有 Pod 都 Ready
  - 纠偏：phase 判断正确；但 rank0 卡住的直接原因不是“节点资源不够”，而是 `worldSize=2` 的 DDP group 缺少 rank1 进程加入。节点资源不够只是 rank1 `Pending` 的可能原因之一。
- G1 验收题 2：
  - 场景：`worldSize=2`，rank0 `Succeeded`，rank1 `Running` 且 Ready，无 Pod `Failed`
  - 用户不看代码判断：TrainJob 为 `Running`
  - 用户看代码后修正：认为如果 `Succeeded` 和 Ready 不冲突则为 `Running`，否则为 `Starting`
  - 纠偏：按当时旧代码会是 `Starting`。`nextPhase` 在检查 `ReadyWorkers == worldSize` 之前，先检查 `RunningWorkers < worldSize`；rank0 已经 `Succeeded`，不计入 `RunningWorkers`，所以 `RunningWorkers=1 < worldSize=2`，直接返回 `Starting`。
- G1 状态机设计纠偏：
  - 用户期望：`worldSize=2`，rank0 `Succeeded`，rank1 `Running`，无 Pod `Failed` 时，TrainJob 应该是 `Running`
  - 语义结论：如果 TrainJob phase 表达的是“整组训练是否已经越过启动阶段并仍未最终完成”，则 `Running + Succeeded` 的混合状态应归入 `Running`
  - 纠偏：Pod phase 和 Ready condition 是不同字段，但不代表任意组合都合理。`Succeeded` Pod 已经终止，通常不应再作为 Ready worker 计数。
  - 用户已调整代码：`nextPhase` 改为使用 `RunningWorkers + SucceededWorkers` 判断是否仍处于 `Starting`
  - 文档同步：`docs/trainjob-state-machine.md` 已改为新语义，`ReadyWorkers` 只作为观察字段，不再决定 TrainJob 主 phase
- G1 验收题 3：
  - 场景：`worldSize=2`，`retryLimit=1`，当前 `status.attempt=0`，rank0 `Running`，rank1 `Failed`
  - 用户不看代码判断：TrainJob 进入 `Retrying`，`status.attempt` 变为 1，当前 attempt 的 worker Pod 被删除
  - 用户看代码后修正：与不看代码判断一致
  - 结论：失败重试路径判断正确；补充细节是 rank0 Service 当前不会在 `handleFailedAttempt` 中删除，而是在下一轮 reconcile 中由 `ensureMasterService` 更新 selector 指向新 attempt
- G1 验收题 4：
  - 场景：`worldSize=2`，`retryLimit=1`，当前 `status.attempt=1`，rank0 `Running`，rank1 `Failed`
  - 用户不看代码判断：TrainJob 进入 `Failed`，`status.attempt` 保持不变，当前 attempt 的 worker Pod 不删除
  - 用户看代码后修正：与不看代码判断一致
  - 结论：耗尽重试后的终态判断正确；最后一轮失败现场会保留，便于继续查看日志和 Pod 状态
- G1 结论：通过。当前状态机语义已调整为 `RunningWorkers + SucceededWorkers` 决定是否越过 `Starting`，`ReadyWorkers` 只作为观察字段。
- 进入 G2 初始探测：
  - 场景：TrainJob `Starting`，rank0 `Running`，rank1 `Pending`，rank0 卡在 DDP 初始化
  - 暴露短板：用户能解释 DDP group 缺少 rank1 会卡住，但不熟悉排障命令、对象字段和输出解读顺序
  - 纠偏方向：G2 不直接写复盘文档，先建立固定命令路径：TrainJob 状态 -> worker Pod 列表 -> Pending Pod describe -> Node 资源账本 -> scheduler 日志 -> Service endpoints -> worker logs
- G2 验收题 1：
  - `describe pod` 片段：`Status=Pending`，`Node=<none>`，`Events Reason=FailedScheduling`，`Message=Insufficient aiinfra.leon.com/gpu-capacity`
  - 用户判断：发生在调度前，应看 Pod `resources.requests` 和 Node `status.allocatable`，与 DDP worker 代码无直接关系，因为 Pod 还没绑定到 Node，进程未启动
  - 结论：通过。已能把资源不足 Pending 与 DDP 代码问题区分开
- G2 验收题 2：
  - `describe pod` 片段：`Status=Pending`，`Node=<none>`，`Events Reason=FailedScheduling`，`Message=pod has unbound immediate PersistentVolumeClaims`
  - 用户判断：不是 DDP worker 代码问题；应看 PVC；当前实现只有 rank0 挂载 PVC，所以可能只影响 rank0
  - 结论：通过。补充命令路径为先 `kubectl get pvc` 看 `STATUS/VOLUME/STORAGECLASS`，再 `kubectl describe pvc` 看 Events
- G2 验收题 3：
  - `describe pod` 片段：`Status=Pending`，`Node=kind-worker2`，Events 已有 `Scheduled`，随后 `Failed to pull image`
  - 用户判断：已经绑定到 Node 之后，不再优先看 scheduler 日志；问题是 worker 镜像未加载到 kind 集群
  - 结论：通过。已能根据 `Node=<none>` 与具体 Node 区分调度阶段和 kubelet/镜像阶段
- G2 验收题 4：
  - 场景：rank0/rank1 都 `Running`，但 rank1 连接 `MASTER_ADDR` 失败；`kubectl get endpoints trainjob-sample-master -o yaml` 输出 `subsets: []`
  - 用户判断：能说出 rank1 通过 Service 找不到 rendezvous 入口；能联想到 attempt，但对 `subsets: []` 的含义和 selector/labels 对照还不够稳
  - 纠偏：`subsets: []` 表示 Service 当前没有可用后端 endpoint；下一步应对照 Service `spec.selector` 与 rank0 Pod `metadata.labels`
- G2 文档初稿完成：新增 `docs/failure-case-rank1-pending.md`
- G2 完整验收第一次：
  - 场景：TrainJob `Starting`，`worldSize=2`，rank0 `Running`，rank1 `Pending`，rank0 卡在 DDP 初始化
  - 用户回答：能说出先看 TrainJob、Pod、describe Pod；能说出 describe 里看 Events；能在 `FailedScheduling + Insufficient` 时继续查 Pod requests 和 Node allocatable；能解释 DDP 需要 `worldSize` 个 rank 加入 process group
  - 暴露短板：命令不够具体，缺少 label selector、`-o wide`、TrainJob status 字段、Pod `STATUS/NODE` 字段；还没有形成稳定的前 4 条命令
  - 结论：未通过完整验收，需要再练一次固定命令顺序
- G2 执行调整：
  - 用户指出不应过度强调具体 TrainJob 名和 Pod 名，不同环境对象名会变化
  - 调整结论：G2 不继续做命令口述卡点；保留文档和分支判断，后续在真实故障或从空集群复现时再做实操验收
- 进入 G3 初始验收：
  - 场景：TrainJob 创建 `worldSize` 个 Pod，rank0 已调度并 `Running`，rank1 因资源不足一直 `Pending`
  - 用户判断：这不是真正 gang scheduling；scheduler 没有把这些 Pod 当作整体调度；rank0 会等待 rank1，既不能开始业务，也不能释放资源
  - 结论：核心判断正确。下一步补“controller 层能做什么、scheduler 层必须做什么”的边界
- G3 验收题 2：
  - 场景：不改 scheduler，只在 controller 中加入长时间 `Starting` 后删除已 `Running` rank0 的逻辑
  - 用户判断：能缓解 rank0 长时间不释放资源；但本质仍是逐个 Pod 调度，只是治标不治本；真正 gang scheduling 还需要 scheduler 侧逻辑
  - 结论：通过。已能区分 controller 事后补偿和 scheduler 事前准入
- G3 文档同步：已在 `docs/trainjob-state-machine.md` 补充 gang scheduling 边界
- G3 最终验收：
  - 用户回答：当前没有实现 gang scheduling；当前只是通过 DDP process group 和失败重试表达整组训练运行与重试；调度仍以单 Pod 为单位，可能导致 rank0 已绑定并占资源但等待 rank1；下一步要补 scheduler，因为整组 Pod 的准入必须在调度侧表达
  - 纠偏：是 `process_group`，不是 `progress_group`；DDP 要求所有 rank 加入通信组，不等于 scheduler 保证同时开始
  - 结论：G3 通过
- 进入 G4 初始验收：
  - 场景：Pod 请求 `resources.requests.aiinfra.leon.com/gpu-capacity=1024000`，scheduler 判断 Node 是否能承载
  - 用户回答：比较 Pod `spec.containers[].resources.requests` 和 Node `status.allocatable`；不应用 Node label 做硬性资源判断；当前 kind demo 通过 patch 修改 Node；真实 GPU 集群由 device plugin 上报
  - 纠偏：前三点正确；第四点需要细化，device plugin 不是直接写 apiserver，而是向 kubelet 注册/汇报设备，kubelet 再更新 Node status 到 apiserver
- G4 验收题 2：
  - 问题：为什么 scheduler 不直接去每台 Node 探测 GPU
  - 用户回答：核心是解耦；各种资源通过 kubelet 上报 apiserver，scheduler 只需要从 apiserver 查询
  - 纠偏：方向正确，需要补全为“节点侧负责发现与上报，apiserver 保存统一资源账本，scheduler 消费账本做调度决策”
- G4 验收题 3：
  - 问题：Node `capacity`、`allocatable`、已运行 Pod requests 与 scheduler 可用量的关系
  - 用户回答：`capacity` 是总资源，`allocatable` 是可分配资源；对 “allocatable=4，已有两个 Pod 各 request 1” 的例子产生疑问，认为 allocatable 是否应该变成 2，或者应该用 `allocatable - requests`
  - 纠偏方向：这是 G4 的核心。`Node.status.allocatable` 是 Node 对象上的可分配上限，不会因为普通 Pod 被调度就直接扣成剩余值；scheduler 在自己的调度视图里用 NodeInfo 汇总已分配 Pod requests，再计算剩余可用量
- G4 验收题 4：
  - 场景：Node allocatable 为 `3000000`，已有两个 Pod 各 request `1024000`，新 Pod request `1024000`
  - 用户判断：Node.status.allocatable 不会因为已有 Pod 运行而变成 `952000`；scheduler 用 `allocatable - podA.requests - podB.requests` 计算；新 Pod 不能放，因为 `952000 < 1024000`
  - 结论：通过。已区分 Node 对象上的 allocatable 上限和 scheduler 调度视图里的剩余可用量
- G4 文档初稿完成：新增 `docs/scheduler-resource-accounting.md`
- G4 最终验收：
  - 用户回答：Pod requests 对 Node allocatable；Node label 不应表达硬资源；kind demo 通过 patch 修改 Node status；真实链路为 device plugin + kubelet 节点侧上报，apiserver/etcd 存储，scheduler 消费；Node.status.allocatable 不是实时剩余量，还要减掉 scheduler cache 里的 Pod requests
  - 纠偏：`requests` 拼写；device plugin 是发现/管理本节点设备并向 kubelet 注册资源，不是汇总整个集群资源
  - 结论：G4 通过
- 进入 G5 初始验收：
  - 场景：worker Pod `Pending`，`spec.schedulerName=my-custom-scheduler`，`spec.nodeName` 为空，Pod Events 为空或长期没有 `FailedScheduling`
  - 用户判断：优先怀疑 custom scheduler 没有接管，因为 Events 为空；下一步检查 scheduler 进程/日志；默认 kube-scheduler 不负责该 Pod
  - 结论：通过。已能把 `schedulerName` 指向自定义 scheduler 与默认 scheduler 不接管关联起来
- G5 验收题 2：
  - 场景：worker Pod `Pending`，`schedulerName=my-custom-scheduler`，`nodeName` 为空，Events 出现 `FailedScheduling` 和 `Insufficient aiinfra.leon.com/gpu-capacity`
  - 用户判断：custom scheduler 已接管；这是 Filter 阶段判断失败；下一步查 Pod requests 和 Node allocatable
  - 结论：通过。已能区分 scheduler 未接管和接管后资源过滤失败
- G5 验收题 3：
  - 场景：custom scheduler 启动后退出，日志为 `plugin "NodeLabelScore" does not extend ScorePlugin plugin`
  - 用户判断：发生在 scheduler 启动加载 profile/plugin 的过程中；Pod 会保持 `Pending`；应检查 SchedulerPlugin 的实现
  - 结论：通过。补充检查点是插件是否真正实现对应扩展点接口、Kubernetes 版本下的接口签名是否匹配、工厂函数返回值和 profile 中插件名是否一致
- G5 验收题 4：
  - 场景：Pod 已绑定到 Node，但没有分到期望的最高分节点
  - 用户判断：这是 Score 阶段排序/权重问题，不会导致 Pod Pending；但不清楚应检查 NodeLabelScore 的哪些输入
  - 纠偏：Score 排障优先看 NodeLabelScore 依赖的 Node label、插件配置、profile 中 Score 插件权重、scheduler 日志中的打分输出
- G5 追加边界：
  - 用户追问：一般情况下 ScorePlugin 给每个节点打分的 score 是否都放在 Node label 里
  - 结论：不是。当前 NodeLabelScore 是教学版/实验版插件，用 Node label 作为简单输入来验证 ScorePlugin 接入；真实 ScorePlugin 更可能基于资源剩余、拓扑、亲和性、负载、设备信息等动态计算分数
- G5 文档初稿完成：新增 `docs/scheduler-pending-playbook.md`
- G5 最终验收：
  - 用户回答：Events 为空且 `nodeName` 为空时说明 custom scheduler 没接管；`FailedScheduling + Insufficient` 说明 Filter 失败，应看 Pod requests 和 Node allocatable；`nodeName` 已有值但 image pull failed 说明绑定后 kubelet 阶段失败；Pod 绑定成功但不是期望节点属于 ScorePlugin 问题，应检查打分逻辑
  - 纠偏：Score 排障可更具体到 Node label、插件配置、权重和 scheduler 日志
  - 结论：G5 通过
- 进入 G6 初始验收：
  - 场景：多个用户同时提交 TrainJob，资源有限，不能让单用户无限占用，重要任务不能长期排队
  - 用户回答：queue 解决同优先级任务按提交时间执行；不知道 quota；priority 让重要任务优先执行；倾向于只放 scheduler，因为这是 job 创建后的调度问题
  - 暴露短板：queue/quota/priority 的平台对象边界不清；需要区分用户侧声明、controller 状态管理和 scheduler 调度消费
- G6 讨论暂存：
  - 用户对 priority、quota、queue 与 preemption 的边界提出疑问，重点争议在“高优先级任务是否必须等待已经运行的低优先级任务”
  - 暂存结论：priority 至少影响等待队列顺序；是否能让已运行低优先级任务让位取决于 preemption；quota 限制 queue/用户资源上限；queue 提供任务归属和排队/配额边界
  - 由于当前讨论收益下降，G6 暂存，后续结合具体对象模型再复核
- 进入 G7 初始验收：
  - 问题：torchrun、TrainJob controller、`init_process_group(env://)` 的职责边界
  - 用户回答：torchrun 负责启动进程、注入变量；不确定通信建立是否由 torchrun 做；controller 替代注入变量和启动进程；`env://` 依赖 `WORLD_SIZE/MASTER_ADDR/MASTER_PORT/RANK/LOCAL_RANK`；`LOCAL_RANK=0` 因为当前 1 Pod = 1 worker process
  - 纠偏：torchrun 提供启动器和 rendezvous 所需环境；真正加入通信组的是 worker 进程中调用的 `dist.init_process_group`
- G7 验收题 2：
  - 问题：为什么 `MASTER_ADDR` 不应让用户在 TrainJob YAML 中手填 Pod IP，为什么 controller 要用 rank0 Service 生成 `MASTER_ADDR`
  - 用户回答：Pod 重启或新 attempt 会导致 Pod IP 变化，其他 rank 可能找不到 rank0；rank0 Service 提供稳定 rendezvous 入口
  - 结论：通过。补充拼写为 `rendezvous`
- G7 验收题 3：
  - 问题：rank0 Service selector 为什么不能只包含 `trainjob-name` 和 `rank=0`，必须包含 `attempt`
  - 用户回答：可能选中 lastFailedAttempt 中尚未销毁的 rank0，导致新的 DDP group 初始化混乱；如果旧 rank0 在过程中被删除，整个 group 会卡在初始化阶段
  - 结论：通过
- G7 文档初稿完成：新增 `docs/ddp-worker-contract.md`
- G7 最终验收：
  - 用户回答：torchrun 负责分配 rank、注入 world/rank 变量、启动进程和管理生命周期；controller 替代环境变量注入；`init_process_group` 负责让 rank 建立通信；`MASTER_ADDR` 和 rank0 Service 提供稳定 rendezvous 入口；attempt selector 防止旧 attempt rank0 进入 endpoints；`LOCAL_RANK` 表示当前 Pod 内第几个训练进程
  - 纠偏：controller 不只是注入变量，还负责创建跨 Pod worker；当前 `1 Pod = 1 worker process`，所以 `LOCAL_RANK=0`；拼写为 `rendezvous`
  - 结论：G7 通过
- 进入 G8 初始验收：
  - 场景：rank0 挂 PVC 到 `/checkpoint`，写入 `latest.pt`，包含 `model_state_dict`、`optimizer_state_dict`、`last_step`、`world_size`
  - 用户回答：`model_state_dict` 恢复模型权重，`optimizer_state_dict` 恢复优化器状态，`last_step` 用于从中断步数继续，`world_size` 保证恢复后 group 成员数保持一致；model 应在 `DDP(model)` 前加载；optimizer 加载位置不确定；rank0-only PVC 不能完整恢复，因为其他 rank 没挂 PVC
  - 纠偏：optimizer state 应在 optimizer 创建之后加载，因为 optimizer state 绑定已经创建好的参数对象
- G8 验收题 2：
  - 问题：只保存 `model_state_dict`，不保存 `optimizer_state_dict`，恢复后能否继续训练以及影响是什么
  - 用户回答：程序上可以继续跑；训练语义上丢失 optimizer 的动量、二阶矩等状态；可能导致 loss 曲线抖动、收敛变差，极端情况下可能不稳定
  - 结论：通过。补充措辞为不一定 loss 爆炸，但优化器连续性被破坏
- G8 验收题 3：
  - 问题：当前 rank0-only PVC 为什么不能叫完整自动恢复
  - 用户回答：只有 rank0 挂 PVC，其他 rank 没有读取 `latest.pt` 的路径
  - 结论：通过。当前只能证明 rank0 checkpoint 持久化链路已通，不能证明整组 worker 自动恢复
- G8 验收题 4：
  - 问题：如果所有 rank 都直接读取 `/checkpoint/latest.pt`，checkpoint 存储需要什么访问能力
  - 纠偏：关键不是是否持久化，而是所有 rank 是否能看到同一份 `latest.pt`；跨 Node 时需要 RWX 或等价共享存储
- G8 验收题 5：
  - 场景：kind local-path PVC 为 RWO，PV 绑定在 `kind-worker2`；下一次 rank0 被调度到 `kind-worker`
  - 用户判断：不能直接读到同一个 local-path PV，因为 RWO 是 Node 边界，PV 已绑定到 `kind-worker2`，`kind-worker` 不能挂载该 PV
  - 结论：通过。已理解 RWO/local-path 对 checkpoint 恢复调度位置的限制
- G8 验收题 6：
  - 场景：只有 rank0 能读 `latest.pt`，然后 rank0 把模型参数同步给其他 rank
  - 用户判断：同步必须发生在 DDP 训练继续之前；`optimizer_state_dict` 也要考虑同步，因为其中有动量、二阶矩等训练状态；复杂度是 rank0 要广播，非 rank0 要接收广播并更新内存数据
  - 结论：通过。已能区分共享存储读取和 rank0 广播两条恢复路线
- G8 文档初稿完成：新增 `docs/checkpoint-restore-boundary.md`
- G8 最终验收：
  - 用户回答：`latest.pt` 至少保存 `model_state_dict`、`optimizer_state_dict`、`last_step`；`model_state_dict` 在初始化 model 后加载，`optimizer_state_dict` 在基于 model 参数创建 optimizer 后加载；只保存模型会丢失动量、二阶矩等历史状态并影响收敛；rank0-only PVC 不等于完整恢复，因为其他 rank 没有读取 `latest.pt` 的路径；RWO/local-path 只能被绑定 Node 使用，跨 Node rank 无法直接读取保存数据
  - 纠偏：字段名建议统一为 `model_state_dict` / `optimizer_state_dict`；`world_size` 也应保存或校验，以确认恢复时 group 规模一致
  - 结论：G8 通过
- 暂停项：根据当前窗口上下文沉淀 `aiinfra-gap-closure` skill 草稿
- Skill 产物：`skills/aiinfra-gap-closure/SKILL.md`
- 恢复后从 G9 继续
