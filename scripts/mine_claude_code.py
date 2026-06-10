#!/usr/bin/env python3
"""挖掘 Claude Code 历史会话中的失败信号 — 复刻 AMD 工程师 issue #42796 的方法。

扫描 ~/.claude/projects/**/*.jsonl，统计每个会话中：
- 用户打断次数 ([Request interrupted by user])
- 质疑/纠错触发词命中（你确定/又错了/还是不行/...）
- 用户消息总数（计算失败信号密度）
输出按信号密度排序的会话清单 + 命中语句样本。
"""
import json
import re
from pathlib import Path
from collections import defaultdict

PROJECTS = Path.home() / ".claude" / "projects"

TRIGGERS = [
    "你确定", "真的吗", "又错了", "你又", "还是不行", "还是报错", "怎么还是",
    "别瞎说", "胡扯", "认真点", "别偷懒", "别糊弄", "别敷衍", "再想想",
    "不对", "错了", "没修复", "没解决", "白改", "倒退", "越改越",
    "长点记性", "之前说过", "我说过", "重新来", "推倒重来",
]
INTERRUPT = "[Request interrupted by user"

def user_texts(line: str):
    """从 jsonl 行提取真实用户输入文本（排除 tool_result 等系统回填）。"""
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return
    if obj.get("type") != "user":
        return
    msg = obj.get("message") or {}
    content = msg.get("content")
    ts = obj.get("timestamp", "")
    if isinstance(content, str):
        yield ts, content
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                yield ts, item.get("text", "")

results = []
for f in sorted(PROJECTS.rglob("*.jsonl")):
    stats = {"file": str(f), "project": f.parent.name, "user_turns": 0,
             "interrupts": 0, "trigger_hits": 0, "first_ts": "", "last_ts": "",
             "samples": [], "trigger_counts": defaultdict(int)}
    try:
        with open(f, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                for ts, text in user_texts(line) or []:
                    if not text.strip():
                        continue
                    stats["user_turns"] += 1
                    if not stats["first_ts"]:
                        stats["first_ts"] = ts
                    stats["last_ts"] = ts
                    if INTERRUPT in text:
                        stats["interrupts"] += 1
                        continue
                    hits = [t for t in TRIGGERS if t in text]
                    if hits:
                        stats["trigger_hits"] += 1
                        for t in hits:
                            stats["trigger_counts"][t] += 1
                        if len(stats["samples"]) < 5:
                            snippet = re.sub(r"\s+", " ", text)[:160]
                            stats["samples"].append((ts[:10], snippet))
    except OSError:
        continue
    if stats["user_turns"] > 0:
        stats["signal"] = stats["interrupts"] + stats["trigger_hits"]
        stats["density"] = stats["signal"] / stats["user_turns"]
        results.append(stats)

results.sort(key=lambda s: s["signal"], reverse=True)

total_turns = sum(s["user_turns"] for s in results)
total_int = sum(s["interrupts"] for s in results)
total_trig = sum(s["trigger_hits"] for s in results)
print(f"会话数: {len(results)} | 用户消息总数: {total_turns} | "
      f"打断: {total_int} | 触发词命中消息数: {total_trig}")
print("=" * 80)

all_triggers = defaultdict(int)
for s in results:
    for t, c in s["trigger_counts"].items():
        all_triggers[t] += c
print("触发词总榜:", dict(sorted(all_triggers.items(), key=lambda x: -x[1])))
print("=" * 80)

for s in results[:15]:
    if s["signal"] == 0:
        break
    print(f"\n### {s['project']}  [{s['first_ts'][:10]} ~ {s['last_ts'][:10]}]")
    print(f"    文件: {s['file']}")
    print(f"    用户消息 {s['user_turns']} | 打断 {s['interrupts']} | "
          f"触发词消息 {s['trigger_hits']} | 信号密度 {s['density']:.0%}")
    print(f"    触发词: {dict(s['trigger_counts'])}")
    for ts, snip in s["samples"]:
        print(f"    [{ts}] {snip}")
