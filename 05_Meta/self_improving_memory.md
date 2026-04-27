---
tags: [meta, self-improving, learning, hot]
---
# Memory (HOT Tier) 🦞

_Last updated: 2026-04-27_
_Compiled from first full day of operation_

## Preferences
- Shawn prefers sharp, analytical, zero-fluff communication
- Use DeepSeek v4-flash for conversation; DeepSeek Reasoner for complex analysis
- HF free models ONLY for prediction pipeline (dual-API enforcement)
- GitHub push protection scans for secrets — never hardcode tokens in scripts
- n8n workflows must use proper UUID node IDs (not string aliases) or import fails
- WriteFile node type is not available in n8n 2.x — use noOp instead
- Dashboard should show: target date, reasoning breakdown, service health, control buttons
- Always log corrections and patterns to HOT memory immediately

## Patterns
- **HF Router fix:** Use `https://router.huggingface.co/hf-inference/models/` not `api-inference.huggingface.co/models/`
- **yfinance MultiIndex:** Single ticker downloads return MultiIndex columns — use `.xs('Close', axis=1, level=0).squeeze()`
- **n8n import format:** Requires wrapping array `[...]`, UUIDs on all node IDs, `typeVersion` on every node, no `writeFile`
- **Prediction scoring:** Weighted combo (sentiment 35% + returns 30% + RSI 20% + volume 15%)
- **Dashboard API proxy:** Dashboard server on 5500 proxies to prediction server 18888 and n8n 5678
- **n8n webhook trigger:** `POST /webhook/run-pipeline` needs NO auth key — use for dashboard control buttons
- **Reasoning breakdown:** Return per-stock rsi, volume_ratio, sentiment, score, return_5d for detailed logs

## Rules
- Before any git push: verify no API keys/tokens are in the staged files
- Unicode chars (─, 🦞, ✅) cause cp1252 errors — use `-X utf8` flag on Python or ASCII replacements
- Services can die after session ends — use `Start-Process -WindowStyle Hidden` for persistence
- HOT memory must be populated with actionable patterns, not left empty
- **Capital preservation first — never lose principal**
