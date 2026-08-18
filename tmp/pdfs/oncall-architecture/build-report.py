from __future__ import annotations

from datetime import date
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
OUTPUT = PROJECT_ROOT / "output" / "pdf" / "super-biz-agent-architecture-report.pdf"

PAGE_PORTRAIT = A4
PAGE_LANDSCAPE = landscape(A4)
MARGIN_X = 18 * mm
MARGIN_TOP = 18 * mm
MARGIN_BOTTOM = 17 * mm

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2F6FA3")
PALE_BLUE = colors.HexColor("#E8F1FB")
PALE_GREEN = colors.HexColor("#EEF7EF")
PALE_ORANGE = colors.HexColor("#FFF7E8")
LINE = colors.HexColor("#B5C1CC")
TEXT = colors.HexColor("#263746")
MUTED = colors.HexColor("#5E6D79")


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("CJK", r"C:\Windows\Fonts\msyh.ttc"))
    pdfmetrics.registerFont(TTFont("CJK-Bold", r"C:\Windows\Fonts\msyhbd.ttc"))
    pdfmetrics.registerFontFamily(
        "CJK",
        normal="CJK",
        bold="CJK-Bold",
        italic="CJK",
        boldItalic="CJK-Bold",
    )


register_fonts()


class ArchitectureDocTemplate(BaseDocTemplate):
    def __init__(self, filename: str) -> None:
        super().__init__(
            filename,
            pagesize=PAGE_PORTRAIT,
            leftMargin=MARGIN_X,
            rightMargin=MARGIN_X,
            topMargin=MARGIN_TOP,
            bottomMargin=MARGIN_BOTTOM,
            title="SuperBizAgent Python 项目整体架构说明",
            author="Codex",
            subject="单一 Durable Incident Runtime、双诊断策略与共享治理架构",
        )

        portrait_frame = Frame(
            MARGIN_X,
            MARGIN_BOTTOM,
            PAGE_PORTRAIT[0] - 2 * MARGIN_X,
            PAGE_PORTRAIT[1] - MARGIN_TOP - MARGIN_BOTTOM,
            id="portrait-frame",
        )
        landscape_frame = Frame(
            MARGIN_X,
            MARGIN_BOTTOM,
            PAGE_LANDSCAPE[0] - 2 * MARGIN_X,
            PAGE_LANDSCAPE[1] - MARGIN_TOP - MARGIN_BOTTOM,
            id="landscape-frame",
        )

        self.addPageTemplates(
            [
                PageTemplate(
                    id="portrait",
                    pagesize=PAGE_PORTRAIT,
                    frames=[portrait_frame],
                    onPage=self._draw_page,
                ),
                PageTemplate(
                    id="landscape",
                    pagesize=PAGE_LANDSCAPE,
                    frames=[landscape_frame],
                    onPage=self._draw_page,
                ),
            ]
        )

    @staticmethod
    def _draw_page(canvas, doc) -> None:
        width, height = canvas._pagesize
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.4)
        canvas.line(MARGIN_X, 13 * mm, width - MARGIN_X, 13 * mm)
        canvas.setFont("CJK", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN_X, 8 * mm, "SuperBizAgent Python 项目整体架构说明")
        canvas.drawRightString(width - MARGIN_X, 8 * mm, f"第 {doc.page} 页")
        canvas.restoreState()


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="CoverTitleCJK",
        fontName="CJK-Bold",
        fontSize=28,
        leading=40,
        textColor=NAVY,
        alignment=TA_CENTER,
        spaceAfter=14 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverSubCJK",
        fontName="CJK",
        fontSize=14,
        leading=23,
        textColor=MUTED,
        alignment=TA_CENTER,
    )
)
styles.add(
    ParagraphStyle(
        name="H1CJK",
        fontName="CJK-Bold",
        fontSize=19,
        leading=28,
        textColor=NAVY,
        spaceBefore=5 * mm,
        spaceAfter=4 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="H2CJK",
        fontName="CJK-Bold",
        fontSize=14,
        leading=21,
        textColor=BLUE,
        spaceBefore=4 * mm,
        spaceAfter=2.5 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="BodyCJK",
        fontName="CJK",
        fontSize=10.5,
        leading=18,
        textColor=TEXT,
        alignment=TA_LEFT,
        spaceAfter=2.5 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="SmallCJK",
        fontName="CJK",
        fontSize=8.7,
        leading=14,
        textColor=MUTED,
        spaceAfter=1.5 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="BulletCJK",
        fontName="CJK",
        fontSize=10.2,
        leading=17,
        leftIndent=6 * mm,
        firstLineIndent=-4 * mm,
        bulletIndent=1 * mm,
        textColor=TEXT,
        spaceAfter=1.5 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="CalloutCJK",
        fontName="CJK",
        fontSize=10.5,
        leading=18,
        textColor=NAVY,
        backColor=PALE_BLUE,
        borderColor=colors.HexColor("#8FB1D1"),
        borderWidth=0.6,
        borderPadding=8,
        spaceBefore=2 * mm,
        spaceAfter=4 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="TableHeadCJK",
        fontName="CJK-Bold",
        fontSize=8.5,
        leading=12,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
)
styles.add(
    ParagraphStyle(
        name="TableCellCJK",
        fontName="CJK",
        fontSize=7.7,
        leading=11.5,
        textColor=TEXT,
    )
)


def para(text: str, style: str = "BodyCJK") -> Paragraph:
    return Paragraph(text, styles[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"• {text}", styles["BulletCJK"])


def diagram_image(filename: str, max_width: float, max_height: float) -> Image:
    path = HERE / filename
    with PILImage.open(path) as image:
        width, height = image.size
    scale = min(max_width / width, max_height / height)
    return Image(str(path), width=width * scale, height=height * scale)


def diagram_page(
    story: list,
    *,
    template: str,
    title: str,
    filename: str,
    caption: str,
) -> None:
    story.extend([NextPageTemplate(template), PageBreak()])
    if template == "landscape":
        max_width = PAGE_LANDSCAPE[0] - 42 * mm
        max_height = PAGE_LANDSCAPE[1] - 80 * mm
    else:
        max_width = PAGE_PORTRAIT[0] - 36 * mm
        max_height = PAGE_PORTRAIT[1] - 90 * mm
    story.append(
        KeepTogether(
            [
                para(title, "H1CJK"),
                diagram_image(filename, max_width, max_height),
                Spacer(1, 2.5 * mm),
                para(caption, "SmallCJK"),
            ]
        )
    )


def build_story() -> list:
    story: list = []

    # Cover
    story.extend(
        [
            Spacer(1, 35 * mm),
            para("SuperBizAgent Python 项目", "CoverTitleCJK"),
            para("整体架构、信息流与模块职责说明", "CoverTitleCJK"),
            Spacer(1, 8 * mm),
            para("单一 Durable Incident Runtime 完成态架构", "CoverSubCJK"),
            Spacer(1, 28 * mm),
            Table(
                [
                    [para("文档目的", "SmallCJK"), para("帮助新成员由浅入深理解系统边界、主流程、状态和依赖", "BodyCJK")],
                    [para("分析范围", "SmallCJK"), para("应用入口、前后端、工作流、数据层、外部系统、测试与运行方式", "BodyCJK")],
                    [para("生成日期", "SmallCJK"), para(date.today().isoformat(), "BodyCJK")],
                    [para("项目目录", "SmallCJK"), para(str(PROJECT_ROOT), "SmallCJK")],
                ],
                colWidths=[32 * mm, 120 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (0, -1), PALE_BLUE),
                        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                        ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            ),
        ]
    )

    # Positioning and reading guide
    story.extend([PageBreak(), para("一、项目定位", "H1CJK")])
    story.append(
        para(
            "这是一个面向值班运维人员的 AI 运维助手，主要解决告警出现以后，如何查资料、收集证据、分析根因并形成处置建议的问题。"
        )
    )
    story.append(
        para(
            "系统提供两类入口：普通 AI 对话和知识问答保持独立；故障诊断统一进入 Durable Incident Runtime，由 Incident Router 在 Simple 与 Enterprise 两种策略之间选择。"
        )
    )
    story.append(
        para(
            "后端主要使用 FastAPI、LangGraph、LangChain、Qwen/DashScope、PostgreSQL 和 Milvus；前端是原生 HTML、CSS、JavaScript，没有 Vue、React 等前端框架。"
        )
    )
    story.append(
        para(
            "应用由 Uvicorn 启动。FastAPI 在启动阶段连接 Milvus 和 PostgreSQL，并通过 REST API 或 SSE 流向浏览器返回结果。"
        )
    )

    story.append(para("阅读顺序", "H2CJK"))
    story.extend(
        [
            bullet("先看系统总览，记住普通 RAG 独立，两个事故接口汇入同一个 AIOpsService。"),
            bullet("再看聊天与知识入库，理解普通问答和 Milvus 知识库的关系。"),
            bullet("然后看统一 Runtime，理解确定性路由、动态升级、审批与 PostgreSQL 恢复。"),
            bullet("接着看 Enterprise 策略，理解多个角色如何并行调查并共享工具治理。"),
            bullet("最后看启动与存储边界，确认哪些数据会保留，哪些只存在内存。"),
        ]
    )
    story.append(
        para(
            "图例：实线箭头表示同步 HTTP 或程序内部调用；虚线箭头表示 SSE、并行流程或人工中断与恢复；粗线箭头表示数据库、文件或状态读写。",
            "CalloutCJK",
        )
    )

    # Diagrams
    diagram_page(
        story,
        template="landscape",
        title="二、整体结构图 - 系统总览",
        filename="01-system-overview.png",
        caption="大白话理解：普通聊天是独立问答链路；所有故障请求进入同一个 AIOpsService。Router 选择 Simple 或 Enterprise，两种策略共享 IncidentState、Checkpoint、Gateway、审批和审计。",
    )
    diagram_page(
        story,
        template="landscape",
        title="子图一：普通聊天与知识入库",
        filename="02-chat-knowledge.png",
        caption="普通聊天使用进程内 MemorySaver；浏览器另存一份 localStorage 历史。上传文档经过切分与向量化后进入 Milvus。Chat Agent 直接绑定工具，不经过 Tool Gateway。",
    )
    diagram_page(
        story,
        template="portrait",
        title="子图二：持久化 AIOps 诊断",
        filename="03-durable-aiops.png",
        caption="Router 先依据显式策略与故障复杂度选路。Simple 证据不足时最多升级一次；Enterprise 复用公共 Executor 和 Approval。父图在每个节点后写入 PostgreSQL，重启后按 incident_id 恢复。",
    )
    diagram_page(
        story,
        template="portrait",
        title="子图三：企业多智能体事故分析",
        filename="04-enterprise-workflow.png",
        caption="Enterprise 是父图中的专业诊断策略：Triage -> RAG -> SRE/Change 并行 -> Root Cause -> Remediation -> Report。外部查询统一经过 Gateway；Provider 失败被隔离并形成 partial results，不生成替代事实。",
    )
    diagram_page(
        story,
        template="landscape",
        title="子图四：启动、存储与运行边界",
        filename="05-runtime-storage.png",
        caption="FastAPI lifespan 初始化 Milvus、PostgreSQL Saver、Incident Graph 快照与单一 AIOpsService。PostgreSQL 保存两种策略的统一状态；普通聊天的 MemorySaver 与浏览器历史保持独立。",
    )

    # Detailed explanation
    story.extend([NextPageTemplate("portrait"), PageBreak(), para("三、核心调用链", "H1CJK")])
    chains = [
        (
            "1. 普通聊天",
            "浏览器 -> Chat API -> RagAgentService -> Qwen -> 本地或 MCP 工具 -> 返回答案",
            "主要模块：static/app.js、app/api/chat.py、app/services/rag_agent_service.py、app/tools/、app/agent/mcp_client.py。",
        ),
        (
            "2. 文档进入知识库",
            "上传文件 -> File API -> uploads 目录 -> 文档切分 -> DashScope Embedding -> Milvus",
            "主要模块：app/api/file.py、document_splitter_service.py、vector_embedding_service.py、vector_index_service.py、vector_store_manager.py。",
        ),
        (
            "3. 统一 Durable Incident Runtime",
            "AIOps API -> Incident Router -> Simple 或 Enterprise -> 统一 IncidentState -> PostgreSQL -> SSE",
            "显式策略覆盖自动路由；auto 对 critical、多服务、GraphRAG/变更关联和 high+recent_change 直接选择 Enterprise，其余先走 Simple。incident_id 同时作为 LangGraph thread_id。",
        ),
        (
            "4. Enterprise 诊断策略",
            "Router -> Triage -> RAG -> SRE 与 Change 并行 -> Root Cause -> Remediation -> 公共 Executor/Approval（可选）-> Report",
            "企业兼容入口强制 enterprise，但仍调用同一个 AIOpsService。Runbook、Hybrid RAG、Incident Graph、MCP Provider 和处置工具都受统一审计边界约束。",
        ),
        (
            "5. 应用启动",
            "app.run -> Uvicorn -> FastAPI lifespan -> Milvus / PostgreSQL -> Incident Graph -> 单一 AIOpsService -> 开放接口",
            "生命周期集中创建与释放连接池；EnterpriseIncidentWorkflow 只向父图注册节点，不持有独立生产运行链。",
        ),
    ]
    for title, chain, detail in chains:
        story.append(KeepTogether([para(title, "H2CJK"), para(chain, "CalloutCJK"), para(detail)]))

    story.extend([PageBreak(), para("四、入口与诊断策略的关键差异", "H1CJK")])
    comparison_data = [
        [
            para("路径", "TableHeadCJK"),
            para("主要用途", "TableHeadCJK"),
            para("状态保存", "TableHeadCJK"),
            para("工具治理", "TableHeadCJK"),
        ],
        [para("普通聊天", "TableCellCJK"), para("问答、知识检索", "TableCellCJK"), para("MemorySaver + 浏览器 localStorage", "TableCellCJK"), para("工具直接绑定，不经过 Tool Gateway", "TableCellCJK")],
        [para("Simple 策略", "TableCellCJK"), para("低成本、逐步诊断", "TableCellCJK"), para("统一 IncidentState + PostgreSQL", "TableCellCJK"), para("Gateway、身份、策略、审批、审计", "TableCellCJK")],
        [para("Enterprise 策略", "TableCellCJK"), para("跨日志、指标、变更和图谱的多角色分析", "TableCellCJK"), para("统一 IncidentState + PostgreSQL", "TableCellCJK"), para("同一 Gateway；Provider 失败隔离", "TableCellCJK")],
    ]
    story.append(
        Table(
            comparison_data,
            colWidths=[29 * mm, 42 * mm, 58 * mm, 45 * mm],
            repeatRows=1,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FA")]),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            ),
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.extend(
        [
            bullet("普通聊天用于知识问答；需要持久化、审批或审计的故障请求统一进入 AIOpsService。"),
            bullet("Simple 优先控制成本，证据不足时由父图动态升级，已采集证据不会丢失。"),
            bullet("Enterprise 负责复杂故障的专业分工，并与 Simple 共享执行和安全底座。"),
        ]
    )

    # Responsibilities table in landscape
    story.extend([NextPageTemplate("landscape"), PageBreak(), para("五、模块职责表", "H1CJK")])
    rows = [
        ("应用入口", "注册路由、静态资源、生命周期", "app/main.py；app/run.py", "FastAPI；Uvicorn"),
        ("Web 前端", "聊天、上传、AIOps 触发和本地历史", "static/index.html；static/app.js", "Fetch；SSE；localStorage"),
        ("Chat API", "普通和流式对话、会话查询与清理", "app/api/chat.py", "RagAgentService"),
        ("文件 API", "上传文档、触发单文件或目录索引", "app/api/file.py", "VectorIndexService"),
        ("AIOps API", "统一诊断、状态查询、审批与企业兼容入口", "app/api/aiops.py", "AIOpsService"),
        ("Chat Agent", "调用模型和工具完成普通问答", "app/services/rag_agent_service.py", "Qwen；MemorySaver；MCP"),
        ("Durable Runtime", "编译单一父图并编排双策略、审批和恢复", "app/services/aiops_service.py", "LangGraph；PostgreSQL"),
        ("AIOps 节点", "Router、Planner、Executor、Replanner、Evidence Assessor", "app/agent/aiops/", "Qwen；Tool Gateway"),
        ("Tool Gateway", "工具注册、风控、审批、超时和审计", "app/agent/tool_gateway.py", "Policy；Identity；Risk"),
        ("证据治理", "统一证据结构、引用和输入检查", "app/agent/evidence.py", "IncidentState"),
        ("Enterprise 节点", "向统一父图注册多角色诊断节点", "app/agent/enterprise_workflow.py", "Gateway；Hybrid RAG；GraphRAG"),
        ("知识检索", "向量、关键词和融合检索", "vector_search_service.py；app/retrieval/hybrid.py", "Milvus；文档集合"),
        ("Incident Graph", "服务、事故、变更关系存储和查询", "app/incident_graph/", "NetworkX"),
        ("Runbook", "加载和匹配标准处置流程", "app/runbooks.py", "YAML；JSON"),
        ("变更智能", "关联事故与近期发布变更", "app/change_intelligence.py", "JSONL"),
        ("PostgreSQL 检查点", "保存可暂停、可恢复的事故状态", "app/core/checkpoint.py", "psycopg；LangGraph Saver"),
        ("Milvus 管理", "管理连接、Collection 和向量索引", "app/core/milvus_client.py", "pymilvus"),
        ("评测与回放", "验证检索质量和历史故障行为", "app/evals/；app/replay/；tests/", "pytest；JSON 数据"),
    ]
    table_data = [[para("模块/子系统", "TableHeadCJK"), para("核心职责", "TableHeadCJK"), para("关键目录或文件", "TableHeadCJK"), para("主要依赖", "TableHeadCJK")]]
    table_data.extend([[para(value, "TableCellCJK") for value in row] for row in rows])
    story.append(
        Table(
            table_data,
            colWidths=[36 * mm, 72 * mm, 89 * mm, 61 * mm],
            repeatRows=1,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F6F8FA")]),
                    ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            ),
        )
    )
    # Architecture notes and evidence
    story.extend([NextPageTemplate("portrait"), PageBreak(), para("六、架构说明", "H1CJK")])
    story.append(
        para(
            "分层说明：app/api 负责协议适配；AIOpsService 持有唯一事故父图；app/agent 提供策略节点；Tool Gateway 形成外部副作用边界；checkpoint.py 与向量服务承担持久化和数据访问。依赖始终由接入层指向运行时、策略和基础设施。",
            "CalloutCJK",
        )
    )
    sections = [
        ("模块划分原则", "普通聊天按问答场景独立；故障处理按单一 Runtime 划分。Simple 与 Enterprise 是同一父图中的可路由策略，不是两套服务。"),
        ("核心依赖方向", "正常方向为：浏览器或 API -> 路由 -> Service/Workflow -> 工具与检索 -> 数据库或外部系统。API 层主要负责参数接收、依赖获取、错误转换和流式返回。"),
        ("关键数据流", "聊天消息保存在 localStorage 与 MemorySaver；知识文档进入 Milvus；所有故障状态、路由历史、证据、审批与 Agent 输出按 incident_id 写入 PostgreSQL。"),
        ("系统边界", "项目内部负责 AI 编排、状态、检索和工具治理。Qwen、MCP、Prometheus、PostgreSQL、Milvus 属于外部运行依赖。系统没有 Redis、Kafka、RabbitMQ 等缓存或消息队列。"),
    ]
    for title, text in sections:
        story.append(para(title, "H2CJK"))
        story.append(para(text))

    story.append(para("解耦边界与设计取舍", "H2CJK"))
    story.extend(
        [
            bullet("AIOpsService 是唯一事故编排所有者；EnterpriseIncidentWorkflow 只提供节点，避免双图状态漂移。"),
            bullet("Gateway 通过 factory 创建请求级实例，策略注册共享、audit hook 隔离，避免并发事故串审计。"),
            bullet("SRE、Change 与 RAG 的外部查询统一经过 Gateway；Provider 失败写入状态而不伪造证据。"),
            bullet("普通聊天保留轻量工具链，不承担生产故障执行；这一边界通过独立 API 和状态存储体现。"),
            bullet("restart_service 被定义为 write 风险；production 需要审批且执行层强制 dry_run。"),
            bullet("旧 planner/executor/replanner/approval 节点名保留，v1 Checkpoint 可按原 next node 恢复。"),
        ]
    )

    story.append(para("七、依据与运行边界", "H1CJK"))
    story.append(para("关键代码依据", "H2CJK"))
    references = [
        "app/main.py：应用生命周期、路由与服务初始化。",
        "app/api/aiops.py：AIOps、事故查询、人工审批和企业接口。",
        "app/services/aiops_service.py：持久化工作流拓扑与恢复方式。",
        "app/agent/tool_gateway.py：工具治理边界。",
        "app/agent/enterprise_workflow.py：企业多智能体流程。",
        "app/services/rag_agent_service.py：普通聊天、MemorySaver 和工具绑定。",
        "app/core/checkpoint.py：PostgreSQL LangGraph 检查点。",
        "static/app.js：前端请求、SSE 和 localStorage。",
        "docs/learning/README.md：能力课程和验收索引。",
    ]
    story.extend([bullet(item) for item in references])

    story.append(para("运行边界声明", "H2CJK"))
    uncertainties = [
        "仓库交付本地与 Docker Compose 运行方式，不绑定 Kubernetes、虚拟机或特定云厂商。",
        "MCP 服务是协议适配器；日志、指标与变更的权限范围由部署环境配置。",
        "Incident Graph 快照带 source=sample provenance，报告能够区分样例来源与真实 Provider 证据。",
        "OpenTelemetry 与 AgentOps 记录 span、成本和角色状态；Exporter 由部署环境注入。",
        "PostgreSQL 负责 LangGraph 检查点；备份、高可用和灾备属于数据库基础设施职责。",
    ]
    story.extend([bullet(item) for item in uncertainties])

    story.append(
        para(
            "验证记录：Python 3.13.15 下全量 pytest 132 passed，代码覆盖率 66.42%；PostgreSQL 18.6 集成测试覆盖连接池重建、事故隔离和中断后不重复节点恢复。",
            "CalloutCJK",
        )
    )

    return story


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = ArchitectureDocTemplate(str(OUTPUT))
    document.build(build_story())
    print(OUTPUT)


if __name__ == "__main__":
    main()
