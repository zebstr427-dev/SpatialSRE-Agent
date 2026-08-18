const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const outputDir = __dirname;

function systemOverviewSvg() {
  return String.raw`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1080" role="img" aria-labelledby="overview-title overview-desc">
  <title id="overview-title">SuperBizAgent 系统总览</title>
  <desc id="overview-desc">普通 Chat 与单一 Durable Incident Runtime，以及只读工具绑定、Tool Gateway、可扩展工具目录和持久化边界。</desc>
  <foreignObject x="0" y="0" width="1600" height="1080">
    <div xmlns="http://www.w3.org/1999/xhtml" class="overview">
      <style>
        * { box-sizing: border-box; }
        .overview {
          width: 1600px; height: 1080px; padding: 24px 30px 22px;
          background: #f7f9fc; color: #17324d;
          font-family: "Microsoft YaHei", "Noto Sans SC", sans-serif;
        }
        h1 { margin: 0; text-align: center; font-size: 28px; letter-spacing: 1px; }
        .subtitle { margin: 5px 0 14px; text-align: center; color: #53677a; font-size: 14px; }
        .layer { border: 1px solid #9fb2c5; border-radius: 12px; background: #ffffff; padding: 10px 14px 12px; margin-top: 9px; }
        .layer-title { margin-bottom: 8px; color: #315b82; font-size: 15px; font-weight: 700; letter-spacing: .5px; }
        .row { display: grid; gap: 12px; align-items: stretch; }
        .access { grid-template-columns: 1fr 1.5fr; }
        .services { grid-template-columns: 1fr 1fr 1.5fr; }
        .runtime { grid-template-columns: .92fr 1.15fr 1.35fr 1.15fr .9fr; align-items: center; }
        .tool-paths { grid-template-columns: .85fr 1.45fr; margin-bottom: 8px; }
        .providers { grid-template-columns: 1fr 1fr 1.2fr; }
        .resources { grid-template-columns: repeat(5, 1fr); }
        .card { min-height: 62px; border: 1.4px solid #5f86ad; border-radius: 8px; background: #e8f1fb; padding: 8px 10px; text-align: center; display: flex; flex-direction: column; justify-content: center; }
        .card strong { font-size: 15px; line-height: 1.35; }
        .card span { margin-top: 3px; color: #3f566c; font-size: 12px; line-height: 1.35; }
        .safe { background: #eef7ef; border-color: #6d9a74; }
        .warn { background: #fff7e8; border-color: #c28b3c; }
        .danger { background: #fff0f0; border-color: #b65a5a; }
        .state { background: #f2ecfb; border-color: #816ca6; }
        .dark { background: #315b82; border-color: #315b82; color: #ffffff; }
        .dark span { color: #eaf3fb; }
        .arrow { display: flex; align-items: center; justify-content: center; color: #53677a; font-size: 24px; font-weight: 700; }
        .inline-flow { display: grid; grid-template-columns: 1fr 28px 1fr 28px 1fr; gap: 4px; align-items: center; }
        .stack { display: grid; grid-template-columns: 1fr; gap: 7px; }
        .contract { margin: 0 auto 8px; width: 64%; }
        .note { margin-top: 7px; padding: 6px 10px; border-radius: 7px; background: #edf3f8; color: #40576d; font-size: 12px; text-align: center; }
        .legend { display: flex; justify-content: center; gap: 18px; margin-top: 8px; color: #53677a; font-size: 11px; }
        .dot { display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 4px; }
      </style>

      <h1>SuperBizAgent 系统总览</h1>
      <div class="subtitle">普通 Chat 保持轻量只读；所有事故调用汇入单一 Durable Incident Runtime，共享工具治理、审批、证据、审计与 Checkpoint。</div>

      <section class="layer">
        <div class="layer-title">1. 访问与 FastAPI 接入层</div>
        <div class="row access">
          <div class="card"><strong>Web 控制台 / API 调用方</strong><span>聊天、Incident 配置、审批卡片、REST / SSE</span></div>
          <div class="card dark"><strong>FastAPI App + lifespan</strong><span>/api/chat | /api/upload | /api/aiops | /api/enterprise/incidents | /api/incidents/{id}</span></div>
        </div>
      </section>

      <section class="layer">
        <div class="layer-title">2. 业务入口</div>
        <div class="row services">
          <div class="card safe"><strong>RagAgentService</strong><span>独立普通 Chat / RAG；MemorySaver 会话</span></div>
          <div class="card safe"><strong>知识入库</strong><span>文档切分 -> Embedding -> Milvus</span></div>
          <div class="card dark"><strong>AIOpsService</strong><span>单一 Durable Incident Runtime；一张持久化 LangGraph</span></div>
        </div>
      </section>

      <section class="layer">
        <div class="layer-title">3. 统一 Incident 父图：Simple / Enterprise 双策略自动路由</div>
        <div class="row runtime">
          <div class="card"><strong>Incident Router</strong><span>确定性规则 + 显式策略覆盖</span></div>
          <div class="card"><strong>Simple</strong><span>Planner / Executor / Replanner / Evidence Assessor</span></div>
          <div class="card warn"><strong>动态升级</strong><span>Auto 且证据不足时 Simple -> Enterprise；最多一次</span></div>
          <div class="card"><strong>Enterprise</strong><span>Triage / RAG / SRE / Change / RCA / Remediation / Report</span></div>
          <div class="card state"><strong>IncidentState v2</strong><span>路由历史、证据、工具审计、报告与 SSE 事件</span></div>
        </div>
      </section>

      <section class="layer">
        <div class="layer-title">4. 工具接入与治理边界</div>
        <div class="row tool-paths">
          <div class="stack">
            <div class="card safe"><strong>Chat Read-only Tool Binding</strong><span>只读 allowlist；不暴露 restart_service 等处置工具</span></div>
            <div class="note">普通 Chat 可使用本地只读工具和 MCP 只读子集，但不承担生产处置。</div>
          </div>
          <div class="inline-flow">
            <div class="card"><strong>Simple / Enterprise Tool Calls</strong><span>事故策略不直连 Provider</span></div>
            <div class="arrow">→</div>
            <div class="card"><strong>Tool Gateway Factory</strong><span>为每次节点调用创建隔离实例</span></div>
            <div class="arrow">→</div>
            <div class="card warn"><strong>Tool Gateway Instance</strong><span>Identity / Risk / Policy / Approval / Timeout / Audit</span></div>
          </div>
        </div>
        <div class="card contract"><strong>Tool Catalog / Registration Contract</strong><span>LangChain BaseTool / StructuredTool；本地注册 + MCP 动态发现；下方只是当前示例，不是工具上限</span></div>
        <div class="row providers">
          <div class="card safe"><strong>本地只读工具（可扩展）</strong><span>知识检索 / 时间 / 指标 / 变更查询</span></div>
          <div class="card danger"><strong>受控处置工具</strong><span>restart_service：经 Gateway 审批，始终强制 dry-run</span></div>
          <div class="card"><strong>MCP 动态工具（可扩展）</strong><span>日志 / 指标 / 变更 / CMDB / 云平台 / 工单等外部 Provider</span></div>
        </div>
        <div class="note">Gateway 是治理边界，不是固定工具清单；每次调用统一沉淀 Evidence / Citations / Tool Audit / Policy Decision / Provider Failure。</div>
      </section>

      <section class="layer">
        <div class="layer-title">5. 模型、知识与持久化边界</div>
        <div class="row resources">
          <div class="card"><strong>DashScope / Qwen</strong><span>Chat、Simple 与 Enterprise 的模型 Provider</span></div>
          <div class="card"><strong>Milvus</strong><span>普通 RAG + Hybrid Retrieval 向量检索</span></div>
          <div class="card"><strong>Runbook + Incident Graph</strong><span>确定性 Registry 与版本化快照</span></div>
          <div class="card"><strong>MemorySaver + localStorage</strong><span>普通 Chat 进程内状态 + 浏览器展示历史</span></div>
          <div class="card state"><strong>LangGraph Checkpointer</strong><span>PostgreSQL 持久化 Incident 父图；支持审批中断与恢复</span></div>
        </div>
      </section>

      <div class="legend">
        <span><i class="dot" style="background:#eef7ef;border:1px solid #6d9a74"></i>只读 / 轻量链路</span>
        <span><i class="dot" style="background:#fff7e8;border:1px solid #c28b3c"></i>安全治理边界</span>
        <span><i class="dot" style="background:#fff0f0;border:1px solid #b65a5a"></i>受控处置</span>
        <span><i class="dot" style="background:#f2ecfb;border:1px solid #816ca6"></i>持久化状态</span>
      </div>
    </div>
  </foreignObject>
</svg>`;
}

const diagrams = {
  // The overview is rendered by the fixed A3 grid above. This Mermaid source
  // remains as a searchable semantic reference for the same architecture.
  '01-system-overview': String.raw`
flowchart TB
    Access["Web 控制台 / API 调用方<br/>聊天、Incident 配置、审批卡片、REST / SSE"]
    API["FastAPI App + lifespan<br/>/api/chat | /api/upload | /api/aiops<br/>/api/enterprise/incidents | /api/incidents/{id}"]

    subgraph S["业务入口与统一事故 Runtime"]
        direction LR
        ChatAgent["RagAgentService<br/>独立普通 Chat / RAG"]
        IndexPipeline["文档切分 -> Embedding -> Milvus"]
        Runtime["AIOpsService<br/>单一 Durable Incident Runtime<br/>一张持久化 LangGraph"]
    end

    subgraph G["统一 Incident 父图：双策略自动路由"]
        direction LR
        Router{"Incident Router<br/>确定性规则 + 显式覆盖"}
        Simple["Simple<br/>Planner / Executor / Replanner<br/>Evidence Assessor"]
        Enterprise["Enterprise<br/>Triage / RAG / SRE / Change<br/>Root Cause / Remediation / Report"]
        State["统一 IncidentState v2<br/>节点状态、路由历史、证据与报告"]
        Events["REST / SSE 输出<br/>routing / escalation / agent_update<br/>approval_required / complete"]
    end

    subgraph T["工具接入与治理边界"]
        direction TB
        ChatBinding["Chat Read-only Tool Binding<br/>只读 allowlist，不暴露处置工具"]
        IncidentCalls["Simple / Enterprise Tool Calls<br/>所有事故工具调用进入治理边界"]
        GatewayFactory["Tool Gateway Factory<br/>为节点创建隔离实例"]
        Gateway["Tool Gateway Instance<br/>Identity / Risk / Policy<br/>Approval / Timeout / Audit"]
        Catalog["Tool Catalog / Registration Contract<br/>LangChain BaseTool / StructuredTool<br/>本地注册 + MCP 动态发现"]
        ReadTools["本地只读工具（当前示例，可扩展）<br/>知识 / 时间 / 指标 / 变更查询"]
        ActionTools["受控处置工具<br/>restart_service：审批 + 强制 dry-run"]
        MCPTools["MCP 动态工具（当前示例，可扩展）<br/>日志 / 指标 / 变更 / CMDB / 云平台 / 工单等"]
        Trace["沉淀到 IncidentState<br/>Evidence / Citations / Tool Audit<br/>Policy Decision / Provider Failure"]
    end

    subgraph P["模型、知识与持久化边界"]
        direction LR
        Qwen["Model Provider<br/>DashScope / Qwen"]
        Milvus[("Milvus<br/>普通 RAG + Hybrid Retrieval")]
        StaticKnowledge[("确定性知识资源<br/>Runbook Registry<br/>Incident Graph 版本快照")]
        ChatMemory[("MemorySaver<br/>普通 Chat 进程内会话")]
        BrowserStore[("localStorage<br/>浏览器展示历史")]
        Persistence["LangGraph Checkpointer<br/>PostgreSQL Incident Checkpoint"]
    end

    Access --> API
    API -->|"/api/chat"| ChatAgent
    API -->|"/api/upload"| IndexPipeline
    API -->|"事故提交 / 查询 / Command resume"| Runtime
    Runtime --> Router
    Router -->|"simple"| Simple
    Router -->|"enterprise"| Enterprise
    Simple -.->|"auto 且证据不足，最多升级一次"| Enterprise
    Simple --> State
    Enterprise --> State
    State --> Events

    ChatAgent --> ChatBinding
    ChatBinding -.->|"遵循统一 Tool 契约"| Catalog
    ChatBinding -->|"本地只读子集"| ReadTools
    ChatBinding -->|"MCP 只读 allowlist"| MCPTools
    Simple --> IncidentCalls
    Enterprise --> IncidentCalls
    IncidentCalls --> GatewayFactory
    GatewayFactory --> Gateway
    Gateway --> Catalog
    Catalog --> ReadTools
    Catalog --> ActionTools
    Catalog --> MCPTools
    Gateway --> Trace

    ChatAgent --> Qwen
    Simple --> Qwen
    Enterprise --> Qwen
    IndexPipeline ==> Milvus
    ReadTools -.->|"retrieve_knowledge"| Milvus
    Enterprise --> StaticKnowledge
    ChatAgent ==> ChatMemory
    Access ==> BrowserStore
    State ==> Persistence
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
        MCPTools["MCP 只读工具<br/>日志和监控能力"]
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
    if (name === '01-system-overview') {
      await page.locator('#mount').evaluate((mount, markup) => {
        mount.innerHTML = markup;
        mount.querySelector('svg').style.width = '1600px';
      }, systemOverviewSvg());
    } else {
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
    }

    const mount = page.locator('#mount');
    const svgMarkup = await mount.locator('svg').evaluate((svg) => svg.outerHTML);
    fs.writeFileSync(path.join(outputDir, `${name}.svg`), svgMarkup, 'utf8');
    await mount.screenshot({
      path: path.join(outputDir, `${name}.png`),
      type: 'png',
      animations: 'disabled',
    });

    if (name === '01-system-overview') {
      const pdfPage = await context.newPage();
      await pdfPage.setContent(`
        <style>
          @page { size: A3 landscape; margin: 8mm; }
          html, body { width: 100%; height: 100%; margin: 0; background: #ffffff; }
          body { display: flex; align-items: center; justify-content: center; }
          svg { display: block; width: 100%; height: 100%; max-width: 100%; max-height: 100%; }
        </style>
        ${svgMarkup}
      `, { waitUntil: 'load' });
      await pdfPage.pdf({
        path: path.join(outputDir, `${name}.pdf`),
        format: 'A3',
        landscape: true,
        printBackground: true,
        preferCSSPageSize: true,
      });
      await pdfPage.close();
    }
  }

  await browser.close();
  fs.writeFileSync(path.join(outputDir, 'render-complete.txt'), 'ok\n');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
