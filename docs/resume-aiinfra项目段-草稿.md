# 简历 · AI Infra 项目段(重写草稿,替换旧项目段)

> 用途:旧简历项目段停在护城河项目之前,还写着"不是真正 gang scheduling"。这份把护城河(mini Kueue + Volcano:gang + 配额 + gang 感知抢占)作为招牌重写,DDP/checkpoint 降为支撑。**这是初稿,你逐条挑刺,我们再改。**

---

## 基于 Kubernetes 的分布式训练平台:自研 gang 调度、配额准入与 gang 感知抢占
个人项目｜2026.03 - 至今

- **项目目标**:自研一个"mini Kueue + Volcano"——平台侧配额准入 + 调度侧 gang 调度与 gang 感知抢占,把用户提交的 TrainJob 端到端跑成多 Pod DDP 训练,**核心机制不依赖 Volcano/Kueue 等现成组件,逐行自写**。

- **Gang 调度(自研,非现成组件)**:在 kube-scheduler framework 上写插件,用 **Permit 等待室**实现整组 all-or-nothing——先到的 worker 挂起等待,凑齐 minMember 才整组放行;基于 **PodGroup 持久化的 round 计数 + Permit 超时 + Unreserve 级联**,实现"凑不齐则整组认输"的有界重试,规避 partial-scheduling 死锁与资源泄漏(利用调度周期串行性保证 round 自增无锁安全)。

- **配额准入(Kueue 式,控制器侧)**:自定义 **Queue CRD**,QueueController 按优先级做配额准入,把"准入"与"物理调度"拆成两层——控制器准入通过才展开 Pod,避免创建准入不了的 Pod 堆积调度器。

- **Gang 感知抢占 + 认领(项目最难点)**:PostFilter 识别低优 victim gang、按"腾空后每节点可容纳的抢占方 worker 数(含已等待成员基线)"生成抢占计划持久化到 PodGroup;经 **preemptedBy 信号 + 控制器协作驱逐**(不从调度器直接删 Pod,避免控制器重建活锁);抢占方下一调度周期在 **PreFilter 读计划入 CycleState、Filter 按计划把 worker 钉到预留节点**;victim 经 **字段索引 + ownerRef 唤醒**、依抢占方状态(Running/Failed/删除)回流 Queued。

- **TrainJob Operator + DDP**:TrainJob CRD 按 worldSize 展开 worker,注入 RANK/WORLD_SIZE/MASTER_ADDR,rank0 ClusterIP Service 提供稳定 rendezvous 入口;PyTorch DDP(Gloo)验证多 rank process group 初始化、step 指标、rank0 写 checkpoint 到 PVC;attempt label 隔离重试轮次。

- **实操验收**:端到端复现"高优 gang 抢占低优 gang → victim 拆除并置 Preempted → 抢占方按计划精确落位每节点、整组 Running → victim 自动释放回流 Queued"完整闭环(kind,2 worker)。

- **定位诚实**:当前抢占为 **CPU 单资源、单 victim gang、无跨队列 reclaim、防第三方偷占未做**;环境为 **kind + CPU/Gloo,非真 GPU/NCCL/RDMA**。下一步:多资源/DRF 公平、NominatedNodeName 预留防偷、GPU device plugin 上报路径。

**技术栈**:Go、controller-runtime、Kubernetes Scheduler Framework(PreFilter/Filter/PostFilter/Reserve/Permit)、CRD/Informer 字段索引、Kind、PyTorch DDP/Gloo、PVC。

---

## 待你确认的取舍
1. **一段还是两段**:建议合成**一段**(护城河是老 demo 长出来的同一套代码,不是两个项目)。若想让老 demo 的调度接入(NodeResourcesFit/NodeLabelScore/extended resource)也留痕,可作为一条支撑 bullet,但别喧宾夺主。
2. **时间**:旧简历写 2026.03-05,建议改成 **2026.03 - 至今**(项目还在演进)。
3. **个人总结**同步改一句:把"完成端到端学习与实验闭环"升级成"**自研 gang 调度 + 配额准入 + gang 感知抢占**",别再用"学习/实验"这种降格词。
