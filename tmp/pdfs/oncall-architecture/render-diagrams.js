const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const outputDir = __dirname;

const diagrams = {
  '01-system-overview': String.raw`
flowchart TB
    subgraph U["用户入口"]
        Web["Web 前端<br/>聊天、上传文件、触发 AIOps"]
        Caller["外部调用方<br/>调用 REST 或 SSE API"]
        Operator["值班人员<br/>查询事故、执行人工审批"]
    end

    subgraph A["接入层：FastAPI"]
        Main["应用入口<br/>路由、静态页面、生命周期"]
        ChatAPI["聊天接口<br/>/api/chat 与 /api/chat_stream"]
        FileAPI["文件接口<br/>/api/upload 与目录索引"]
        AIOpsAPI["持久化运维接口<br/>诊断、状态与审批"]
        EnterpriseAPI["企业事故接口<br/>/api/enterprise/incidents"]
    end

    subgraph B["核心业务层"]
        ChatAgent["RAG Chat Agent<br/>普通对话与知识问答"]
        IndexPipeline["知识入库流水线<br/>切分、向量化、建索引"]
        DurableAIOps["持久化 AIOps<br/>Plan-Execute-Replan"]
        EnterpriseFlow["企业多智能体工作流<br/>结构化事故分析"]
    end

    subgraph C["平台能力层"]
        Gateway["Tool Gateway<br/>风控、审批、重试、审计"]
        Retrieval["知识检索<br/>向量检索与 Hybrid RAG"]
        GraphRAG["Incident Graph / GraphRAG<br/>关联服务、变更和历史事故"]
        Evidence["证据治理<br/>来源、引用和输入防护"]
    end

    subgraph D["数据与外部系统"]
        PostgreSQL[("PostgreSQL<br/>AIOps 检查点")]
        Milvus[("Milvus<br/>知识文档向量")]
        FileStore[("本地文件<br/>文档、Runbook、变更、策略")]
        MemoryState[("进程内状态<br/>MemorySaver 与 NetworkX")]
        Qwen["DashScope / Qwen<br/>推理与向量化"]
        MCP["MCP 与 Prometheus<br/>日志、指标、监控工具"]
    end

    Web --> Main
    Caller --> Main
    Operator --> Main
    Main --> ChatAPI
    Main --> FileAPI
    Main --> AIOpsAPI
    Main --> EnterpriseAPI
    ChatAPI --> ChatAgent
    FileAPI --> IndexPipeline
    AIOpsAPI --> DurableAIOps
    EnterpriseAPI --> EnterpriseFlow
    ChatAgent --> Qwen
    ChatAgent --> Retrieval
    ChatAgent ==> MemoryState
    IndexPipeline --> Qwen
    IndexPipeline ==> Milvus
    IndexPipeline ==> FileStore
    DurableAIOps --> Qwen
    DurableAIOps --> Gateway
    DurableAIOps --> Evidence
    DurableAIOps ==> PostgreSQL
    EnterpriseFlow --> Retrieval
    EnterpriseFlow --> GraphRAG
    EnterpriseFlow --> Evidence
    EnterpriseFlow ==> FileStore
    EnterpriseFlow ==> MemoryState
    Retrieval ==> Milvus
    GraphRAG ==> MemoryState
    Gateway --> MCP
    DurableAIOps -.->|"SSE 诊断事件"| Web
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
    Boundary["边界提示<br/>Chat 工具不经过 Tool Gateway"]

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
    Request["AIOps 请求<br/>会话、事故编号、告警、身份"]
    Guardrail["输入防护<br/>校验并清理事故输入"]
    State["IncidentState<br/>计划、证据、工具调用、审批状态"]

    subgraph GRAPH["LangGraph：Plan-Execute-Replan"]
        Planner["Planner<br/>制定诊断步骤"]
        Executor["Executor<br/>执行当前步骤并收集结果"]
        NeedApproval{"是否有<br/>待审批工具调用"}
        Approval["Approval Node<br/>暂停等待人工决定"]
        Replanner["Replanner<br/>继续、调整计划或形成报告"]
        Finished{"是否得到<br/>最终响应"}
    end

    subgraph CONTROL["工具执行控制"]
        Gateway["Tool Gateway<br/>受控工具统一入口"]
        Identity["身份范围<br/>工具、服务、风险上限"]
        Risk["风险分类<br/>只读、写操作、高风险"]
        Policy["Policy-as-Code<br/>允许、拒绝、要求审批"]
        ExecuteTool["执行工具<br/>超时、重试、dry-run、审计"]
        Evidence["证据记录<br/>来源、内容、采集时间"]
    end

    PostgreSQL[("PostgreSQL<br/>按 incident_id 保存检查点")]
    Human["值班人员<br/>批准或拒绝"]
    SSE["SSE 事件流<br/>plan、step、approval、complete、error"]
    Tools["本地工具 / MCP / Prometheus<br/>日志、指标、知识、变更"]

    Request --> Guardrail
    Guardrail --> State
    State --> Planner
    Planner --> Executor
    Executor --> Gateway
    Gateway --> Identity
    Identity --> Risk
    Risk --> Policy
    Policy --> ExecuteTool
    ExecuteTool --> Tools
    ExecuteTool --> Evidence
    Evidence --> Executor
    Executor --> NeedApproval
    NeedApproval -->|"不需要"| Replanner
    NeedApproval -->|"需要"| Approval
    Approval -.->|"interrupt"| Human
    Human -.->|"审批 API + resume"| Approval
    Approval --> Executor
    Replanner --> Finished
    Finished -->|"还有步骤"| Executor
    Finished -->|"完成"| SSE
    Planner ==> PostgreSQL
    Executor ==> PostgreSQL
    Approval ==> PostgreSQL
    Replanner ==> PostgreSQL
    Planner -.-> SSE
    Executor -.-> SSE
    Approval -.-> SSE
`,
  '04-enterprise-workflow': String.raw`
flowchart TB
    API["POST /api/enterprise/incidents<br/>事故描述与告警"]
    Validate["输入 Guardrail<br/>拒绝空输入和不合规输入"]
    Triage["Triage Agent<br/>判断影响范围和事故优先级"]
    RAG["RAG Agent<br/>检索 Runbook、知识和历史事故"]

    subgraph PARALLEL["并行调查"]
        SRE["SRE Agent<br/>分析指标、日志和服务关系"]
        Change["Change Agent<br/>关联近期发布和配置变更"]
    end

    RootCause["Root Cause<br/>汇总证据并判断可能根因"]
    Remediation["Remediation<br/>匹配 Runbook 并生成处置动作"]
    Report["Report Agent<br/>生成结构化事故报告"]
    Response["JSON 响应<br/>证据、根因、动作和报告"]

    Hybrid["Hybrid Retriever<br/>关键词与语义检索融合"]
    GraphRAG["GraphRAG<br/>扩展服务、变更和事故关系"]
    Runbooks[("Runbook YAML / JSON<br/>标准处置步骤")]
    Changes[("Change JSONL<br/>发布和配置变更")]
    NetworkX[("NetworkX 内存图<br/>事故关系图")]
    Evidence["Evidence Guardrails<br/>检查证据来源与引用"]

    API --> Validate
    Validate --> Triage
    Triage --> RAG
    RAG --> Hybrid
    RAG --> GraphRAG
    Hybrid ==> Runbooks
    GraphRAG ==> NetworkX
    RAG -.-> SRE
    RAG -.-> Change
    Change ==> Changes
    SRE -.->|"并行结果汇合"| RootCause
    Change -.->|"并行结果汇合"| RootCause
    RootCause --> Evidence
    Evidence --> Remediation
    Remediation ==> Runbooks
    Remediation --> Report
    Report --> Response
`,
  '05-runtime-storage': String.raw`
flowchart LR
    subgraph STARTUP["启动过程"]
        Start["启动命令<br/>app.run / Makefile / Windows 脚本"]
        Uvicorn["Uvicorn<br/>启动 FastAPI 进程"]
        Lifespan["FastAPI lifespan<br/>初始化与释放资源"]
        MilvusConnect["连接 Milvus<br/>加载或创建 biz collection"]
        PGConnect["连接 PostgreSQL<br/>初始化 LangGraph Saver"]
        InitServices["初始化服务<br/>AIOps 与 EnterpriseWorkflow"]
        Ready["应用可用<br/>监听 9900 端口"]
    end

    subgraph DATA["运行数据"]
        PG[("PostgreSQL<br/>持久化 AIOps 状态")]
        MV[("Milvus<br/>知识文档向量")]
        Files[("本地文件<br/>上传、Runbook、变更、策略、评测")]
        Memory[("进程内内存<br/>Chat MemorySaver、NetworkX")]
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
        OTel["OpenTelemetry Span<br/>已有埋点，未确认 exporter"]
    end

    Start --> Uvicorn
    Uvicorn --> Lifespan
    Lifespan --> MilvusConnect
    Lifespan --> PGConnect
    MilvusConnect --> InitServices
    PGConnect --> InitServices
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
    Tests -.->|"验证工作流与恢复能力"| InitServices
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
