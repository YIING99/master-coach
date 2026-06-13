#!/bin/bash
# 验收回执门禁 · 通用版（Claude Code + Codex 双格式自适应）
# 行为: 最后一条 assistant 消息宣布"完成"但无验收回执 → decision:block 拒绝结束
# 安全原则: 任何无法识别的输入一律放行(exit 0)，绝不误伤
# 校准: 首次运行会把 stdin 采样到 ~/.cache/receipt-gate/stdin-sample.json 供适配核对

INPUT=$(cat)

# 采样(仅一次,便于核对宿主 harness 的真实输入格式)
SAMPLE_DIR="$HOME/.cache/receipt-gate"
if [ ! -f "$SAMPLE_DIR/stdin-sample.json" ]; then
  mkdir -p "$SAMPLE_DIR" && printf '%s' "$INPUT" | head -c 4000 > "$SAMPLE_DIR/stdin-sample.json" 2>/dev/null
fi

STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
[ "$STOP_ACTIVE" = "true" ] && exit 0

TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
[ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ] && exit 0

# 取最后一条 assistant 文本 —— 自动探测两种格式
# Claude Code: {"type":"assistant","message":{"content":[{"type":"text","text":...}]}}
# Codex:       {"type":"response_item","payload":{"type":"message","role":"assistant",
#               "content":[{"type":"output_text","text":...}]}}
LAST=$(grep '"type":"assistant"' "$TRANSCRIPT" | tail -1 | \
  jq -r '[.message.content[]? | select(.type=="text") | .text] | join("\n")' 2>/dev/null)
if [ -z "$LAST" ]; then
  LAST=$(grep '"type":"agent_message"' "$TRANSCRIPT" | tail -1 | \
    jq -r '.payload.message // empty' 2>/dev/null)
fi
if [ -z "$LAST" ]; then
  LAST=$(grep '"role":"assistant"' "$TRANSCRIPT" | tail -1 | \
    jq -r '[.payload.content[]? | select(.type=="output_text") | .text] | join("\n")' 2>/dev/null)
fi
[ -z "$LAST" ] && exit 0

# 同一条消息只拦一次(宿主不回传 stop_hook_active 时的防死循环双保险)
HASH=$(printf '%s' "$TRANSCRIPT:$LAST" | md5 2>/dev/null || printf '%s' "$TRANSCRIPT:$LAST" | md5sum | cut -d' ' -f1)
STATE="${TMPDIR:-/tmp}/.receipt-gate-last"
if [ -n "$HASH" ] && [ -f "$STATE" ] && [ "$(cat "$STATE" 2>/dev/null)" = "$HASH" ]; then
  exit 0
fi

CLAIM='已修复|已完成|已搞定|搞定了|都正常|全部正常|没问题了|修复完成|部署完成|上线完成'
RECEIPT='验收回执|门禁回执|无需回执'

if echo "$LAST" | grep -qE "$CLAIM" && ! echo "$LAST" | grep -qE "$RECEIPT"; then
  [ -n "$HASH" ] && printf '%s' "$HASH" > "$STATE"
  cat <<'ENDJSON'
{"decision":"block","reason":"[回执门禁] 检测到完成性表述但缺少验收回执。按协议2: 输出『验收回执』——本任务类型门禁清单逐项标注 ✅(附具体证据)/❌/N-A(附理由), 缺证据的项不得标✅。若本任务确属无需回执的闲聊/问答, 写明『无需回执』+一句理由即可通过。"}
ENDJSON
  exit 0
fi
exit 0
