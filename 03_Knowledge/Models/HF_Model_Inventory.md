---
tags: [knowledge, models, huggingface, free]
---
# HuggingFace Models Inventory 🦞

_Last tested: 2026-04-26_
_All tested via `router.huggingface.co/hf-inference/models` with HF token auth._

## ✅ Primary Pipeline Models (Available Free via HF Router)

### Step 1: Financial Sentiment (All Working)

| Model | Score* | Downloads | Params | Notes |
|-------|--------|-----------|--------|-------|
| `ahmedrachid/FinancialBERT-Sentiment-Analysis` | **0.9997** | 27k | 110M | Best financial-specific model |
| `mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis` | **0.9995** | **304k** | 82M | Most popular, fast |
| `mrm8488/deberta-v3-ft-financial-news-sentiment-analysis` | **0.9982** | 44.7k | 0.1B | High quality |
| `cardiffnlp/twitter-roberta-base-sentiment-latest` | 0.9547 | 10M+ | 125M | General purpose fallback |

*Score: POS-NEG on "AAPL stock surges on strong earnings" test.

**Winner:** `ahmedrachid/FinancialBERT-Sentiment-Analysis` (best financial accuracy, lowest size)

### Step 2: Time Series (Not Available via Free HF Router)
- `google/timesfm-1.0-200m` — ❌ "not supported by provider hf-inference"
- `facebook/prophet-net` — ❌ "not supported by provider hf-inference"
- `Nixtla/TimeGPT-1` — ❌ "not supported by provider hf-inference"

**→ Fallback: Technical indicators (RSI, MACD, Bollinger Bands, volume trends)**

### Step 3: Stock Prediction (Not Available via Free HF Router)
- `NeoQuasar/Kronos-base` — ❌ "not supported by provider hf-inference"
- `NeoQuasar/Kronos-tiny` — ❌ "not supported by provider hf-inference"

**→ Fallback: Weighted combination of sentiment + technical momentum**

## Architecture (Updated)
```
1. yfinance → OHLCV + News Headlines
2. ahmedrachid/FinancialBERT-Sentiment-Analysis → Sentiment Score
3. Technical indicators (RSI, MACD, BB, Volume) → Momentum Score
4. Weighted prediction: Sentiment(30%) + Momentum(70%) → Predicted Return
5. Rank → Top 10 for T+2
```

## Alternative Inference Providers
HF partners (may offer time series/stock models):
- Groq, Together AI, Fireworks, Replicate, SambaNova, Cerebras
- Check: `https://huggingface.co/models?inference_provider=groq&search=timeseries`
