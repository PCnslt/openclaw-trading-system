---
tags: [knowledge, model, sentiment, financial]
---
# FinTwitBERT Model Overview 🦞

**Source:** Hugging Face - `StephanAkkerman/FinTwitBERT`
**Type:** Fine-tuned BERT for financial social media sentiment
**Use case:** Sentiment scoring of stock-related headlines & social media

## Key Details
- Based on BERT-base-uncased
- Fine-tuned on financial Twitter/social media data
- Output: Sentiment score (-1 to +1 scale)
- License: MIT

## Integration
- Called from `sentiment_pipeline.py`
- Input: News headlines or social media text related to a ticker
- Output: Float sentiment score per stock
