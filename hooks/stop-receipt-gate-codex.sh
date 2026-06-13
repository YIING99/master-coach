#!/bin/bash
# 验收回执门禁 (Codex Stop hook 适配版) v1 — 传功强制执行层
# 与 Claude Code 版的差异:
#   1. 转录格式: Codex rollout-*.jsonl 用 event_msg/agent_message 与
#      response_item/message(role=assistant, output_text) 两种结构, 解析路径不同。
#   2. 防死循环: 除 stop_hook_active 外, 增加"同一条消息只拦一次"的本地状态守卫
#      (无法确认 Codex 是否回传 stop_hook_active, 双保险)。
#   3. stdin 没给 transcript_path 时, 兜底取 ~/.codex/sessions 最近 10 分钟内的
#      最新 rollout 文件。
# 原则: 任何一步解析失败都 exit 0 放行 (fail-open), 绝不误锁会话。

INPUT=$(cat)

STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
[ "$STOP_ACTIVE" = "true" ] && exit 0

TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)

if [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; then
  TRANSCRIPT=$(find "$HOME/.codex/sessions" -name 'rollout-*.jsonl' -type f -mmin -10 2>/dev/null -exec ls -t {} + | head -1)
fi
{ [ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ]; } && exit 0

# 最后一条 agent 最终答复: 优先 agent_message, 兜底 assistant/output_text
LAST=$(grep '"type":"agent_message"' "$TRANSCRIPT" | tail -1 | \
  jq -r '.payload.message // empty' 2>/dev/null)
if [ -z "$LAST" ]; then
  LAST=$(grep '"role":"assistant"' "$TRANSCRIPT" | grep '"output_text"' | tail -1 | \
    jq -r '[.payload.content[]? | select(.type=="output_text") | .text] | join("\n")' 2>/dev/null)
fi
[ -z "$LAST" ] && exit 0

# 同一条消息只拦一次 (防 Codex 不传 stop_hook_active 时死循环)
HASH=$(printf '%s' "$TRANSCRIPT:$LAST" | md5 2>/dev/null)
STATE="${TMPDIR:-/tmp}/.receipt-gate-codex-last"
if [ -n "$HASH" ] && [ -f "$STATE" ] && [ "$(cat "$STATE" 2>/dev/null)" = "$HASH" ]; then
  exit 0
fi

CLAIM='已修复|已完成|已搞定|搞定了|都正常|全部正常|没问题了|修复完成|部署完成|上线完成'
RECEIPT='验收回执|无需回执'

if echo "$LAST" | grep -qE "$CLAIM" && ! echo "$LAST" | grep -qE "$RECEIPT"; then
  [ -n "$HASH" ] && printf '%s' "$HASH" > "$STATE"
  cat <<'ENDJSON'
{"decision":"block","reason":"[回执门禁] 检测到完成性表述但缺少验收回执。按协议2: 输出『验收回执』——本任务类型门禁清单逐项标注 ✅(附具体证据)/❌/N-A(附理由), 缺证据的项不得标✅。若本任务确属无需回执的闲聊/问答, 写明『无需回执』+一句理由即可通过。"}
ENDJSON
fi
exit 0
