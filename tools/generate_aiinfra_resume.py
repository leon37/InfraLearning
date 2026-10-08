#!/usr/bin/env python3
"""Generate the AI Infra version of Li Tao's resume as a PDF."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "2026-resume-li-tao-aiinfra.pdf"


def text(value: str) -> str:
    return escape(value).replace("\n", "<br/>")


def register_fonts() -> None:
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    common = {
        "fontName": "STSong-Light",
        "wordWrap": "CJK",
        "splitLongWords": True,
    }
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Normal"],
            fontName="STSong-Light",
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#111827"),
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            **common,
            fontSize=9.5,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#374151"),
        ),
        "section": ParagraphStyle(
            "section",
            parent=base["Normal"],
            **common,
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=7,
            spaceAfter=3,
        ),
        "normal": ParagraphStyle(
            "normal",
            parent=base["Normal"],
            **common,
            fontSize=8.8,
            leading=11.8,
            alignment=TA_LEFT,
            textColor=colors.HexColor("#111827"),
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["Normal"],
            **common,
            fontSize=8.2,
            leading=10.8,
            textColor=colors.HexColor("#374151"),
        ),
        "bullet": ParagraphStyle(
            "bullet",
            parent=base["Normal"],
            **common,
            fontSize=8.7,
            leading=11.6,
            leftIndent=9,
            bulletIndent=0,
            textColor=colors.HexColor("#111827"),
        ),
        "muted": ParagraphStyle(
            "muted",
            parent=base["Normal"],
            **common,
            fontSize=8,
            leading=10.5,
            textColor=colors.HexColor("#4b5563"),
        ),
    }


def p(value: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text(value), style)


def section(flow: list, title: str, s: dict[str, ParagraphStyle]) -> None:
    flow.append(p(title, s["section"]))
    flow.append(
        HRFlowable(
            width="100%",
            thickness=0.6,
            color=colors.HexColor("#cbd5e1"),
            spaceBefore=0,
            spaceAfter=4,
        )
    )


def bullets(flow: list, values: list[str], s: dict[str, ParagraphStyle]) -> None:
    for value in values:
        flow.append(Paragraph(text(value), s["bullet"], bulletText="-"))


def two_col_header(left: str, right: str, s: dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [[p(left, s["normal"]), p(right, s["small"])]],
        colWidths=[124 * mm, 46 * mm],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    return table


def add_footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("STSong-Light", 7.2)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.drawRightString(200 * mm, 9 * mm, f"{doc.page}")
    canvas.restoreState()


def build() -> None:
    register_fonts()
    s = styles()
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=13 * mm,
        bottomMargin=12 * mm,
        title="李涛 - AI Infra 简历",
        author="李涛",
        subject="AI Infra / Kubernetes / 训练平台简历",
    )

    flow = []
    flow.append(p("李涛", s["title"]))
    flow.append(
        p(
            "求职意向：AI Infra / 机器学习平台 / 训练平台控制面 / Kubernetes 后端研发",
            s["subtitle"],
        )
    )
    flow.append(
        p(
            "成都｜29 岁｜182 0014 3014｜13368447@qq.com",
            s["subtitle"],
        )
    )

    section(flow, "个人总结", s)
    bullets(
        flow,
        [
            "4 年 Golang 后端研发经验，长期负责高并发业务逻辑、实时状态同步、全服活动、排行榜与批量结算等服务端模块，具备稳定性、并发模型和数据一致性工程经验。",
            "近期主线转向 AI Infra 与 Kubernetes 控制面，完成从 Docker / K8s 底层、Scheduler Framework、TrainJob Controller 到 PyTorch DDP worker 的端到端学习与实验闭环。",
            "已实现本地 kind 环境下的 AI 训练平台最小 demo：TrainJob CRD 展开 DDP worker，自定义 scheduler 接管调度，worker 通过 Gloo 完成多 Pod DDP，rank0 写 checkpoint 到 PVC，controller 聚合任务状态。",
            "定位诚实：当前项目验证的是 AI workload 控制面、调度接入和 DDP 启动契约，不包装成真实 GPU/NCCL/RDMA 性能优化经验；下一步可沿 device plugin、CUDA tensor、NCCL、DCGM 指标继续补强。",
        ],
        s,
    )

    section(flow, "专业技能", s)
    skills = [
        ["语言与工程", "Golang 熟练，理解 GMP 调度与 CSP 并发模型；Python 可用于 PyTorch/DDP 实验与脚本；C 可阅读底层代码。"],
        ["Kubernetes", "理解 Pod / Service / PVC / PV / StorageClass / Node / Events；熟悉 CRD、controller-runtime、Reconcile、OwnerReference、Informer cache。"],
        ["调度与资源", "掌握 schedulerName、自定义 scheduler profile、Filter/Score 插件边界、requests 与 Node.status.allocatable、extended resource、scheduler cache 基本语义。"],
        ["AI Infra", "理解 DDP rank/world_size/rendezvous/process group、Gloo 与 NCCL 边界、checkpoint 持久化与恢复限制；了解 NVIDIA device plugin、DCGM/Prometheus 的接入位置。"],
        ["存储与中间件", "熟悉 Redis、MySQL、MongoDB；有排行榜、缓存策略、分布式锁、批处理结算和监控告警模块经验。"],
        ["系统基础", "熟悉 Linux 常用排障命令、Docker 容器化、Namespace/cgroup 基础链路；熟悉 TCP/IP、HTTP、WebSocket。"],
    ]
    table = Table(
        [[p(k, s["small"]), p(v, s["normal"])] for k, v in skills],
        colWidths=[28 * mm, 142 * mm],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#0f172a")),
            ]
        )
    )
    flow.append(table)

    section(flow, "AI Infra 项目经历", s)
    flow.append(
        two_col_header(
            "基于 Kubernetes 的分布式训练任务控制面与调度扩展",
            "个人项目｜2026.03 - 2026.05",
            s,
        )
    )
    bullets(
        flow,
        [
            "项目目标：构建一个训练平台最小闭环，把用户提交的 TrainJob 转换为多 Pod DDP worker，并串联 controller、scheduler plugin、DDP worker、checkpoint PVC 与任务状态聚合。",
            "TrainJob Operator：定义 TrainJob CRD，controller 根据 worldSize 展开 worker Pod，注入 MASTER_ADDR、MASTER_PORT、RANK、WORLD_SIZE、LOCAL_RANK；通过 rank0 ClusterIP Service 提供稳定 rendezvous 入口。",
            "状态与重试：使用 attempt label 隔离不同重试轮次，避免旧 attempt rank0 被 Service endpoints 误选；实现 worker Pod 状态聚合、Succeeded/Failed/Retrying 流转，并明确当前不是真正 gang scheduling。",
            "Scheduler Plugin：worker Pod 通过 schedulerName=my-custom-scheduler 交给自定义 scheduler；资源过滤使用 Kubernetes 原生 NodeResourcesFit，对比 Pod.requests 与 Node.status.allocatable；自定义 NodeLabelScore 用于节点偏好打分。",
            "资源模型：从 label-only 模拟切换到 extended resource 路线，使用 aiinfra.leon.com/gpu-capacity 模拟 GPU 容量账本；能解释真实 GPU 应由 device plugin 经 kubelet 上报到 Node allocatable。",
            "DDP worker：基于 PyTorch DDP 脚本验证 kind + Pod 网络 + Gloo backend 下的多 rank 启动、process group 初始化、step 指标输出和慢 rank 影响；rank0 将 latest.pt 写入 PVC。",
            "实操验收：从清理状态重新跑通 TrainJob -> Scheduler -> DDP -> checkpoint -> Succeeded；主动制造 extended resource 不足，能从 FailedScheduling / Insufficient 判断 scheduler Filter 阶段失败。",
        ],
        s,
    )
    flow.append(
        p(
            "技术栈：Go、controller-runtime、Kubernetes Scheduler Framework、Kind、Docker、PyTorch DDP、Gloo、PVC/PV、Redis/MySQL 基础工程经验",
            s["muted"],
        )
    )

    flow.append(PageBreak())

    section(flow, "工作经历", s)
    flow.append(two_col_header("动力部落科技有限公司｜后端开发工程师", "2022.10 - 至今", s))
    bullets(
        flow,
        [
            "负责游戏服务器核心业务逻辑、高并发模块与全服活动系统开发，主要使用 Golang 完成服务端逻辑、状态同步、数据结构和结算链路设计。",
            "家族系统：基于 Goroutine + Channel 的串行化处理模型重构核心逻辑，将同一业务实体的操作收敛到单执行流，降低共享状态并发读写和锁竞争风险。",
            "全服活动与排行：基于 Redis ZSet 等结构实现全服排行、实时百分比排名和活动进度上报，处理多进程并发写入下的数据一致性问题。",
            "批量结算：针对活动结束时的结算洪峰设计分批处理机制，降低瞬时写入压力，保障奖励发放准确性和服务稳定性。",
            "多人交互预研：对多人同屏状态同步与帧同步方案进行对比和原型验证，积累实时系统、长连接和状态一致性设计经验。",
        ],
        s,
    )
    flow.append(Spacer(1, 3))
    flow.append(two_col_header("泛联智存科技有限公司｜后端开发工程师", "2022.04 - 2022.10", s))
    bullets(
        flow,
        [
            "开发统一监控告警模块，对接硬件与业务指标，支持异常及时通知与故障定位。",
            "负责双节点数据库同步工具开发与维护，保障主备切换时的数据完整性。",
        ],
        s,
    )
    flow.append(Spacer(1, 3))
    flow.append(two_col_header("晓多科技｜后端开发工程师", "2021.07 - 2022.04", s))
    bullets(
        flow,
        [
            "负责业务系统与飞书、纷享销客等第三方平台的 API 对接，完成接口联调、数据映射和异常处理。",
        ],
        s,
    )

    section(flow, "科研与底层项目", s)
    flow.append(two_col_header("基于 ETSI 欧标的车联网通信协议栈开发", "硕士核心课题", s))
    bullets(
        flow,
        [
            "基于 ETSI ITS 标准体系研发适配 IPv6 的车联网网络层协议栈，理解 V2X、GeoNetworking、IPv6 封装与透明传输链路。",
            "在 GeoNetworking 协议基础上开发 GN6ASL 适配层，并结合 IEEE 1609.4 处理底层多信道切换逻辑。",
            "搭建基于 OBU 车载单元的真机测试环境，通过串口发包、抓包分析验证协议栈连通性与数据包投递情况。",
        ],
        s,
    )
    flow.append(Spacer(1, 2))
    flow.append(two_col_header("InfraLearning：Linux / Docker / Kubernetes 底层学习仓库", "个人长期项目", s))
    bullets(
        flow,
        [
            "按 kubectl -> apiserver -> scheduler -> kubelet -> containerd/runc -> CNI / kube-proxy -> Linux 内核的链路拆解 Kubernetes 控制面和容器运行时。",
            "完成 Namespace、cgroup、Docker 运行时、Kubernetes 对象模型、Informer/Reconcile、Scheduler cache、PVC/PV 等主题的实验记录与复盘文档。",
        ],
        s,
    )

    section(flow, "教育背景与证书", s)
    education = [
        ["硕士", "电子科技大学 985｜电子通信工程｜2017 - 2021"],
        ["本科", "电子科技大学 985｜机械设计制造及其自动化｜2013 - 2017"],
        ["证书", "软考·系统架构设计师（高级）；英语 CET-6"],
    ]
    edu_table = Table(
        [[p(k, s["small"]), p(v, s["normal"])] for k, v in education],
        colWidths=[22 * mm, 148 * mm],
        hAlign="LEFT",
    )
    edu_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    flow.append(edu_table)

    doc.build(flow, onFirstPage=add_footer, onLaterPages=add_footer)


if __name__ == "__main__":
    build()
    print(OUT)
