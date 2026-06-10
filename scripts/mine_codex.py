#!/usr/bin/env python3
"""挖掘 Codex 会话日志中的失败信号（与 mine_failures.py 同方法，适配 Codex rollout 格式）。

Codex rollout jsonl 用户消息形如:
{"timestamp":...,"type":"response_item","payload":{"type":"message","role":"user",
 "content":[{"type":"input_text","text":"..."}]}}
"""
import json
import re
from pathlib import Path
from collections import defaultdict

SESSIONS = Path.home() / ".codex" / "sessions"

TRIGGERS = [
    "你确定", "真的吗", "又错了", "你又", "还是不行", "还是报错", "怎么还是",
    "别瞎说", "胡扯", "认真点", "别偷懒", "别糊弄", "别敷衍", "再想想",
    "不对", "错了", "没修复", "没解决", "白改", "倒退", "越改越",
    "长点记性", "之前说过", "我说过", "重新来", "推倒重来", "把脉",
]

# 系统注入的伪用户消息，需排除
NOISE_PREFIXES = ("<environment_context>", "<turn_context>", "<user_instructions>",
                  "# AGENTS.md", "<ENVIRONMENT", "[Request interrupted")

results = []
for f in sorted(SESSIONS.rglob("*.jsonl")):
    stats = {"file": str(f), "user_turns": 0, "trigger_hits": 0,
             "first_ts": "", "last_ts": "", "cwd": "",
             "samples": [], "trigger_counts": defaultdict(int)}
    try:
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                # 快速预过滤，避免对每行大 JSON 做完整解析
                if '"session_meta"' in line and not stats["cwd"]:
                    try:
                        meta = json.loads(line)
                        stats["cwd"] = meta.get("payload", {}).get("cwd", "")
                    except json.JSONDecodeError:
                        pass
                    continue
                if '"role":"user"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = obj.get("payload") or {}
                if payload.get("type") != "message" or payload.get("role") != "user":
                    continue
                texts = [c.get("text", "") for c in payload.get("content", [])
                         if isinstance(c, dict) and c.get("type") == "input_text"]
                text = "\n".join(t for t in texts if t).strip()
                if not text or text.startswith(NOISE_PREFIXES):
                    continue
                ts = obj.get("timestamp", "")
                stats["user_turns"] += 1
                if not stats["first_ts"]:
                    stats["first_ts"] = ts
                stats["last_ts"] = ts
                hits = [t for t in TRIGGERS if t in text]
                if hits:
                    stats["trigger_hits"] += 1
                    for t in hits:
                        stats["trigger_counts"][t] += 1
                    if len(stats["samples"]) < 4:
                        snippet = re.sub(r"\s+", " ", text)[:120]
                        stats["samples"].append((ts[:10], snippet))
    except OSError:
        continue
    if stats["user_turns"] > 0:
        stats["signal"] = stats["trigger_hits"]
        stats["density"] = stats["signal"] / stats["user_turns"]
        results.append(stats)

results.sort(key=lambda s: s["signal"], reverse=True)

total_turns = sum(s["user_turns"] for s in results)
total_trig = sum(s["trigger_hits"] for s in results)
print(f"会话数: {len(results)} | 真实用户消息: {total_turns} | 触发词命中消息数: {total_trig}")
print("=" * 80)

all_triggers = defaultdict(int)
for s in results:
    for t, c in s["trigger_counts"].items():
        all_triggers[t] += c
print("触发词总榜:", dict(sorted(all_triggers.items(), key=lambda x: -x[1])))
print("=" * 80)

for s in results[:12]:
    if s["signal"] == 0:
        break
    print(f"\n### {s['cwd'] or '(unknown cwd)'}  [{s['first_ts'][:10]} ~ {s['last_ts'][:10]}]")
    print(f"    文件: {s['file']}")
    print(f"    用户消息 {s['user_turns']} | 触发词消息 {s['trigger_hits']} | 密度 {s['density']:.0%}")
    print(f"    触发词: {dict(s['trigger_counts'])}")
    for ts, snip in s["samples"]:
        print(f"    [{ts}] {snip}")
