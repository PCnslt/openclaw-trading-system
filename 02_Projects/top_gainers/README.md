---
tags: [trading, prediction, gainers, project]
---
# Top Gainers Two-Day-Ahead Prediction Project 🦞

**Goal:** Predict the top 10 daily stock gainers two days in advance.
**Started:** 2026-04-26
**Status:** Initial setup

## Project Architecture

```
Data Sources (yfinance, NewsAPI, social) 
    ↓
Python Workers (fetch_universe.py → feature_pipeline.py → predict_gainers.py)
    ↓
n8n Orchestration (Daily_Gainers_Pipeline + Weekly_Retraining)
    ↓
Obsidian Vault (predictions, logs, knowledge, post-mortems)
    ↓
Dashboards (OpenClaw Dashboard + Custom prediction dashboard)
```

## Current Setup Status

- [x] Vault folder structure created
- [ ] Python installed
- [ ] n8n installed
- [ ] fetch_universe.py written
- [ ] feature_pipeline.py written
- [ ] predict_gainers.py written
- [ ] Daily n8n workflow configured
- [ ] Evaluation dashboard built
- [ ] Weekly retraining cron active

## Key Files

| File | Purpose |
|------|---------|
| 02_Projects/top_gainers/ | Prediction logs, backtests, analysis |
| 02_Projects/post_mortems/ | Autopsy reports for failed predictions |
| 03_Knowledge/gainers_drivers/ | Why stocks become gainers (knowledge base) |
| 05_Meta/predictor_retraining_log.md | Retraining history & performance |
| 05_Meta/mistakes_registry.md | False prediction patterns (filter rules) |
| 02_Projects/scripts/ | Python worker scripts |

## Strategy Notes

- Primary model: Gradient Boosted Trees (ranking by future excess returns)
- Secondary: Mamba-2 SSM + MoE deep learning (fallback/ensemble)
- Evaluation: Hit rate (top 10 predicted → actual), annualized return
- Walk-forward retraining: expanding window, retrain weekly
