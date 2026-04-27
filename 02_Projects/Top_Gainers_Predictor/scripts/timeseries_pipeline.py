#!/usr/bin/env python3
"""
timeseries_pipeline.py — Step 2: Time Series & Technical Analysis (UPDATED)
HF router endpoint for TimesFM, falls back to technical indicators.
"""

import sys, os, json, requests, numpy as np, pandas as pd
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
HF_MODEL = "google/timesfm-1.0-200m"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def compute_macd_hist(series, fast=12, slow=26, signal=9):
    ef = series.ewm(span=fast, adjust=False).mean()
    es = series.ewm(span=slow, adjust=False).mean()
    return (ef - es - (ef - es).ewm(span=signal, adjust=False).mean()).iloc[-1]

def compute_tech_momentum(ticker, price_data, vol_data=None):
    if price_data is None or price_data.empty:
        return 0.0
    close = price_data["Close"] if "Close" in price_data.columns else price_data.iloc[:, 0]
    ret5 = close.pct_change(5).iloc[-1] if len(close) > 5 else 0
    rsi = compute_rsi(close, 14).iloc[-1] if len(close) > 14 else 50
    macd = compute_macd_hist(close) if len(close) > 26 else 0
    vol_ratio = 1.0
    if vol_data is not None and not vol_data.empty:
        v = vol_data["Volume"] if "Volume" in vol_data.columns else vol_data.iloc[:, 0]
        vol_ratio = v.iloc[-1] / v.rolling(20).mean().iloc[-1] if len(v) > 20 else 1
    
    rsi_c = (rsi - 50) / 50
    ret_c = np.clip(ret5 * 10, -1, 1)
    vol_c = np.clip((vol_ratio - 1) * 2, -1, 1)
    macd_c = np.clip(macd * 10, -1, 1)
    return round(np.clip(rsi_c * 0.3 + ret_c * 0.3 + vol_c * 0.2 + macd_c * 0.2, -1, 1), 4)

def forecast_timesfm(close_prices):
    try:
        prices = close_prices.dropna().values.tolist()[-90:]
        if len(prices) < 20:
            return None
        resp = requests.post(
            f"{HF_BASE}/{HF_MODEL}",
            headers=HEADERS,
            json={"inputs": {"context": prices, "horizon": 5}},
            timeout=30
        )
        if resp.status_code == 200:
            result = resp.json()
            forecast = result.get("forecast", result) if isinstance(result, dict) else result
            if isinstance(forecast, list) and len(forecast) > 0 and len(prices) > 0:
                last_f = forecast[-1] if isinstance(forecast[-1], (int, float)) else (forecast[-1][0] if isinstance(forecast[-1], list) else None)
                if last_f and prices[-1]:
                    return np.clip((float(last_f) / float(prices[-1]) - 1) * 5, -1, 1)
        elif resp.status_code in [400, 404]:
            pass  # TimesFM not available on router, use technical only
    except:
        pass
    return None

def analyze_momentum(tickers):
    import yfinance as yf
    results = {}
    for ticker in tickers:
        try:
            data = yf.download(ticker, period="6mo", progress=False, auto_adjust=True)
            if data.empty:
                results[ticker] = 0.0
                continue
            pc = [c for c in data.columns if c[0] != 'Volume']
            vc = [c for c in data.columns if c[0] == 'Volume']
            tech = compute_tech_momentum(ticker, data[pc] if pc else data, data[vc] if vc else None)
            close = data["Close"] if "Close" in data.columns else data.iloc[:, 0]
            tfm = forecast_timesfm(close)
            final = round(tech * 0.4 + tfm * 0.6, 4) if tfm is not None else tech
            results[ticker] = final
            print(f"  {ticker}: {final} (tech={tech}, tfm={tfm})")
        except Exception as e:
            print(f"  [error] {ticker}: {e}")
            results[ticker] = 0.0
    return results

if __name__ == "__main__":
    tickers = sys.argv[1:] if len(sys.argv) > 1 else ["AAPL","MSFT","TSLA","AMZN","NVDA"]
    print(f"Timeseries: {', '.join(tickers)}")
    results = analyze_momentum(tickers)
    output = {"timestamp": datetime.now().isoformat(), "model": HF_MODEL, "momentum_scores": results}
    print(f"JSON_OUTPUT:{json.dumps(output)}")
