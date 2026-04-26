---
tags: [meta, cost, model-routing, finance]
---
# API Cost Ledger 🦞

Tracks every model API call for cost awareness. Updated per-call.

## Model Pricing (USD per 1M tokens)

| Model | Input | Output | Notes |
|-------|-------|--------|-------|
| deepseek/deepseek-v4-flash | 0.14 | 0.28 | Default: simple Q&A, vault ops, routine |
| deepseek/deepseek-chat | 0.28 | 0.42 | General conversation, moderate reasoning |
| deepseek/deepseek-reasoner | 0.28 | 0.42 | Complex analysis, strategy design, backtesting |
| deepseek/deepseek-v4-pro | 1.74 | 3.48 | Heavy analysis, large codegen, >500K tokens |

## Routing Rules

1. **Always prefer cheapest model that can reliably do the job.**
2. v4-flash for: vault reads/writes, answered questions, simple lookups, routine commands.
3. deepseek-chat for: normal convo, trading concept explanations, market news summaries.
4. deepseek-reasoner for: strategy dev, complex chart analysis, risk assessment, post-mortems.
5. v4-pro **only** when: >500K tokens needed, production codegen, or cheaper models proven to fail.
6. **v4-pro requires justification** logged in this file before use.
7. Always inform user when switching to a stronger model.

## Cost Log

| Timestamp | Model | Input tokens | Output tokens | Input cost | Output cost | Total cost | Task |
|-----------|-------|-------------|--------------|------------|-------------|------------|------|
| 2026-04-26 14:50 | deepseek-v4-flash | — | — | — | — | — | Model routing config setup |
| 2026-04-26 15:24 | deepseek-v4-flash | — | — | — | — | — | Active model switching enforcement added — fallback order fixed to cheapest-first |
