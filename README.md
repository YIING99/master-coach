# 传功 Master Coach

> 用最强模型给你的日常 AI 定标准。它走了，标准归你。
> Let the strongest model write acceptance standards for your everyday AI.

强模型把验证内化在权重里，普通模型需要把验证外置在结构里。本仓库是一套完整的"外置结构"工具包：

| 资产 | 作用 | 适用人群 |
|------|------|---------|
| [SKILL.md](SKILL.md) | 传功 Skill：失败案例→验收标准的五步复诊流程 | Claude Code 用户 |
| [templates/coach-prompt.md](templates/coach-prompt.md) | 传功 Prompt 模板，任何强模型可用 | 所有人 |
| [templates/chat-guardrails.md](templates/chat-guardrails.md) | Chat 门禁卡 8 条，贴 Project instructions 即生效 | 网页版用户 |
| [templates/harness-sample.md](templates/harness-sample.md) | 验收门禁 CLAUDE.md 样例骨架 | Claude Code / Codex |
| [hooks/stop-receipt-gate.sh](hooks/stop-receipt-gate.sh) | 拦截型回执门禁：宣布完成但无回执 → 本轮结束不了 | Claude Code 用户 |
| [agents/acceptance-officer.md](agents/acceptance-officer.md) | 验收官 subagent：强模型只做裁决不做执行 | Claude Code 用户 |
| [scripts/](scripts/) | 对话日志挖掘脚本：统计你的"纠错率"，挖失败案例 | 所有人 |

## 30 秒安装（Skill）

```bash
git clone https://github.com/YIING99/master-coach.git ~/.claude/skills/master-coach
```

重启 Claude Code，对话中说「传功」即触发。

## 回执门禁启用

```bash
chmod +x ~/.claude/skills/master-coach/hooks/stop-receipt-gate.sh
```

在 `~/.claude/settings.json` 的 hooks 里追加：

```json
{ "hooks": { "Stop": [ { "hooks": [
  { "type": "command", "command": "~/.claude/skills/master-coach/hooks/stop-receipt-gate.sh" } ] } ] } }
```

## 设计哲学

1. **可靠性 = 知识 × 执行倾向。** 知识可提炼（写成标准），执行倾向提炼不走（在权重里），但可以被结构替代（hook / 独立验收者）。
2. **执行流便宜化，裁决点贵族化。** 贵模型只出现在计划评审、完成验收、月度传功三个裁决点。
3. **标准负责语义，门禁负责机械。** 验收回执设计成固定格式，就是为了让 30 行 bash 能检测它。

姊妹项目：[expert-pulse（把脉）](https://github.com/YIING99/expert-pulse) — 决策多视角评审 Skill。

MIT License ｜ 公众号「持续进化营」
