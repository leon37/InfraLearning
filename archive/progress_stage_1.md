# 学习进度 - 第一阶段 (容器与 K8s 基础)

## 1. 12 周阶段 Checklist

| 周次 | 主题 | 状态 | 备注 |
| --- | --- | --- | --- |
| 第 1 周 | Docker 基础命令与容器生命周期 | 已完成 | 已完成 image / container / process / writable layer 的第一轮认知验收 |
| 第 2 周 | Dockerfile、镜像分层与 OverlayFS 初识 | 已完成 | 已完成最小 Dockerfile、缓存链、GraphDriver 与 OverlayFS 存储痕迹验收 |
| 第 3 周 | 容器网络与端口映射 | 已完成 | 已完成 bridge、容器名解析、docker-proxy 与宿主机访问路径验收 |
| 第 4 周 | Volume、Bind Mount 与挂载视角 | 已完成 | 已完成 bind mount、volume 与挂载路径生效范围验收 |
| 第 5 周 | Namespace 深入与最小容器雏形 | 已完成 | 已完成 UTS、PID、Mount 三条骨架与最小容器初始化链收口 |
| 第 6 周 | cgroup、capabilities 与容器安全边界 | 已完成 | 已完成 cgroup v2、memory.max 与 capabilities 边界验收 |
| 第 7 周 | Kubernetes 核心对象入门 | 已完成 | 已完成 Pod、Deployment、Service 及其关系的第一轮验收 |
| 第 8 周 | ConfigMap、Secret、Volume 与声明式配置 | 已完成 | 已完成 ConfigMap、Secret 与注入方式差异验收 |
| 第 9 周 | 调度、资源请求限制与探针 | 已完成 | 已完成 Pending / OOMKilled / readiness / liveness 四类现象边界验收 |
| 第 10 周 | Kubernetes 网络模型 | 已完成 | 已完成 CoreDNS / kube-proxy / CNI(kindnet) / Service / Endpoints 职责边界与单节点网络链路验收 |
| 第 11 周 | Kubelet、CRI、containerd、runc 调用链 | 已完成 | 已完成 `kubectl apply` 到 apiserver / etcd / scheduler / kubelet / containerd / shim / runc / pause sandbox 的最小链路验收 |
| 第 12 周 | 控制面与综合复盘 | 已完成 | 已完成从 `kubectl apply` 到 sandbox / 容器 / 网络 / Service 转发 / 内核机制落地的总链路复盘 |

## 2. 实验记录 (归档)

(包含 2026-03-13 至 2026-03-27 的所有容器基础与 K8s 基础实验记录，已从主文件移除)
