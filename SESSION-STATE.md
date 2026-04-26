---
tags: [memory, hot-ram, wal-protocol, session]
---
# SESSION-STATE.md — Active Working Memory

**WAL Protocol:** Write state BEFORE responding, not after.

## Current Task
Dual-API Top 10 Gainers Prediction System — Setup Complete ✅

## Dual-API Policy (Enforced)
- **DeepSeek** → conversation, reasoning, vault management (THIS session)
- **HuggingFace FREE models** → ALL prediction work (forbidden to use DeepSeek for predictions)

## Pipeline: HF Free Models Only
```
Step 1: StephanAkkerman/FinTwitBERT → Sentiment Scores
Step 2: google/timesfm-1.0-200m + RSI/MACD/BB → Momentum Scores
Step 3: NeoQuasar/Kronos-base → Return % Forecasts
Step 4: Ranking → Top 10 → Logged to vault
```

## Setup Status
- [x] Project folder: 02_Projects/Top_Gainers_Predictor/
- [x] Scripts: sentiment_pipeline.py, timeseries_pipeline.py, kronos_pipeline.py, predict_gainers.py
- [x] Model KB: 03_Knowledge/Models/ (Kronos, FinTwitBERT, TimesFM overviews)
- [x] n8n workflow template: n8n_daily_workflow.json
- [x] Prediction logging: 05_Meta/prediction_log.md + .csv
- [x] GitHub auto-sync: Startup + every 4 hours via Task Scheduler
- [x] GitHub repo: PCnslt/openclaw-trading-system (51 files pushed)
- [x] Robinhood accessible via browser
- [x] Memory index updated

## Pending
- [ ] Install n8n (npm install still downloading)
- [ ] First live prediction run (test the HF API endpoints)
- [ ] Build evaluation dashboard

---
*Last updated: 2026-04-26T23:50:00.000Z*
