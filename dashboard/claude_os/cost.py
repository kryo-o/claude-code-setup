"""Token use, cost and cold-cache reloads of one session transcript.

Only usage, model and timestamp leave this module, never message text.
"""
import json
from datetime import datetime

from .pricing import WRITE_1H, WRITE_5M, rates

COLD_MIN = 10_000  # smaller writes are ordinary turns


def _ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def price(model, t, write_1h=0):
    """Estimated $ for token counts t on model, or None for a model with no known price."""
    r = rates(model)
    if not r:
        return None
    inp, out, read = r
    write = (t["cache_write"] - write_1h) * inp * WRITE_5M + write_1h * inp * WRITE_1H
    return (t["input"] * inp + t["output"] * out + write + t["cache_read"] * read) / 1e6


def session(path):
    msgs, seen, engine_cost = [], set(), None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            # Cheap prefilter: most lines are text or tool output.
            if '"usage"' not in line and '"cost-state"' not in line:
                continue
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if o.get("type") == "cost-state":
                engine_cost = o.get("totalCostUSD", engine_cost)
                continue
            m = o.get("message") or {}
            if o.get("type") != "assistant" or not m.get("usage") or m.get("id") in seen:
                continue
            seen.add(m.get("id"))
            u = m["usage"]
            msgs.append({
                "ts": o.get("timestamp"), "model": m.get("model"),
                "input": u.get("input_tokens", 0), "output": u.get("output_tokens", 0),
                "cache_write": u.get("cache_creation_input_tokens", 0),
                "cache_read": u.get("cache_read_input_tokens", 0),
                "write_1h": (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0),
            })

    keys = ("input", "output", "cache_write", "cache_read")
    tokens = {k: sum(m[k] for m in msgs) for k in keys}
    est = 0.0
    for m in msgs:
        p = price(m["model"], m, m["write_1h"])
        est = None if p is None or est is None else est + p

    # A cold reload: after the first message, the conversation is written to cache again. The system
    # prompt often stays cached, so it shows as a large write that outweighs the read.
    cold = {"count": 0, "tokens": 0, "usd": 0.0, "max_idle_min": 0}
    for prev, m in zip(msgs, msgs[1:]):
        if m["cache_write"] >= COLD_MIN and m["cache_write"] > m["cache_read"]:
            cold["count"] += 1
            cold["tokens"] += m["cache_write"]
            r = rates(m["model"])
            if r:
                cold["usd"] += ((m["cache_write"] - m["write_1h"]) * WRITE_5M + m["write_1h"] * WRITE_1H) * r[0] / 1e6
            if prev["ts"] and m["ts"]:
                idle = int((_ts(m["ts"]) - _ts(prev["ts"])).total_seconds() // 60)
                cold["max_idle_min"] = max(cold["max_idle_min"], idle)

    return {
        "session": path.stem,
        "messages": len(msgs),
        "first": msgs[0]["ts"] if msgs else None,
        "last": msgs[-1]["ts"] if msgs else None,
        "models": sorted({m["model"] for m in msgs if m["model"]}),
        "tokens": tokens,
        "cost_usd": engine_cost if engine_cost is not None else est,
        "estimated": engine_cost is None,
        "cold_reloads": cold,
    }
