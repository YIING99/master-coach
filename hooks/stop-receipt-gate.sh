#!/bin/bash
# 验收回执门禁 (Stop hook, 拦截型) v1 — 传功强制执行层
# 机制: 模型宣布"完成/已修复"但没有输出验收回执时, 拒绝结束本轮,
#       强制模型补交回执。与注入型 hook 的区别: 这是 harness 在裁决, 不是模型在自律。
# 防死循环: stop_hook_active=true (本轮已被 block 过一次) 时直接放行。

INPUT=$(cat)

STOP_ACTIVE=$(echo "$INPUT" | jq -r '.stop_hook_active // false' 2>/dev/null)
[ "$STOP_ACTIVE" = "true" ] && exit 0

TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
[ -z "$TRANSCRIPT" ] || [ ! -f "$TRANSCRIPT" ] && exit 0

# 取最后一条 assistant 文本消息
LAST=$(grep '"type":"assistant"' "$TRANSCRIPT" | tail -1 | \
  jq -r '[.message.content[]? | select(.type=="text") | .text] | join("\n")' 2>/dev/null)
[ -z "$LAST" ] && exit 0

CLAIM='已修复|已完成|已搞定|搞定了|都正常|全部正常|没问题了|修复完成|部署完成|上线完成'
RECEIPT='验收回执|无需回执'

if echo "$LAST" | grep -qE "$CLAIM" && ! echo "$LAST" | grep -qE "$RECEIPT"; then
  cat <<'ENDJSON'
{"decision":"block","reason":"[回执门禁] 检测到完成性表述但缺少验收回执。按协议2: 输出『验收回执』——本任务类型门禁清单逐项标注 ✅(附具体证据)/❌/N-A(附理由), 缺证据的项不得标✅。若本任务确属无需回执的闲聊/问答, 写明『无需回执』+一句理由即可通过。"}
ENDJSON
  exit 0
fi
exit 0
