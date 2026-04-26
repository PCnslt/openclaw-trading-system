---
tags: [knowledge, model, timesfm, timeseries]
---
# TimesFM Model Overview 🦞

**Source:** Hugging Face - `google/timesfm-1.0-200m`
**Type:** Time Series Foundation Model (Google Research)
**Use case:** Momentum scoring from stock price/volume time series

## Key Details
- 200M parameter time series foundation model
- Pre-trained on diverse time series datasets
- Can generate forecasts and embeddings from historical data
- License: Apache 2.0

## Integration
- Called from `timeseries_pipeline.py`
- Input: Historical OHLCV data (e.g., 60-90 days)
- Output: Momentum score + forecast features
- Combined with classic technical indicators (RSI, MACD, Bollinger)
