---
tags: [knowledge, model-routing, config, cost]
---
# Model Routing Guide 🦞

_Last updated: 2026-04-26_

## Available DeepSeek Models (cheapest → most capable)

| Model ID | Cost (in/out per 1M) | Best for |
|----------|----------------------|----------|
| deepseek/deepseek-v4-flash | $0.14 / $0.28 | Vault ops, simple Q&A, routine commands, lookups |
| deepseek/deepseek-chat | $0.28 / $0.42 | Normal conversation, concept explanations, news summaries |
| deepseek/deepseek-reasoner | $0.28 / $0.42 | Strategy design, chart analysis, risk assessment, post-mortems |
| deepseek/deepseek-v4-pro | $1.74 / $3.48 | >500K token processing, production codegen, heavy analysis |

## Routing Decision Tree

```
Task received
├─ Simple vault read/write / status / lookup?       → v4-flash
├─ Answered in vault (retrieve first)?               → v4-flash
├─ Routine command / help?                           → v4-flash
├─ Normal conversation / explain concept?            → chat
├─ Market news summary (no deep reasoning)?          → chat
├─ Strategy design / backtest / complex analysis?    → reasoner
├─ Post-mortem / risk assessment?                    → reasoner
├─ Multi-timeframe concurrence analysis?             → reasoner
├─ >500K tokens or production codegen?               → v4-pro (log justification)
└─ Anything else:                                    → v4-flash (cheapest that works)
```

## Active Switching (Enforced)

I **must actively switch models** based on the task — not passively rely on fallbacks. The default is v4-flash, but I am responsible for evaluating each task and escalating when appropriate.

### How to switch
- **Same session:** Use `session_status` tool with `model="deepseek/deepseek-reasoner"` to override the current session
- **Sub-task / background:** Use `sessions_spawn` with explicit `model` for isolated reasoning work
- **Reset:** `session_status` with `model="default"` to return to v4-flash

### Rules
- Start cheap. Escalate only if task complexity demands it.
- **Evaluate every task** — do not default to v4-flash without thinking about whether it's the right model
- **Must inform user** when switching: "Switching to DeepSeek Reasoner for this analysis."
- **v4-pro requires a logged justification** in `05_Meta/api_costs.md` before use
- After completing heavy work on a stronger model, **reset back to v4-flash** to save costs
- Log every switch in `05_Meta/api_costs.md` (model used, task, cost estimate)

## Related

- Cost ledger: 05_Meta/api_costs.md
