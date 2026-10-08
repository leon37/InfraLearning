# 项目拷打排雷清单

> 用途:记录"面试式拷打"三个项目(TrainJob / SchedulerPlugin / DDPLab)过程中,发现的**看起来像能力、实则空心 / 断裂 / 答不出**的点。
> 每条记录:现象 → 为什么是雷 → 严重度 → 处理动作 → 状态。
> 拷打结束后在末尾做归纳。

- 创建时间:2026-05-29
- 方式:Claude 扮演面试官,用户先盲答(不看源码),再对照真实代码,重点看"盲答与真相的差距"。

---

## 一、已确认的雷(本轮拷打实测)

### L1 — 不熟悉原生 Job,且"为什么不用原生 Job"主线没内化
- **项目**:TrainJob / 概念
- **现象**:回答"为什么不用原生 Job 而自写 TrainJob CRD"时:
  - 事实错误:以为原生 Job 不聚合 Pod 状态(实际 Job 有 `.status.succeeded` / `.status.failed` + `backoffLimit`)。
  - 漏掉最致命的两条:原生 Job 缺 **rank 身份分配** 和 **rendezvous 会合入口**——而这恰恰是 operator 里 `workerEnv()`(注入 RANK/WORLD_SIZE)和 `ensureMasterService()`(rank0 Service + MASTER_ADDR)在做的事。
  - 自承没学过 `completions`/`parallelism`。
- **为什么是雷**:分布式训练平台岗**几乎必问**的开场题,答不好直接出局。
- **严重度**:高
- **处理动作**:
  1. 补原生 Job:`completions` / `parallelism` / `backoffLimit` / `completionMode: Indexed`(尤其 Indexed Job 的 `JOB_COMPLETION_INDEX` 像 rank,但仍不够)。
  2. 练成脱口而出:"原生 Job 把 Pod 当成统计意义上独立可互换的任务;DDP 是需身份+会合+要么一起活要么一起死的紧耦合通信组。Job 给不了 rank 身份、rendezvous、整组重启。"
- **状态**:待办

### L2 — `gang_scheduling.go` 是从未运行的死代码,四层全断
- **项目**:SchedulerPlugin / 严重
- **现象**:对该文件**完全无印象**。实测四层全断:
  1. `main.go` 未注册;且 `NewGangScheduling(handle)` 返回 `*GangScheduling`,不符合 `app.WithPlugin` 要求的 PluginFactory 签名 → 想注册都编不过。
  2. `scheduler-config.yaml` 无 `permit` 扩展点 → 框架不会调用。
  3. 读 label `training.kubeflow.org/job-name`,而 operator 打的是 `trainjob-name` → 读空 → Permit 返回 Error。
  4. 读 annotation `scheduling.aiinfra.io/min-member`,而 `buildWorkerPod` 从不设 annotation → Atoi 失败 → Error。
- **为什么是雷**:面试官看仓库必问;答不出 = 当场承认提交了自己不懂的代码,诚信观感崩塌。
- **严重度**:最高
- **处理动作(二选一)**:
  1. 【保守】删除该文件排雷,故事收敛为"gang 是我清楚边界但未实现的扩展点"。
  2. 【进取/护城河】**自己(非 ChatGPT)真正实现**:改对工厂签名 → 注册 → 配 Permit → 对齐 label/annotation 与 operator → 处理超时与内存泄漏(见 P6)。做成 = 拥有一个能逐行扛追问的硬核亮点。
- **建议**:不急 + 要护城河 + 已有残骸 → 选 2,自己写。
- **状态**:待决策

### L3 — 实际过滤资源的是默认 NodeResourcesFit,不是自写 NodeLabelFilter
- **项目**:SchedulerPlugin / 认知
- **现象**:`NodeLabelFilter` 在 `scheduler-config.yaml` 中被注释停用;真正生效的资源过滤是 K8s **默认 NodeResourcesFit**(对 extended resource `aiinfra.leon.com/gpu-capacity`)。
- **为什么是雷**:被问"谁在过滤资源 / 你的 Filter 做了什么"时会答错。
- **严重度**:中
- **处理动作**:讲清"我自定义的是 Score(读 `node_topological_hint` 打分);资源过滤复用默认 NodeResourcesFit;早期写过 NodeLabelFilter 做 label 模拟,切到 extended resource 后停用,避免 label 与 allocatable 双账本"。
- **状态**:待办(表达层面)

### L4 — `Queued` 是空壳门,与 L2(gang)同属一个深做方向(P1 已确认)
- **项目**:TrainJob / 认知
- **现象**:用户盲答正确——Reconcile 中 `Queued` case **无条件**跳到 `Starting`,没有任何准入/配额判断;`SetupWithManager` 里"Pod 事件唤醒 Queued job"的 Watches 因此形同虚设(没有 job 会真的停在 Queued)。
- **为什么是雷**:对外讲"我有排队/准入"时无法逐行兑现;且这正是用户一直没内化的 queue/quota 区域。
- **严重度**:中(表达)/高(护城河价值)
- **处理动作**:与 L2 合并成同一深做方向 —— **"mini Kueue + Volcano":平台侧准入(Queue/Quota)+ 调度侧 gang(Permit)**。Queued 要真正成为准入门(配额不足则停在 Queued,资源释放后被唤醒),正好让那段 Pod-watch Watches 名副其实。
- **状态**:待决策(同 L2 合并)

---

## 二、待拷打项(已在代码里看到、本轮还没考)

> 后续逐个盲答验收,通过的移出,答不出的升级为正式雷。
- **P2 [TrainJob]** 死代码:`isResourceValid()` 永远返回 false 且从未被调用;`deleteServiceForAttempt()` 从未被调用。
- **P3 [TrainJob] ✅ 已验收(表达校准类)** 用户盲答正确:状态机靠"改 status → 自己发 watch 事件 → 推进一格"的自循环驱动;`Result{}` 为空、不靠显式 requeue。已识别两种 stall 场景:(A) 写入内容与现状相同 → apiserver 不 bump resourceVersion、不发事件;(B) `For()` 加 `GenerationChangedPredicate` → status 改动不动 generation、事件被全挡。**结论**:把 level-triggered 模型掰成 edge-triggered,脆且依赖隐性契约;正解为显式 `Requeue`/`RequeueAfter` 或一次性收敛。
- **P4 [TrainJob]** 没有 finalizer:要能解释为什么不需要(OwnerReference + GC 级联删 Pod/Svc),以及什么场景才必须用 finalizer。
- **P5 [Scheduler]** `NodeLabelScore` 读 `node_topological_hint` label 打分是纯教学玩具——要能承认真实 Score 应基于资源剩余/拓扑/负载动态计算。
- **P6 [Scheduler] ⚠️ 无法盲答 → 反向坐实 L2** 用户明确表示记不清 `Unreserve` 等 gang 代码,因为 SchedulerPlugin 是最早的 demo 且一大半为 AI 所写。**这本身是最关键发现:gang 不是知识盲区,是"代码主权"问题——不是用户写的,无法逐行扛追问。** 泄漏机制(已讲解,作知识补给):① 超时时 Pod 非 Succeeded/Failed,故"只在 S/F 删 map"的 Unreserve 不退账;② `ReadyCount` 只增不减、可被污染;③ 每个拼不齐的 gang 在 map 里留永不删的 `PodGroupContext` → 常驻进程无界累积 → OOM。正解:Unreserve 对任何被拒 Pod 退账 + 组空删 ctx + 超时整组 Deny 置 Failed + TTL 兜底。**对 L2 的影响:倾向"删掉 or 从零自己重写",而非"在 AI 残骸上修补"。**
- **P7 [DDP]** `05_ddp_step_time.py` 里 `fail_before_init` 日志硬编码 `"rank":1`(应打 `env_rank`);checkpoint 只存不恢复(已知边界);脚本里的 `all_reduce` 仅用于求 MAX step time 指标,**真正的梯度同步是 DDP 内部 bucket 在 backward 时做的**——要能区分这两个 all_reduce。

---

## 三、归纳(拷打结论,2026-06-01 收口)

### 核心发现(比任何单条地雷都重要)
三个项目的代码绝大部分由 AI 生成,用户真实掌握停留在"会跑 + 看指标 + 懂契约/行为"层面,**无法逐行扛实现追问**。
- **TrainJob**:相对最好——能讲清状态机自驱动(P3)、finalizer/GC(P4)、Queued 空壳门(L4)等**行为与设计**;实现细节未必全握。
- **SchedulerPlugin**:最早的 demo,gang 部分(L2/P6)完全是 AI 残骸,无代码主权;Filter/Score 略有印象。
- **DDPLab**:**全部** AI 写,只跑过、看过指标、懂启动契约,实现细节答不出(P7 两个 all_reduce 的区分需作为知识补给)。

→ **结论**:当前没有任何一个项目是"能在面试逐行扛追问的自有项目"。出路不是逐条修补地雷,而是**挑一个,从零自己重写到真正拥有**。

### A. 必删的雷(提交/讲述前清掉)
- `gang_scheduling.go`(若走删除路线 / 或重写)
- `isResourceValid()`、`deleteServiceForAttempt()` 死代码(P2)
- `05_ddp_step_time.py` 里 `fail_before_init` 硬编码 `"rank":1` 的 bug(P7)

### B. 只需校准讲法的点(诚实表达边界即可,不必删)
- L1 原生 Job 主线、L3 NodeResourcesFit vs 自写 Filter、P3 状态机自驱动隐患(显式 requeue 才稳)、P4 finalizer 与 GC 边界、P5 NodeLabelScore 是静态教学探针、P7 两个 all_reduce 的区分。
- DDP 仅验证 kind + CPU/Gloo,不声称 GPU/NCCL/RDMA(已有边界文档)。

### C. 值得自己深做的护城河项(从零自写,真正拥有)
- **L2 + L4 合并 = "mini Kueue + Volcano"**:平台侧准入(Queue/Quota,让 `Queued` 名副其实)+ 调度侧 gang(Permit/Reserve/Unreserve 全生命周期 + 超时整组 Deny + 防内存泄漏 P6)。
- 理由:最难被替代、用户已有概念脚手架、正是 AI Infra 平台岗高频考点。

---

## 四、护城河项目模拟面(2026-07 起)— 逐条 gap

> 与前三节不同:护城河项目(mini Kueue + Volcano)是用户**自己逐行写的**,不存在"AI 残骸"问题。这里记的是模拟面里**压力下讲不全/讲错**的点——多为"记不牢""因果讲不闭环",而非"不拥有"。修法通常是"回读自己代码重新锚定",不是补知识。

### M1 — gang 认输的"轮次时钟"只讲了一半(超时清场那半漏了)
- **项目**:SchedulerPlugin / gang
- **现象**(2026-07-14 模拟面):被问"始终凑不齐会不会无限 Waiting"时,能答出 round 自增 + `scheduleMaxLimit` 上限、且"每轮第一个 pod(等待数=0 时)自增"、并发安全靠调度周期串行——**这些都对**。但被追"什么把上一轮 waiting pod 清空、让等待数归 0、下一轮才开得了头"时**卡住、答不出**。
- **承重真相**:清场靠 **Permit 超时**(channel + `time.AfterFunc`);一轮超时未凑齐 → waiting pod 被 Deny → Unreserve 级联拆掉半组 → 等待室清空 → 下个重试 pod 见等待数=0 才开下一轮、round 才 +1。**"第一个 pod 自增"与"超时清场"是同一机制的两半**;没有超时,"等待数=0=新一轮"是假的,round 永卡 1,`scheduleMaxLimit` 永不触发。此超时还承载抢占("熬过 victim 终止 + 凑齐兄弟"需足够轮次)。
- **为什么是雷**:是自己设计的承重逻辑,压力下讲不闭环 → 面试官一追就露"记得结论、忘了机制"。
- **严重度**:中(能自愈,回读代码即可锚回)
- **处理动作**:回读自己 Permit 代码(`AfterFunc` 超时 + Deny + Unreserve 级联),练到能顺畅讲"进等待室→超时→清场→下一轮→round+1→到限认输"整条链。
- **状态**:✅ 已闭(2026-07-21 回读代码后能复述全链)。加分洞察:整组级联 reject 让等待室**原子清空**——错开的超时不会把轮次计数搞出 2→1→0 的中间态,"空室=干净轮次边界"始终成立。

### M2 — "防偷"缺口:答成"抢占没准头",没说后果也没说标准解
- **项目**:SchedulerPlugin / 抢占
- **现象**(2026-07-21 模拟面):被问"victim 死、HPT 未回来的窗口期,什么拦着别的 pod 偷走腾出的 CPU"时,答"没留也无法保证,抢占本就不保证成功"。honest 但**软**,且把真缺陷说成了固有不确定性。
- **承重真相**:后果不是"不保证成功",而是**低优 pod 可在窗口期偷走空间 → 优先级倒挂 + victim 白被驱逐**。标准解 = **`NominatedNodeName`**:抢占时给抢占方设提名节点,调度器资源账把该节点预留给提名者,别的 pod 算余量时看不到 → 挡在外面(kube-scheduler 默认抢占即如此)。用户的 claim(Filter 约束 HPT 到预留节点)只做了"引进来",没做"挡出去"——防偷口子敞着。
- **为什么是雷**:抢占岗高频追问;软答暴露"不知后果、不知业界解法"。
- **严重度**:中(表达/知识层;防偷本身是 design 已知搁置项,不必真做)
- **处理动作**:练成脱口而出"已知缺口 → 后果是优先级倒挂+白驱逐 → 标准解 NominatedNodeName 预留 → 我只引进未挡出"。
- **状态**:待办(练讲法)

### M3 — 对"配额放控制器"这个架构选择无取舍意识
- **项目**:TrainJob / 配额准入
- **现象**(2026-07-21 模拟面):被问"配额准入放哪、为什么、好处代价"时,答"放 QueueController,当初没做取舍、直接选了这种实现,不知道好处代价"。honest,但暴露"对自己的架构选择没有 design-space 意识"。
- **承重真相**:这是 **Kueue 式(控制器/工作负载层准入,调度前)vs Volcano 式(配额在调度器内)**的取舍。
  - **买到**:①分层干净、调度器保持简单(只 gang+抢占);②不创建准入不了的 pod(不堆 Pending 堵调度器);③与调度器解耦。
  - **代价**:①准入≠物理装得下,两层异步会各说各话(job-high 被准入却塞不下→**这正是需要抢占来兜底的原因**);②配额粗、看不到节点级装箱→可能超准入/碎片化;③无跨队列公平/借用/reclaim(静态闸,非 Volcano DRF/reclaim)。
- **为什么是雷**:平台岗爱问"为什么这么分层";答"没做取舍"直接掉价。
- **严重度**:中(需把无意识选择翻成能辩护的取舍)
- **处理动作**:练成答"Kueue 式解耦→调度器简单+不堆无效 pod;代价是两层会不一致、正因此才需要抢占兜底;Volcano 反之(配额进调度器、有节点全视野能 reclaim,但调度器庞大绑引擎)"。锚点:自己跑过的 job-high"被准入却要抢占"。
- **状态**:待办(练讲法)

### 模拟面同时暴露的"表达型"复发问题(非新雷,校准讲法)
- **反复串"谁改谁的状态"**:如把"QueueController 把 TrainJob 置 Starting"(实为 QueueController 只写 `queue.Status.Used`,TrainJobController 自己翻 Starting)、"scheduler 把 preemptedBy 写进 TrainJob"(实为写 victim **PodGroup**)。**scheduler 只碰 PodGroup、controller 才碰 TrainJob phase;PodGroup 是两子系统契约缝**——需练到张口分清。
- **反复把 gang 屏障讲没**:"所有 pod Running 后 job Running"跳过了 Permit 凑齐 Allow→bind 这道招牌屏障。
- **开场把项目缩成"gang 调度器"**:漏掉抢占 + 两层配额;开场应先甩"mini Kueue + Volcano"骨架 + 主动抛设计张力。
- **"独立实现调度器"过度声称**:须主动澄清"扩展 kube-scheduler 框架、非自研引擎"。
