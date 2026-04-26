#!/usr/bin/env python3
"""
timeseries_pipeline.py — Step 2: Time Series & Technical Analysis

Uses google/timesfm-1.0-200m from Hugging Face for time series forecasting,
combined with classic technical indicators (RSI, MACD, Bollinger, volume trends).

Output: {ticker: momentum_score}

Usage: python 02_Projects/Top_Gainers_Predictor/scripts/timeseries_pipeline.py TICKER1 TICKER2 ...
"""

import sys
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import requests

VAULT_ROOT = Path(__file__).resolve().parents[3]
os.chdir(VAULT_ROOT)

# Free HF Inference API for google/timesfm-1.0-200m
HF_API_URL = "https://api-inference.huggingface.co/models/google/timesfm-1.0-200m"
HF_HEADERS = {"Content-Type": "application/json"}

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd_hist(series, fast=12, slow=26, signal=9):
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return (macd_line - signal_line).iloc[-1]

def compute_bb_width(series, period=20):
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std * 2)
    lower = sma - (std * 2)
    return ((upper - lower) / sma.iloc[-1] * 100).iloc[-1]

def compute_technical_score(ticker, price_data, volume_data=None):
    """Compute momentum score from technical indicators alone."""
    if price_data is None or price_data.empty:
        return 0.0
    
    close = price_data["Close"] if "Close" in price_data.columns else price_data.iloc[:, 0]
    high = price_data["High"] if "High" in price_data.columns else close
    low = price_data["Low"] if "Low" in price_data.columns else close
    
    features = {}
    
    # Returns
    features["ret_1d"] = close.pct_change(1).iloc[-1] if len(close) > 1 else 0
    features["ret_5d"] = close.pct_change(5).iloc[-1] if len(close) > 5 else 0
    features["ret_10d"] = close.pct_change(10).iloc[-1] if len(close) > 10 else 0
    features["ret_21d"] = close.pct_change(21).iloc[-1] if len(close) > 21 else 0
    
    # Technicals
    features["rsi_14"] = compute_rsi(close, 14).iloc[-1] if len(close) > 14 else 50
    features["macd_hist"] = compute_macd_hist(close) if len(close) > 26 else 0
    features["bb_width"] = compute_bb_width(close) if len(close) > 20 else 0
    
    # Volume
    if volume_data is not None and not volume_data.empty:
        vol = volume_data["Volume"] if "Volume" in volume_data.columns else volume_data.iloc[:, 0]
        features["vol_ratio"] = vol.iloc[-1] / vol.rolling(20).mean().iloc[-1] if len(vol) > 20 else 1
    else:
        features["vol_ratio"] = 1.0
    
    # Normalize to -1 to +1 momentum score
    # High RSI (>70) + positive returns + rising volume = bullish momentum
    rsi_component = (features["rsi_14"] - 50) / 50  # -1 to +1
    ret_component = np.clip(features["ret_5d"] * 10, -1, 1)
    vol_component = np.clip((features["vol_ratio"] - 1) * 2, -1, 1)
    macd_component = np.clip(features["macd_hist"] * 10, -1, 1)
    
    momentum_score = (rsi_component * 0.3 + ret_component * 0.3 + 
                      vol_component * 0.2 + macd_component * 0.2)
    
    return round(np.clip(momentum_score, -1, 1), 4)

def forecast_with_timesfm(close_prices):
    """Use TimesFM via HF Inference API to get forecast signal."""
    try:
        # Format as list of numbers
        prices = close_prices.dropna().values.tolist()[-90:]  # last 90 days
        if len(prices) < 20:
            return 0.0
        
        payload = {
            "inputs": {"context": prices, "horizon": 5},
            "parameters": {}
        }
        
        resp = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload, timeout=30)
        
        if resp.status_code == 200:
            result = resp.json()
            # Depends on API response format - may need adjustment
            if isinstance(result, dict) and "forecast" in result:
                forecast = result["forecast"]
                # Compare forecast trend to recent price level
                if len(prices) > 0 and len(forecast) > 0:
                    trend = (forecast[-1] / prices[-1]) - 1
                    return np.clip(trend * 5, -1, 1)  # Scale to -1 to +1
        elif resp.status_code == 503:
            print("  [timesfm] Model loading, using technical only")
        elif resp.status_code == 429:
            print("  [timesfm] Rate limited, using technical only")
        else:
            print(f"  [timesfm] HTTP {resp.status_code}")
    except Exception as e:
        print(f"  [timesfm] Error: {e}")
    
    return None  # Signal to fall back to technical-only

def analyze_ticker_momentum(tickers):
    """Compute momentum scores for a list of tickers."""
    import yfinance as yf
    
    results = {}
    
    for ticker in tickers:
        try:
            data = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
            if data.empty:
                results[ticker] = 0.0
                continue
            
            # Separate price from volume
            price_cols = [c for c in data.columns if c[0] != 'Volume']
            vol_cols = [c for c in data.columns if c[0] == 'Volume']
            price_data = data[price_cols] if price_cols else data
            vol_data = data[vol_cols] if vol_cols else None
            
            # Technical score
            tech_score = compute_technical_score(ticker, price_data, vol_data)
            
            # TimesFM forecast (optional enhancement)
            close = price_data["Close"] if "Close" in price_data.columns else price_data.iloc[:, 0]
            timesfm_score = forecast_with_timesfm(close)
            
            # Combine: use TimesFM if available, otherwise technical-only
            if timesfm_score is not None:
                final_score = round(tech_score * 0.4 + timesfm_score * 0.6, 4)
            else:
                final_score = tech_score
            
            results[ticker] = final_score
            print(f"  {ticker}: momentum={final_score} (tech={tech_score}, timesfm={timesfm_score})")
            
        except Exception as e:
            print(f"  [error] {ticker}: {e}")
            results[ticker] = 0.0
    
    return results

def main():
    tickers = sys.argv[1:] if len(sys.argv) > 1 else None
    if not tickers:
        print("No tickers provided. Testing with default list.")
        tickers = ["AAPL", "MSFT", "TSLA", "AMZN", "NVDA"]
    
    print(f"Time Series & Technical Analysis Pipeline")
    print(f"Models: google/timesfm-1.0-200m + Technical Indicators")
    print(f"Tickers: {', '.join(tickers)}")
    print("-" * 50)
    
    results = analyze_ticker_momentum(tickers)
    
    output = {
        "timestamp": datetime.now().isoformat(),
        "model": "google/timesfm-1.0-200m",
        "momentum_scores": results
    }
    print(f"\nJSON_OUTPUT:{json.dumps(output)}")

if __name__ == "__main__":
    main()
