#!/usr/bin/env python3
"""
sentiment_pipeline.py — Step 1: Sentiment Analysis (UPDATED)
Uses HF router endpoint with cardiffnlp/twitter-roberta-base-sentiment-latest
Output: {ticker: sentiment_score} where score is -1 to +1
"""

import sys, os, json, requests
from pathlib import Path
from datetime import datetime

VAULT_ROOT = Path(__file__).resolve().parents[3]
os.chdir(VAULT_ROOT)

import os
import sys
from pathlib import Path
VAULT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(VAULT_ROOT / "02_Projects" / "scripts"))
try:
    from env_loader import get_api_key
    HF_TOKEN = get_api_key("HUGGINGFACE_TOKEN", os.environ.get("HF_TOKEN", ""))
except:
    HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_BASE = "https://router.huggingface.co/hf-inference/models"
HF_MODEL = "ahmedrachid/FinancialBERT-Sentiment-Analysis"  # Best financial sentiment model
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}

def get_sentiment_score(text):
    try:
        resp = requests.post(
            f"{HF_BASE}/{HF_MODEL}",
            headers=HEADERS,
            json={"inputs": text[:512]},
            timeout=30
        )
        if resp.status_code == 200:
            result = resp.json()
            if isinstance(result, list) and len(result) > 0 and isinstance(result[0], list):
                scores = result[0]
                pos = next((s["score"] for s in scores if s["label"].lower() == "positive"), 0.33)
                neg = next((s["score"] for s in scores if s["label"].lower() == "negative"), 0.33)
                return round(pos - neg, 4)
            elif isinstance(result, list) and len(result) > 0:
                pos = next((s["score"] for s in result if s["label"].lower() == "positive"), 0.33)
                neg = next((s["score"] for s in result if s["label"].lower() == "negative"), 0.33)
                return round(pos - neg, 4)
        elif resp.status_code == 503:
            print("  [sentiment] Model loading, retry later")
        else:
            print(f"  [sentiment] API {resp.status_code}: {resp.text[:100]}")
    except Exception as e:
        print(f"  [sentiment] Error: {e}")
    return 0.0

def fetch_headlines_for_ticker(ticker):
    import yfinance as yf
    try:
        stock = yf.Ticker(ticker)
        return [item.get("title", "") for item in (stock.news[:5] or [])]
    except:
        return []

def analyze_ticker_sentiment(tickers):
    results = {}
    for ticker in tickers:
        headlines = fetch_headlines_for_ticker(ticker)
        if not headlines:
            results[ticker] = 0.0
            continue
        scores = [get_sentiment_score(h) for h in headlines]
        avg = round(sum(scores) / len(scores), 4)
        results[ticker] = avg
        print(f"  {ticker}: {avg} (from {len(scores)} headlines)")
    return results

if __name__ == "__main__":
    tickers = sys.argv[1:] if len(sys.argv) > 1 else ["AAPL","MSFT","TSLA","AMZN","NVDA"]
    print(f"Sentiment: {', '.join(tickers)}")
    results = analyze_ticker_sentiment(tickers)
    output = {"timestamp": datetime.now().isoformat(), "model": HF_MODEL, "sentiment_scores": results}
    print(f"JSON_OUTPUT:{json.dumps(output)}")
