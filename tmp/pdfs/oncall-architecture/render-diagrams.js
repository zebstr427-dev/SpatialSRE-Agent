const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const outputDir = __dirname;

const diagrams = {
  '01-system-overview': String.raw`
flowchart TB
    subgraph U["用户"]
        Web["Web 控制台<br/>聊天、Incident 配置、审批卡片"]
        Caller["API 调用方<br/>REST / SSE"]
    end

    subgraph A["FastAPI 接入层"]
        Main["FastAPI lifespan<br/>路由与依赖注入"]
        ChatAPI["/api/chat<br/>普通问答"]
        FileAPI["/api/upload<br/>知识入库"]
        AIOpsAPI["/api/aiops<br/>默认 strategy=auto"]
        EnterpriseAPI["/api/enterprise/incidents<br/>兼容入口，强制 enterprise"]
        IncidentAPI["/api/incidents/{id}<br/>状态查询与审批恢复"]
    end

    subgraph CHAT["独立的普通 RAG 链路"]
        ChatAgent["RagAgentService<br/>问答与工具调用"]
        IndexPipeline["切分 -> Embedding -> Milvus"]
        ChatStore[("MemorySaver / localStorage<br/>Milvus 知识向量")]
    end

    subgraph RUNTIME["单一 Durable Incident Runtime：AIOpsService"]
        Router{"Incident Router<br/>确定性规则 + 显式覆盖"}
        Simple["Simple 策略<br/>Planner -> Executor -> Replanner"]
        Assess{"Evidence Assessor<br/>置信度是否 >= 0.60"}
        Enterprise["Enterprise 策略节点<br/>Triage / RAG / SRE / Change<br/>Root Cause / Remediation / Report"]
        State["统一 IncidentState v2<br/>节点状态、路由历史、证据与报告"]
    end

    subgraph CONTROL["两种策略共享的治理边界"]
        Governance["Tool Gateway Factory<br/>Identity / Risk / Policy / Approval"]
        Trace["Evidence / Citations / Tool Audit<br/>Provider Failure Isolation"]
        Checkpoint[("PostgreSQL Checkpoint<br/>每个父图节点后持久化")]
    end

    subgraph PROVIDERS["Provider 与知识来源"]
        Knowledge[("Runbook / Milvus Hybrid RAG<br/>Incident Graph 快照")]
        Tools["本地工具 / MCP 适配器<br/>日志、指标、变更"]
        Qwen["DashScope / Qwen"]
    end

    Web --> Main
    Caller --> Main
    Main --> ChatAPI
    Main --> FileAPI
    Main --> AIOpsAPI
    Main --> EnterpriseAPI
    Main --> IncidentAPI
    ChatAPI --> ChatAgent
    FileAPI --> IndexPipeline
    ChatAgent ==> ChatStore
    IndexPipeline ==> ChatStore
    ChatAgent --> Qwen

    AIOpsAPI --> Router
    EnterpriseAPI -->|"requested_strategy=enterprise"| Router
    Router -->|"simple"| Simple
    Router -->|"enterprise"| Enterprise
    Simple --> Assess
    Assess -->|"证据充分"| State
    Assess -->|"auto 且不足，最多升级一次"| Enterprise
    Enterprise --> State
    IncidentAPI -.->|"查询 / Command resume"| State
    State ==> Checkpoint
    Simple --> Governance
    Enterprise --> Governance
    Governance --> Tools
    Governance --> Trace
    Trace --> State
    Enterprise --> Knowledge
    Knowledge --> Trace
    Simple --> Qwen
    Enterprise --> Qwen
    State -.->|"routing / agent / approval / complete"| Web
`,
  '02-chat-knowledge': String.raw`
flowchart LR
    subgraph F["浏览器"]
        UI["聊天页面<br/>提问、流式显示、上传文件"]
        LocalHistory[("localStorage<br/>前端会话列表")]
    end

    subgraph API["接口层"]
        ChatRoute["Chat API<br/>普通回答、流式回答、会话管理"]
        UploadRoute["File API<br/>校验并保存 txt / md"]
    end

    subgraph CHAT["聊天处理"]
        RagAgent["RagAgentService<br/>创建 LangChain Agent"]
        ChatMemory[("MemorySaver<br/>进程内对话状态")]
        LocalTools["本地工具<br/>时间、知识、指标、变更"]
        MCPTools["MCP 工具<br/>日志和监控能力"]
    end

    subgraph KNOWLEDGE["知识入库与检索"]
        Uploads[("uploads 目录<br/>原始文件")]
        Splitter["文档切分<br/>生成重叠文本块"]
        Embedding["向量化服务<br/>DashScope Embedding"]
        VectorIndex["向量索引服务<br/>写入 biz collection"]
        VectorSearch["向量搜索服务<br/>返回 Top-K 文档"]
        Milvus[("Milvus<br/>1024 维知识向量")]
    end

    Qwen["Qwen 模型<br/>理解问题、选择工具、组织答案"]
    Boundary["架构边界<br/>普通聊天不进入 Durable Incident Runtime"]

    UI -->|"POST /api/chat"| ChatRoute
    UI -.->|"POST /api/chat_stream"| ChatRoute
    UI ==> LocalHistory
    ChatRoute --> RagAgent
    RagAgent --> Qwen
    RagAgent --> LocalTools
    RagAgent --> MCPTools
    RagAgent ==> ChatMemory
    LocalTools --> VectorSearch
    VectorSearch ==> Milvus
    VectorSearch --> RagAgent
    RagAgent -.->|"逐段返回答案"| UI
    RagAgent -.-> Boundary
    UI -->|"上传文件"| UploadRoute
    UploadRoute ==> Uploads
    UploadRoute --> Splitter
    Splitter --> Embedding
    Embedding --> VectorIndex
    VectorIndex ==> Milvus
`,
  '03-durable-aiops': String.raw`
flowchart TB
    Request["AIOpsRequest<br/>input / alert / identity<br/>strategy / execute_remediation"]
    State["IncidentState v2<br/>单一父图、统一状态 schema"]
    Router{"incident_router<br/>显式策略优先；auto 使用确定性规则"}

    subgraph SIMPLE["Simple 诊断策略"]
        Planner["planner<br/>生成最小诊断计划"]
        Executor["executor<br/>逐步调用 Gateway 并沉淀证据"]
        NeedApproval{"pending_tool_calls?"}
        Approval["approval<br/>LangGraph interrupt / resume"]
        Replanner["replanner<br/>继续计划或形成报告"]
        EvidenceAssessor{"evidence_assessor<br/>置信度、报告与失败步骤"}
    end

    subgraph ENTERPRISE["Enterprise 诊断策略"]
        Triage["enterprise_triage"]
        RAG["enterprise_rag<br/>Runbook / Hybrid / Graph"]
        SRE["enterprise_sre<br/>日志与指标"]
        Change["enterprise_change<br/>近期变更关联"]
        RCA["enterprise_root_cause"]
        Remediation["enterprise_remediation<br/>建议或结构化执行计划"]
        Report["enterprise_report"]
    end

    subgraph SHARED["共享执行、安全与可恢复性"]
        Gateway["create_tool_gateway<br/>请求级实例，隔离 audit hook"]
        Control["Identity -> Risk -> Policy<br/>拒绝 / 审批 / forced dry-run"]
        Audit["evidence / tool_calls<br/>policy_decisions / routing_history"]
        PostgreSQL[("PostgreSQL Saver<br/>thread_id = incident_id")]
    end

    Request --> State
    State --> Router
    Router -->|"simple：默认低成本"| Planner
    Router -->|"enterprise：critical / 多服务<br/>GraphRAG / 变更关联 / high+recent_change"| Triage
    Planner --> Executor
    Executor --> Gateway
    Gateway --> Control
    Control --> Audit
    Audit --> Executor
    Executor --> NeedApproval
    NeedApproval -->|"不需要"| Replanner
    NeedApproval -->|"需要"| Approval
    Approval -->|"批准或拒绝后恢复"| Executor
    Replanner -->|"仍有计划"| Executor
    Replanner -->|"已有报告"| EvidenceAssessor
    EvidenceAssessor -->|">= 0.60 且证据充分"| End["END<br/>completed"]
    EvidenceAssessor -->|"auto 证据不足<br/>escalation_count < 1"| Triage

    Triage --> RAG
    RAG -.-> SRE
    RAG -.-> Change
    SRE --> RCA
    Change --> RCA
    RCA --> Remediation
    Remediation -->|"仅建议"| Report
    Remediation -->|"execute_remediation=true"| Executor
    Executor -->|"Enterprise 计划完成"| Report
    Report --> EnterpriseEnd["END<br/>completed / completed_with_partial_results"]

    State ==>|"父图在每个节点后保存"| PostgreSQL
`,
  '04-enterprise-workflow': String.raw`
flowchart TB
    API["/api/aiops strategy=enterprise<br/>或企业兼容入口"]
    Runtime["AIOpsService<br/>统一父图 + PostgreSQL Checkpoint"]
    Triage["Triage Agent<br/>影响范围、优先级、调查方向"]
    RAG["RAG Agent<br/>Runbook / Hybrid RAG / Incident Graph"]

    subgraph PARALLEL["并行调查"]
        SRE["SRE Agent<br/>经 Gateway 查询指标与日志"]
        Change["Change Agent<br/>经 Gateway 查询变更并做关联"]
    end

    RootCause["Root Cause<br/>汇总证据并判断可能根因"]
    Remediation["Remediation<br/>建议；可选生成公共 Executor 计划"]
    Report["Report Agent<br/>生成结构化事故报告"]
    Response["统一持久化状态 + SSE / JSON<br/>完整或 partial results"]

    Gateway["Tool Gateway Factory<br/>身份、策略、审批、审计"]
    Hybrid[("Milvus / Hybrid Retriever")]
    GraphRAG[("版本化 Incident Graph 快照<br/>sample provenance")]
    Runbooks[("Runbook YAML / JSON")]
    Providers["MCP Provider<br/>metrics / logs / changes"]
    Failure["Provider Failure Isolation<br/>记录失败，不伪造事实"]
    CommonExecutor["公共 Executor / Approval<br/>restart_service 永远 dry_run"]

    API --> Runtime
    Runtime --> Triage
    Triage --> RAG
    RAG --> Gateway
    Gateway --> Hybrid
    Gateway --> GraphRAG
    Gateway --> Runbooks
    Hybrid ==> Runbooks
    RAG -.-> SRE
    RAG -.-> Change
    SRE --> Gateway
    Change --> Gateway
    Gateway --> Providers
    Providers -.->|"单 Provider 失败"| Failure
    SRE -.->|"并行结果汇合"| RootCause
    Change -.->|"并行结果汇合"| RootCause
    Failure --> RootCause
    RootCause --> Remediation
    Remediation -->|"execute_remediation=true"| CommonExecutor
    CommonExecutor --> Report
    Remediation --> Report
    Report --> Response
    Response ==> Runtime
`,
  '05-runtime-storage': String.raw`
flowchart LR
    subgraph STARTUP["启动过程"]
        Start["启动命令<br/>app.run / Makefile / Windows 脚本"]
        Uvicorn["Uvicorn<br/>启动 FastAPI 进程"]
        Lifespan["FastAPI lifespan<br/>初始化与释放资源"]
        MilvusConnect["连接 Milvus<br/>加载或创建 biz collection"]
        PGConnect["连接 PostgreSQL<br/>初始化 LangGraph Saver"]
        LoadGraph["加载 Incident Graph 快照<br/>保留 source provenance"]
        InitServices["初始化单一 AIOpsService<br/>注入 Enterprise 节点与 Gateway factory"]
        Ready["应用可用<br/>监听 9900 端口"]
    end

    subgraph DATA["运行数据"]
        PG[("PostgreSQL<br/>统一 IncidentState 检查点")]
        MV[("Milvus<br/>知识文档向量")]
        Files[("版本化文件<br/>Runbook、Graph 快照、策略、评测")]
        Memory[("进程内内存<br/>普通 Chat MemorySaver")]
        Browser[("浏览器 localStorage<br/>前端聊天历史")]
    end

    subgraph EXTERNAL["外部依赖"]
        DashScope["DashScope<br/>Qwen 与 Embedding"]
        MCP["MCP 服务<br/>默认 8003 / 8004"]
        Prometheus["Prometheus<br/>默认 9090"]
    end

    subgraph OPS["测试与观测"]
        Tests["测试体系<br/>unit、integration、eval、replay"]
        Logs["Loguru<br/>应用日志"]
        OTel["AgentOps / OpenTelemetry<br/>span、成本、角色状态"]
    end

    Start --> Uvicorn
    Uvicorn --> Lifespan
    Lifespan --> MilvusConnect
    Lifespan --> PGConnect
    Lifespan --> LoadGraph
    MilvusConnect --> InitServices
    PGConnect --> InitServices
    LoadGraph --> InitServices
    InitServices --> Ready
    MilvusConnect ==> MV
    PGConnect ==> PG
    Ready ==> Files
    Ready ==> Memory
    Ready ==> Browser
    Ready --> DashScope
    Ready --> MCP
    Ready --> Prometheus
    Ready --> Logs
    Ready --> OTel
    Tests -.->|"验证路由、升级、并行、审批与恢复"| InitServices
`,
};

async function main() {
  const browser = await chromium.launch({
    headless: true,
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  });
  const context = await browser.newContext({
    viewport: { width: 2100, height: 1400 },
    deviceScaleFactor: 2,
  });
  const page = await context.newPage();

  await page.setContent(`
    <style>
      html, body { margin: 0; padding: 0; background: #ffffff; }
      #mount { display: inline-block; padding: 28px; background: #ffffff; }
      #mount svg { display: block; max-width: none !important; height: auto !important; }
    </style>
    <div id="mount"></div>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
  `, { waitUntil: 'networkidle' });

  await page.waitForFunction(() => typeof window.mermaid !== 'undefined');
  await page.evaluate(() => {
    window.mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'loose',
      theme: 'base',
      flowchart: {
        curve: 'linear',
        htmlLabels: true,
        nodeSpacing: 34,
        rankSpacing: 42,
        useMaxWidth: false,
      },
      themeVariables: {
        fontFamily: 'Microsoft YaHei, Noto Sans SC, sans-serif',
        fontSize: '18px',
        primaryColor: '#e8f1fb',
        primaryTextColor: '#17324d',
        primaryBorderColor: '#5f86ad',
        secondaryColor: '#eef7ef',
        tertiaryColor: '#fff7e8',
        lineColor: '#53677a',
        clusterBkg: '#f7f9fb',
        clusterBorder: '#a7b5c3',
        edgeLabelBackground: '#ffffff',
        mainBkg: '#e8f1fb',
        nodeBorder: '#5f86ad',
      },
    });
  });

  for (const [name, code] of Object.entries(diagrams)) {
    await page.evaluate(async ({ name, code }) => {
      const mount = document.getElementById('mount');
      const result = await window.mermaid.render(`diagram-${name}`, code);
      mount.innerHTML = result.svg;
      const svg = mount.querySelector('svg');
      svg.removeAttribute('width');
      svg.removeAttribute('height');
      const viewBox = svg.viewBox.baseVal;
      const targetWidth = Math.min(2300, Math.max(1500, viewBox.width));
      svg.style.width = `${targetWidth}px`;
    }, { name, code });

    const mount = page.locator('#mount');
    const svgMarkup = await mount.locator('svg').evaluate((svg) => svg.outerHTML);
    fs.writeFileSync(path.join(outputDir, `${name}.svg`), svgMarkup, 'utf8');
    await mount.screenshot({
      path: path.join(outputDir, `${name}.png`),
      type: 'png',
      animations: 'disabled',
    });
  }

  await browser.close();
  fs.writeFileSync(path.join(outputDir, 'render-complete.txt'), 'ok\n');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
