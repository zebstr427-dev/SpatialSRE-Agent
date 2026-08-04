# Lesson Protocol

Use this protocol for every interaction. Keep headings compact and teaching content concrete.

## Contents

- [1. Route The Learner Message](#1-route-the-learner-message)
- [2. Lesson Card](#2-lesson-card)
- [3. Whole-Lesson Packet](#3-whole-lesson-packet)
- [4. Review Rubric](#4-review-rubric)
- [5. Debugging Protocol](#5-debugging-protocol)
- [6. Completion Evidence](#6-completion-evidence)
- [7. Lesson Close](#7-lesson-close)

## 1. Route The Learner Message

Choose exactly one route after inspecting repository evidence:

| Learner message | Route | Required action |
| --- | --- | --- |
| "继续"、"下一课"、fresh invocation | Orient/Instruct | Establish current state, select the first incomplete roadmap item, give the complete remaining lesson packet. |
| "完成了"、"改好了" | Review | Read files and diff, verify returned command evidence, classify feedback, then advance or correct. |
| Expected RED output from the instructed test | Review -> GREEN | Verify the failure matches the intended missing behavior, accept the RED slice, then give the complete remaining packet beginning with the minimal GREEN checkpoint. |
| Error, traceback, failed test, failed startup | Debug | Inspect full evidence, diagnose cause, give the smallest correction, require rerun. |
| "能不能总结" | Gate | Verify all gates; document only if accepted, otherwise list missing proof. |
| Design or interview question | Explain | Answer using current code, then return to the same lesson state without advancing. |

Do not infer acceptance from confidence or prose. Repository and runtime evidence control progression.

## 2. Lesson Card

Use this shape when opening a lesson:

```markdown
**第 N 课：标题**

企业问题：...

所在位置：`upstream -> current layer -> downstream`

本课交付：...

预计涉及：`path/a.py`、`tests/...`

验收证据：...

秋招重点：概念 A、概念 B、概念 C
```

Keep the card focused. Explain dependencies on previous lessons where they affect design.

At lesson start and meaningful resumes, add a feature map before the complete lesson packet:

```markdown
| 状态 | 功能点 | 可验证结果 |
| --- | --- | --- |
| 已完成 | ... | ... |
| 当前 | ... | ... |
| 待完成 | ... | ... |
```

A lesson normally contains 3-6 related feature points. Mark only repository-proven work as complete; later checkpoints remain pending even though their implementation code is visible in the packet. After review, update the map from actual evidence rather than the learner's confidence.

When the lesson introduces a central concept, follow the card with a compact teaching bridge:

1. `直观理解`：用短类比或具体场景建立心智模型。
2. `精确定义`：说明真实技术机制、契约和失败边界。
3. `项目映射`：落到当前仓库的字段、函数、测试或数据流。

State where the analogy stops matching if it could conceal an important boundary. Omit this bridge for familiar or purely mechanical work.

## 3. Whole-Lesson Packet

Give every remaining lesson feature point in one response. Organize it as numbered checkpoints that the learner executes strictly in order. Each checkpoint contains one to three operations that together deliver or prove one small capability. Start every checkpoint with this frame:

```markdown
**检查点 X：一句话描述单一行为**

项目位置：说明架构层，以及 `上游 -> 本次改动 -> 下游` 数据流。

大白话导入：先说明这段功能替项目做什么，以及没有它时用户或系统会遇到什么问题。按具备基础 Python 语法、但计算机基础尚不完整的学习者来讲。

现有代码如何运行：说明入口、调用时机、主要输入输出，以及缺失行为在哪个边界出现。

代码路线图：在展示代码前，按 `输入 -> 主要处理 -> 输出/异常` 预告执行过程，并介绍即将出现的关键类、函数、参数和字段。新术语第一次出现时先用大白话定义。

讲解深度：标明本段是 `重点讲解` 还是 `整体说明`。核心契约、算法、状态变化、失败语义、安全边界和关键取舍采用重点讲解；导入、样板字段、重复管道和机械命令只交代整体用途、系统位置及非显然限制。

完成后：说明系统新获得的行为，或本轮 RED 将精确证明的缺口。

项目亮点（必要时）：只写具体的生产、设计、测试或面试价值；没有真实亮点则省略。
```

Then give independently checkable operations:

````markdown
**操作 1/3：动词 + 目标**

这段代码是干什么的：用大白话说明整段代码的产品作用，以及不增加它会缺少什么能力。

它会怎样运行：说明谁调用它、输入是什么、内部做哪几件关键事情、输出或异常是什么，以及输出接下来交给谁。

先认识这些名字：只列本段真正关键的新类、函数、参数或字段，并给出初学者能复述的定义。

文件：`absolute/or/project-relative/path.py`

当前状态：说明目标代码是未修改、部分完成还是已经完整存在；已经正确时明确跳过。

作用域与参考行号：`ClassName.method / function / nested branch`，当前约第 X-Y 行；行号仅供导航，以下唯一锚点才是编辑依据。

唯一锚点：逐字复制当前文件中的独特代码。说明它应只匹配一次；匹配零次或多次时立即停止并返回附近代码。

动作与边界：插入时明确写在锚点 `之前/之后`，替换时明确包含的首行和末行。相似代码出现多次时，写明 `if/except/success return` 等控制流分支。

```python
# Complete code for only this operation
```

修改后局部结构：展示锚点和新代码组合后的短代码块，使缩进、顺序和所属分支可核对。

代码讲评：重点代码在代码块之后解释关键语句组分别承担什么职责；评价它做得好的地方、适合当前项目的原因、真实取舍，以及明确没有解决的边界。非重点代码不逐行讲，只总结整块作用、系统位置和必要限制。测试代码还要说明 `准备场景 -> 执行动作 -> 观察结果`，以及断言为什么足以证明目标行为。

设计与秋招点：在已经讲懂代码的基础上，再总结接口、边界、取舍，以及面试时如何表述。

请你执行：

```powershell
# One focused verification command
```

预期：给出可验证的摘要，不伪造精确动态值。

失败时返回：完整命令、完整 traceback/输出，以及你实际改动的文件。
````

Use exact code that matches current imports, types, versions, naming, and test conventions. Avoid ellipses inside code the learner must enter. Do not bundle unrelated cleanup.

After each edit, require the learner to reread the qualified scope or inspect a scoped diff. The target change must occur exactly once. If the current file already contains the requested code, skip that edit rather than adding it again.

For a purely mechanical verification command, keep only its purpose, exact command, expected result, and stop-on-mismatch evidence. Do not manufacture a three-layer explanation or interview story for routine checks.

All operations in a checkpoint must serve the stated mini-feature. Prefer a test/edit/verification slice with one observable acceptance result. Move unrelated formatting, cleanup, documentation, and later behavior to separate checkpoints.

Provide complete learner-ready code for every edit. Before the block, explain its whole job in plain language and where it sits in the system. For important code, also teach its input -> work -> output path, callers and consumers, important symbols, and then explain and evaluate the key lines or groups after the block, focusing on execution timing, data ownership, failure semantics, tradeoffs, and why it fits. For unimportant plumbing, keep the explanation to the overall job, system location, and non-obvious constraints. Apply `准备场景 -> 执行动作 -> 观察结果 -> 证明范围` to behavior-defining tests. Do not narrate obvious syntax line by line.

At a key learning point, put the same `直观理解 -> 精确定义 -> 项目映射` bridge before the edit or command. Keep it brief and do not repeat it once the concept is established.

For every RED checkpoint, place its complete GREEN checkpoint later in the same response, but state explicitly: `先运行 RED；只有失败原因与预期一致，才执行紧随其后的 GREEN。` After every verification command, state: `如果结果与预期不同，立即停止，不执行后续检查点，并返回第一处差异的完整输出。`

End the packet with: `请按顺序完成整课；全部符合预期时一次性返回验收证据，任一步异常时只返回第一处失败。`

## 4. Review Rubric

Inspect before writing feedback:

- The exact changed hunks and surrounding implementation.
- Added or changed tests and whether assertions prove behavior rather than execution.
- User-provided command output; inspect the integrated terminal when available.
- Serialization, async lifecycle, error handling, idempotency, security, observability, compatibility, and cleanup boundaries relevant to this checkpoint.

Respond with:

```markdown
**阻塞问题**

- 无

**应改进问题**

- 无

**已达标点**

- `file:symbol` 已证明 ...
```

When blockers exist, follow with a corrective checkpoint. When no blockers exist, state which gate passed, what project capability the mini-feature added, what it still does not guarantee, and then give a concise interview-ready explanation using `场景 -> 风险 -> 方案 -> 验证 -> 边界`. Update the feature map before giving the remaining lesson packet. Do not repeat already accepted code.

## 5. Debugging Protocol

1. Reproduce mentally from the exact command and traceback; inspect code and dependency versions.
2. Name the failing boundary: syntax/import, unit contract, async lifecycle, external dependency, configuration, network, persistence, or runtime behavior.
3. State one evidence-backed root cause. Label alternatives as hypotheses and say how to distinguish them.
4. For a non-obvious root cause, teach it as `直观理解 -> 精确定义 -> 项目映射`, including the analogy's limit when relevant.
5. Give the smallest exact correction and rerun the same failing command before broader regression.

Do not hide failures with broad exception handling, skipped tests, weakened assertions, fake mocks, or silent fallbacks unless the explicit product contract requires that behavior.

## 6. Completion Evidence

Collect or inspect:

- Focused test command and pass summary.
- Relevant non-integration regression command and pass summary.
- Integration test when the lesson crosses a real infrastructure boundary.
- Ruff/type/compile result for changed code.
- Startup command, health response, target workflow response, and relevant failure/boundary response.
- `git diff --check`, lesson diff summary, and secret/unrelated-change check.

Use actual results in documentation. Record an encountered problem only when it occurred; do not manufacture a polished debugging story.

## 7. Lesson Close

After documentation is written, provide:

- One-paragraph outcome tied to enterprise behavior.
- Three to five high-value autumn-recruiting takeaways.
- One interview question for the learner to answer in their own words next time.
- Exact suggested files to stage and one Conventional Commit message.
- The next roadmap lesson title, without giving its implementation early.
