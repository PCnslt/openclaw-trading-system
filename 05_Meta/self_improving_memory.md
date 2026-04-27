---
tags: [meta, self-improving, learning, hot]
---
# Memory (HOT Tier) 🦞

_Last updated: 2026-04-26_
_Compiled from first full day of operation_

## Preferences
- Shawn prefers sharp, analytical, zero-fluff communication
- Use DeepSeek v4-flash for conversation; DeepSeek Reasoner for complex analysis
- HF free models ONLY for prediction pipeline (dual-API enforcement)
- GitHub push protection scans for secrets — never hardcode tokens in scripts
- n8n workflows must use proper UUID node IDs (not string aliases) or import fails
- WriteFile node type is not available in n8n 2.x — use noOp instead

## Patterns
- **HF Router fix:** Use `https://router.huggingface.co/hf-inference/models/` not `api-inference.huggingface.co/models/` (old endpoint returns 404)
- **yfinance MultiIndex:** Single ticker downloads return MultiIndex columns — must use `.xs('Close', axis=1, level=0).squeeze()` to extract Series
- **n8n import format:** Requires wrapping array `[...]`, UUIDs on all node IDs, `typeVersion` on every node, no `writeFile` node type
- **Prediction scoring:** Weighted combo (sentiment 35% + returns 30% + RSI 20% + volume 15%) best matches Yahoo gainers
- **Yahoo scraping:** Change% is embedded in price column cell `60.32+26.07(+76.12%)` — use regex `\((\+?\d+\.?\d*)%\)` to extract

## Rules
- Before any git push: verify no API keys/tokens are in the staged files
- Unicode chars (─, 🦞, ✅) cause cp1252 errors — use `-X utf8` flag on Python or ASCII replacements
- n8n exec tool keeps getting SIGKILL on large npm installs — use `background: true` and long timeout
- Kelly criterion: session context grows fast — store to MEMORY.md before compaction
- **Capital preservation first — never lose principal**
