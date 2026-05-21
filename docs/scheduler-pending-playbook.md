# Scheduler Pending 排障剧本

## 1. 文档定位

本文记录 `AIInfraSchedulerPlugin` 相关 Pending 和调度结果不符合预期时的排障路径。

目标：

```text
能区分 custom scheduler 未接管、Filter 失败、scheduler 启动失败、Score 不符合预期、Pod 已绑定后的 kubelet 阶段问题。
```

本文不追求覆盖 Kubernetes 所有 Pending 原因，只覆盖当前三个项目最容易遇到的场景。

## 2. 先看三个字段

排查 worker Pod Pending 时，先看：

```bash
kubectl get pod <pod-name> -o yaml
```

重点字段：

```text
spec.schedulerName
spec.nodeName
status.phase
```

含义：

| 字段 | 判断 |
| --- | --- |
| `spec.schedulerName=my-custom-scheduler` | 这个 Pod 应由 custom scheduler 接管 |
| `spec.nodeName` 为空 | Pod 尚未绑定到 Node |
| `spec.nodeName` 是具体 Node | scheduler 已完成 bind，后续问题多半在 kubelet/container 阶段 |

然后看：

```bash
kubectl describe pod <pod-name>
```

重点区域：

```text
Events
Reason
Message
```

## 3. 场景一：Events 长时间为空

现象：

```text
Pod.status.phase = Pending
Pod.spec.schedulerName = my-custom-scheduler
Pod.spec.nodeName = ""
describe pod 里 Events 为空，或者长时间没有 FailedScheduling
```

判断：

```text
优先怀疑 custom scheduler 没有接管。
```

原因：

```text
默认 kube-scheduler 不会处理 schedulerName=my-custom-scheduler 的 Pod。
如果负责 my-custom-scheduler 的 scheduler 进程没启动、启动失败、profile 名不匹配，Pod 就可能一直没人调度。
```

下一步：

```text
检查 custom scheduler 进程是否还在。
检查 custom scheduler 日志。
检查 scheduler config 里的 profile schedulerName。
检查 Pod.spec.schedulerName 是否和 profile 名一致。
```

## 4. 场景二：FailedScheduling + Insufficient

现象：

```text
Pod.status.phase = Pending
Pod.spec.nodeName = ""

Events:
  Warning  FailedScheduling   0/2 nodes are available: 2 Insufficient aiinfra.leon.com/gpu-capacity.
```

判断：

```text
custom scheduler 已经接管并处理过这个 Pod。
这是 Filter 阶段资源判断失败。
```

下一步看 Pod requests：

```bash
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[0].resources.requests}{"\n"}'
```

再看 Node allocatable：

```bash
kubectl get node -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.allocatable.aiinfra\.leon\.com/gpu-capacity}{"\n"}{end}'
```

判定：

```text
如果所有 Node 的剩余可用量都小于 Pod requests，调度失败是预期结果。
```

注意：

```text
Node.status.allocatable 不是实时剩余量。
scheduler 还会结合该 Node 上已经分配的 Pod requests 计算剩余可用量。
```

## 5. 场景三：scheduler 启动时插件初始化失败

现象：

```text
custom scheduler 进程启动后立刻退出。
```

日志示例：

```text
plugin "NodeLabelScore" does not extend ScorePlugin plugin
```

判断：

```text
这不是某个 Pod 调度失败。
这是 scheduler 启动加载 profile/plugin 时失败。
```

Pod 表现：

```text
schedulerName=my-custom-scheduler 的 worker Pod 会保持 Pending。
```

优先检查：

```text
插件是否真正实现了配置中声明的扩展点接口。
当前 Kubernetes 版本下插件接口签名是否匹配。
插件工厂函数返回值是否是正确的插件对象。
scheduler config 中插件名是否和注册名一致。
```

本项目曾遇到过的典型问题：

```text
Kubernetes v1.29 的 ScorePlugin 接口是 Score(ctx, state, pod, nodeName string)。
如果插件实现的是错误版本的接口，编译可能过，但 scheduler profile 初始化会失败。
```

## 6. 场景四：Pod 已绑定，但不是期望节点

现象：

```text
Pod.spec.nodeName = kind-worker2
Pod 已经 Running 或 Succeeded
但它没有落到你期望的最高分 Node
```

判断：

```text
这不是 Filter 失败。
这不是 Pending 问题。
这是 Score 排序、权重或输入数据问题。
```

优先检查 Node label：

```bash
kubectl get node --show-labels
```

重点看当前插件依赖的 label，例如：

```text
node_topological_hint
```

再检查 scheduler config：

```text
profiles[].plugins.score.enabled
profiles[].plugins.score.enabled[].weight
profiles[].pluginConfig
```

再看 custom scheduler 日志：

```text
每个 Node 是否参与打分。
每个 Node 的原始分或最终分是否符合预期。
是否还有其他 Score 插件或权重影响最终结果。
```

## 7. NodeLabelScore 的边界

当前 `NodeLabelScore` 是教学版/实验版插件。

它的链路是：

```text
Node label
-> 插件读取 label
-> 转成 score
-> 返回给 scheduler
```

它适合验证：

```text
ScorePlugin 如何接入 scheduler framework。
scheduler 如何调用 Score。
不同 Node 得分如何影响最终绑定结果。
```

但这不是通用做法。

一般情况下，ScorePlugin 不应该假设所有分数都预先写在 Node label 里。真实调度中，ScorePlugin 更可能根据调度周期中的动态信息计算分数，例如：

```text
Node 当前剩余资源
Pod requests
Pod 和已有 Pod 的亲和/反亲和关系
拓扑分布
镜像本地性
节点负载
设备拓扑
队列或任务优先级
```

面试表达：

```text
我当前的 NodeLabelScore 是为了验证 ScorePlugin 接入链路，用 label 作为简单输入。
它不代表生产调度器都把分数放在 Node label 里。
真实场景里，ScorePlugin 更可能基于资源剩余量、拓扑、亲和性、负载指标或设备信息动态计算节点分数。
```

## 8. 固定判断顺序

遇到 worker Pod Pending：

```text
1. 看 spec.schedulerName
   判断应该由哪个 scheduler 处理。

2. 看 spec.nodeName
   为空表示尚未 bind；有值表示 scheduler 已完成绑定。

3. 看 describe pod Events
   没有 FailedScheduling：优先怀疑 scheduler 没接管或没运行。
   有 FailedScheduling + Insufficient：Filter 阶段资源失败。
   有 Scheduled 后 image/pull/mount 失败：scheduler 已完成，转向 kubelet/container 阶段。

4. 如果是资源失败
   查 Pod requests、Node allocatable、已有 Pod requests。

5. 如果是绑定结果不符合预期
   查 Score 插件输入、权重、日志，而不是继续查 Filter。
```

## 9. 面试回答底稿

如果被问：

```text
worker Pod 一直 Pending，你怎么判断是 scheduler 没接管，还是资源不足？
```

可以回答：

```text
我会先看 Pod.spec.schedulerName 和 spec.nodeName。
如果 schedulerName 是 my-custom-scheduler，nodeName 为空，并且 describe pod 长时间没有 FailedScheduling 事件，我会优先怀疑 custom scheduler 没启动、没接管或 profile 名不匹配。默认 kube-scheduler 不会处理这个 schedulerName 的 Pod。

如果 describe pod 已经有 FailedScheduling，并且 Message 是 Insufficient 某个 extended resource，说明 scheduler 已经接管并执行 Filter，只是资源账本判断不满足。下一步看 Pod resources.requests、Node.status.allocatable，以及 scheduler cache 中该节点已有 Pod requests。
```

如果被问：

```text
Pod 调度成功了，但不是你期望的节点，怎么办？
```

可以回答：

```text
这通常不是 Filter 问题，而是 Score 排序、权重或输入数据问题。我会看 NodeLabelScore 依赖的 Node label 是否正确，看 scheduler config 中 Score 插件和权重是否正确，再看 scheduler 日志中每个 Node 的得分。

同时我会说明，我当前的 NodeLabelScore 是教学版，用 Node label 作为简单打分输入。真实平台里 ScorePlugin 通常会结合资源剩余、拓扑、亲和性、负载或设备信息动态计算分数。
```

