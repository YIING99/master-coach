#!/usr/bin/env python3
"""挖掘 claude.ai 导出数据（conversations.json）中的失败信号。

格式：[{uuid, name, summary, created_at, chat_messages:[{text, sender, created_at, ...}]}]
"""
import json
import re
import sys
from collections import defaultdict

EXPORT = sys.argv[1] if len(sys.argv) > 1 else "conversations.json"

TRIGGERS = [
    "瞎搞", "瞎编", "胡编", "编造", "混淆", "张冠李戴",
    "你确定", "真的吗", "又错了", "你又", "还是不行", "怎么还是",
    "别瞎说", "胡扯", "认真点", "别偷懒", "别糊弄", "别敷衍", "再想想",
    "不对", "错了", "没修复", "没解决", "长点记性", "之前说过", "我说过",
    "把脉", "验真", "追因",
]

with open(EXPORT, encoding="utf-8") as f:
    data = json.load(f)

results = []
month_count = defaultdict(int)
for conv in data:
    created = (conv.get("created_at") or "")[:10]
    month_count[created[:7]] += 1
    stats = {"name": (conv.get("name") or "(无标题)")[:40], "uuid": conv.get("uuid", ""),
             "date": created, "user_turns": 0, "trigger_hits": 0,
             "samples": [], "trigger_counts": defaultdict(int)}
    for msg in conv.get("chat_messages", []):
        if msg.get("sender") != "human":
            continue
        text = (msg.get("text") or "").strip()
        if not text:
            continue
        stats["user_turns"] += 1
        hits = [t for t in TRIGGERS if t in text]
        if hits:
            stats["trigger_hits"] += 1
            for t in hits:
                stats["trigger_counts"][t] += 1
            if len(stats["samples"]) < 3:
                snippet = re.sub(r"\s+", " ", text)[:130]
                stats["samples"].append((msg.get("created_at", "")[:10], snippet))
    if stats["user_turns"] > 0:
        stats["density"] = stats["trigger_hits"] / stats["user_turns"]
        results.append(stats)

results.sort(key=lambda s: s["trigger_hits"], reverse=True)

total_turns = sum(s["user_turns"] for s in results)
total_trig = sum(s["trigger_hits"] for s in results)
print(f"对话数: {len(results)} | 用户消息总数: {total_turns} | 触发词命中消息数: {total_trig} "
      f"| 命中率: {total_trig/total_turns:.1%}")
print("按月分布:", dict(sorted(month_count.items())))
print("=" * 80)

all_triggers = defaultdict(int)
for s in results:
    for t, c in s["trigger_counts"].items():
        all_triggers[t] += c
print("触发词总榜:", dict(sorted(all_triggers.items(), key=lambda x: -x[1])))
print("=" * 80)

for s in results[:18]:
    if s["trigger_hits"] == 0:
        break
    print(f"\n### [{s['date']}] {s['name']}")
    print(f"    用户消息 {s['user_turns']} | 触发词消息 {s['trigger_hits']} | 密度 {s['density']:.0%}"
          f" | {dict(s['trigger_counts'])}")
    for ts, snip in s["samples"]:
        print(f"    [{ts}] {snip}")
