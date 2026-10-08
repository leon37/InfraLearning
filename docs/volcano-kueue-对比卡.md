# Volcano / Kueue 对比卡(挂在"我的项目"上记)

> 用途:面试"你这套跟 Volcano/Kueue 比怎么样"的速答卡。**不是学 Volcano/Kueue,是记住"我的决定 vs 它们的决定 + 为什么"。** 每条都锚在我自己写过的东西上,所以记得住。
> 读文档的唯一姿势:带着某一行的"我这么做了,它呢?"去查那一个点,查完补进这张卡。别再从头通读。

## 一句话总纲

我的项目 = **mini Kueue(配额准入,控制器侧、Kueue 风格)+ mini Volcano(gang/抢占,调度器侧、Volcano 风格)**。所以拆成两半跟不同的系统比。

## 对比表

| 维度 | 我的项目 | Volcano / Kueue | 一句话面试话术 |
|---|---|---|---|
| **调度器形态** | kube-scheduler **框架 + 插件**,打包成 my-custom-scheduler 二进制;逐 pod 串行调度周期 | Volcano 是**自研调度引擎**,Session+Action 模型,一次批量看一堆 PodGroup | "我是扩展 kube-scheduler 框架、没另写调度引擎;Volcano 是独立引擎" |
| **gang 机制** | **Permit 等待室**:先到的 pod 扣住,凑齐 minMember 再整组放行 | Volcano 在 **allocate action 里一次性 all-or-nothing** 判整组 | "逐 pod 进框架决定了我只能用等待室凑;它批量调度所以能当场原子判" |
| **两层对象切分** | TrainJob(工作负载)+ PodGroup(调度器 gang 契约) | vcjob + PodGroup,**同一套切分** | "我独立重新发现了 Volcano 的分层;我的 TrainJob 是 DDP 专用版 vcjob" |
| **配额/队列住在哪** | **控制器侧**,队列装 **TrainJob**(按 jobName),准入在调度之前(Queued→Starting) | Volcano:**调度器内**,队列装 **PodGroup**,配额在调度周期里算。Kueue:**控制器/工作负载侧**(跟我一样) | "我的配额是 Kueue 式的工作负载层准入,把准入和物理调度分两层;Volcano 把配额揉进调度器" |
| **配额模型** | **单档硬顶**:resourceQuota + Used,用满即拒,静态 | Volcano Queue:**guarantee / deserved / capability 三档弹性** + 借用 + reclaim。Kueue:nominalQuota + borrowingLimit/lendingLimit + cohort | "我是静态单档硬顶,没有公平线、没有跨队列借用/回收;它们是三档弹性配额" |
| **抢占范围** | **队列内按优先级**、gang-aware | Volcano:**preempt(队列内优先级)+ reclaim(跨队列收回超借的 deserved)** | "我做了队列内 gang 抢占,没有跨队列 reclaim" |
| **资源维度** | **只算 CPU** | 多资源(DRF 等) | "我目前单 CPU 资源,上 GPU/多资源要补多维公平" |

## 关键概念小抄(被追问时用)

- **guarantee / deserved / capability**:锁死地板(空着也留、秒拿)/ 公平线(闲了外借、要用靠 reclaim 抢回、护住不被压下)/ 硬天花板。`guarantee ≤ deserved ≤ capability`。
- **借空闲 vs reclaim**:借 = 用别人空着的份额,不踢人、不牢(会被原主收回);reclaim = 把占我 deserved 的人踢走、拿回自己的,踢人、踏实。铁律:**超过自己 deserved 只能靠借空闲,永远不能靠踢人**。
- **PodGroup 的意义**:应用控制器 ↔ 通用调度器 之间的**窄腰契约**;调度器只认 PodGroup,不认 vcjob/TrainJob,所以任何工作负载建个 PodGroup 就能白嫖 gang。
