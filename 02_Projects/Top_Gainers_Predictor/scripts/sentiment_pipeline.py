#!/usr/bin/env python3
"""
sentiment_pipeline.py — Step 1: Sentiment Analysis

Uses FinTwitBERT (StephanAkkerman/FinTwitBERT) from Hugging Face
to analyze financial news/social media sentiment for each ticker.

Output: {ticker: sentiment_score} where score is -1 to +1

Usage: python 02_Projects/Top_Gainers_Predictor/scripts/sentiment_pipeline.py
"""

import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime
import requests

VAULT_ROOT = Path(__file__).resolve().parents[3]
os.chdir(VAULT_ROOT)

# Hugging Face Inference API (free tier) - no key needed for free models
HF_API_URL = "https://api-inference.huggingface.co/models/StephanAkkerman/FinTwitBERT"
HF_HEADERS = {"Content-Type": "application/json"}

def get_sentiment_score(text):
    """Get sentiment score for a text using HF Inference API."""
    try:
        resp = requests.post(
            HF_API_URL,
            headers=HF_HEADERS,
            json={"inputs": text[:512]},  # truncate to fit model
            timeout=15
        )
        if resp.status_code == 200:
            result = resp.json()
            # FinTwitBERT returns [[{"label": "POSITIVE", "score": x}, ...]]
            if isinstance(result, list) and len(result) > 0:
                scores = result[0]
                pos = next((s["score"] for s in scores if s["label"] == "POSITIVE"), 0.5)
                neg = next((s["score"] for s in scores if s["label"] == "NEGATIVE"), 0.5)
                return round(pos - neg, 4)  # -1 to +1
        elif resp.status_code == 429:
            print("  [sentiment] Rate limited, using neutral score")
            return 0.0
        else:
            print(f"  [sentiment] API error {resp.status_code}: {resp.text[:100]}")
            return 0.0
    except Exception as e:
        print(f"  [sentiment] Error: {e}")
        return 0.0

def fetch_headlines_for_ticker(ticker):
    """Fetch recent headlines for a ticker. Uses free sources."""
    import yfinance as yf
    
    headlines = []
    try:
        stock = yf.Ticker(ticker)
        news = stock.news[:5]  # Top 5 recent news items
        for item in news:
            title = item.get("title", "")
            if title:
                headlines.append(title)
    except:
        pass
    
    return headlines

def analyze_ticker_sentiment(tickers):
    """Analyze sentiment for a list of tickers."""
    results = {}
    
    for ticker in tickers:
        headlines = fetch_headlines_for_ticker(ticker)
        if not headlines:
            results[ticker] = 0.0  # neutral if no news
            continue
        
        # Average sentiment across headlines
        scores = []
        for headline in headlines:
            score = get_sentiment_score(headline)
            scores.append(score)
        
        avg_score = round(sum(scores) / len(scores), 4)
        results[ticker] = avg_score
        print(f"  {ticker}: {avg_score} (from {len(scores)} headlines)")
    
    return results

def main():
    tickers = sys.argv[1:] if len(sys.argv) > 1 else None
    if not tickers:
        print("No tickers provided. Testing with default list.")
        tickers = ["AAPL", "MSFT", "TSLA", "AMZN", "NVDA"]
    
    print(f"Sentiment Analysis Pipeline (FinTwitBERT)")
    print(f"Tickers: {', '.join(tickers)}")
    print("-" * 50)
    
    results = analyze_ticker_sentiment(tickers)
    
    # Output for orchestrator
    output = {
        "timestamp": datetime.now().isoformat(),
        "model": "StephanAkkerman/FinTwitBERT",
        "sentiment_scores": results
    }
    print(f"\nJSON_OUTPUT:{json.dumps(output)}")

if __name__ == "__main__":
    main()
