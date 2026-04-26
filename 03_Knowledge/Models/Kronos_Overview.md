---
tags: [knowledge, model, kronos, prediction]
---
# Kronos-base Model Overview 🦞

**Source:** Hugging Face - `NeoQuasar/Kronos-base`
**Type:** Financial time series forecasting model
**Use case:** Final market movement prediction combining OHLCV + sentiment + momentum

## Key Details
- Input: Multivariate time series (OHLCV + engineered features)
- Output: Forecasted return percentage for target date
- Architecture: Transformer-based financial forecasting model
- License: Free to use via HF Inference API

## Integration
- Called from `predict_gainers.py` orchestrator
- Receives combined feature vector from Steps 1 & 2
- Produces final predicted return for ranking
