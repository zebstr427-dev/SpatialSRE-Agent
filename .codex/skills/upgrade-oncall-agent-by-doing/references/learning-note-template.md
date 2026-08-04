# Learning Note Template

Use this template only after the lesson passes every applicable gate. Match established Chinese terminology and numbering in `docs/learning`; omit sections that genuinely do not apply.

```markdown
# 第 NN 课：<可验证的能力标题>

完成日期：YYYY-MM-DD

对应范围：`<建议提交信息或 roadmap item>`

## 企业问题

说明旧实现的具体风险、生产场景和本课边界。不要泛泛描述“提升性能”或“更加企业级”。

## 本课目标与完成结果

- 目标：...
- 实际完成：...
- 明确未覆盖：...

## 设计与实现

说明关键数据结构、接口、控制流和所有权。引用少量必要代码或结构图，不复制整份实现。

## 为什么这样设计

记录真实取舍、替代方案及未选择原因，并说明不提供哪些保证。

## 验证证据

```powershell
# 实际执行过的命令
```

实际结果：`N passed`、HTTP 状态、关键响应字段或日志证据。不得填写未执行的预期结果。

## 排错记录

仅记录本课真实发生的问题：现象、根因、修复、如何提前发现。没有真实问题时写“本课未发生需要记录的排错事件”。

## 常见错误

### <容易出现的实现错误>

说明识别方式和正确边界。常见错误可以来自代码审查，即使本课未实际发生，但不得写成已发生事件。

## 秋招知识点

- <知识点>：结合本项目说明，而不是背定义。
- <知识点>：说明生产风险与工程措施。
- <知识点>：说明测试如何证明，及仍不能证明什么。

## 面试问答

**问：<围绕设计取舍的问题>**

答：使用“场景 -> 风险 -> 方案 -> 验证 -> 边界”的结构。

**问：<围绕失败语义或测试的问题>**

答：基于本课真实实现回答。

## 下一课衔接

说明当前能力为严格路线中的下一项提供了什么前置条件，不提前声称下一项已实现。
```

After creating the note:

1. Add one ordered link to `docs/learning/README.md`.
2. Update aggregate verification counts only from fresh command output.
3. Preserve existing uncommitted README content and line endings where practical.
4. Read both files with explicit UTF-8 and inspect `git diff --check`.
5. Never include credentials, private endpoints, full sensitive tool arguments, or raw production data.
