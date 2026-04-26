#!/usr/bin/env python3
"""
feature_pipeline.py — Build features for the gainers prediction model.

Computes:
- Technical indicators (RSI, MACD, Bollinger Bands, volume trends)
- Momentum features (short/long-term returns, lagged returns)
- Sentiment features (from NewsAPI if available)
- Cross-stock correlation features
- Volatility proxies

Output: Feature matrix cached in vault for training/prediction.

Usage: python 02_Projects/scripts/feature_pipeline.py --date YYYY-MM-DD
"""

import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

VAULT_ROOT = Path(__file__).resolve().parents[2]
FEATURES_DIR = VAULT_ROOT / "02_Projects" / "top_gainers"
os.chdir(VAULT_ROOT)

def parse_args():
    parser = argparse.ArgumentParser(description="Build feature matrix for top gainers prediction")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"),
                        help="Date to build features for (YYYY-MM-DD)")
    parser.add_argument("--tickers", type=str, nargs="+", 
                        default=["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"],
                        help="Tickers to process")
    parser.add_argument("--lookback", type=int, default=252,
                        help="Lookback days for feature computation")
    return parser.parse_args()

def compute_rsi(series, period=14):
    """Compute Relative Strength Index."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta.where(delta < 0, 0.0))
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_macd(series, fast=12, slow=26, signal=9):
    """Compute MACD histogram."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return histogram

def compute_bollinger_bands(series, period=20, std_dev=2):
    """Compute Bollinger Band width (volatility proxy)."""
    sma = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = sma + (std * std_dev)
    lower = sma - (std * std_dev)
    bandwidth = (upper - lower) / sma * 100  # Percent bandwidth
    return bandwidth

def build_features(ticker, price_data, volume_data, lookback=252):
    """Build complete feature set for a single ticker."""
    features = {}
    
    if price_data.empty or len(price_data) < 50:
        return None
    
    close = price_data["Close"] if "Close" in price_data else price_data.iloc[:, 0]
    volume = volume_data["Volume"] if "Volume" in volume_data else None
    high = price_data["High"] if "High" in price_data else close
    low = price_data["Low"] if "Low" in price_data else close
    open_p = price_data["Open"] if "Open" in price_data else close
    
    # Returns
    features["return_1d"] = close.pct_change(1).iloc[-1] if len(close) > 1 else 0
    features["return_5d"] = close.pct_change(5).iloc[-1] if len(close) > 5 else 0
    features["return_10d"] = close.pct_change(10).iloc[-1] if len(close) > 10 else 0
    features["return_21d"] = close.pct_change(21).iloc[-1] if len(close) > 21 else 0
    features["return_63d"] = close.pct_change(63).iloc[-1] if len(close) > 63 else 0
    
    # Lagged returns (T-1, T-2)
    features["return_lag1"] = close.pct_change(1).iloc[-2] if len(close) > 2 else 0
    features["return_lag2"] = close.pct_change(1).iloc[-3] if len(close) > 3 else 0
    features["return_lag5"] = close.pct_change(5).iloc[-2] if len(close) > 6 else 0
    
    # Technical indicators
    features["rsi_14"] = compute_rsi(close, 14).iloc[-1] if len(close) > 14 else 50
    features["rsi_7"] = compute_rsi(close, 7).iloc[-1] if len(close) > 7 else 50
    
    # MACD histogram
    features["macd_hist"] = compute_macd(close).iloc[-1] if len(close) > 26 else 0
    
    # Bollinger Band width (volatility)
    features["bb_width"] = compute_bollinger_bands(close).iloc[-1] if len(close) > 20 else 0
    
    # Position in range
    period_high = close.rolling(20).max().iloc[-1] if len(close) > 20 else close.iloc[-1]
    period_low = close.rolling(20).min().iloc[-1] if len(close) > 20 else close.iloc[-1]
    range_val = period_high - period_low
    features["position_in_range"] = ((close.iloc[-1] - period_low) / range_val * 100) if range_val > 0 else 50
    
    # Volume features
    if volume is not None and not volume.empty:
        features["volume_ratio"] = volume.iloc[-1] / volume.rolling(20).mean().iloc[-1] if len(volume) > 20 else 1
        features["volume_change"] = volume.pct_change(1).iloc[-1] if len(volume) > 1 else 0
    else:
        features["volume_ratio"] = 1.0
        features["volume_change"] = 0.0
    
    # Volatility proxy
    features["volatility_10d"] = close.pct_change().rolling(10).std().iloc[-1] * 100 if len(close) > 10 else 0
    
    # Price level features
    features["close_vs_sma20"] = (close.iloc[-1] / close.rolling(20).mean().iloc[-1] - 1) * 100 if len(close) > 20 else 0
    features["close_vs_sma50"] = (close.iloc[-1] / close.rolling(50).mean().iloc[-1] - 1) * 100 if len(close) > 50 else 0
    
    # Gap (open vs previous close)
    features["gap_pct"] = ((open_p.iloc[-1] / close.iloc[-2]) - 1) * 100 if len(close) > 1 else 0
    
    # Intraday range
    features["intraday_range"] = ((high.iloc[-1] - low.iloc[-1]) / close.iloc[-1]) * 100
    
    return features

def main():
    args = parse_args()
    import yfinance as yf
    
    print(f"Building features for date: {args.date}")
    print(f"Tickers: {len(args.tickers)}")
    print(f"Lookback: {args.lookback} days")
    
    all_features = {}
    start_date = (datetime.strptime(args.date, "%Y-%m-%d") - timedelta(days=args.lookback)).strftime("%Y-%m-%d")
    
    for ticker in args.tickers:
        try:
            print(f"  Fetching {ticker}...", end=" ")
            data = yf.download(ticker, start=start_date, end=args.date, progress=False, auto_adjust=True)
            
            if data.empty:
                print("No data")
                continue
            
            # Separate price and volume
            price_cols = [c for c in data.columns if c[0] != 'Volume']
            vol_cols = [c for c in data.columns if c[0] == 'Volume']
            
            price_data = data[price_cols] if price_cols else data
            vol_data = data[vol_cols] if vol_cols else None
            
            features = build_features(ticker, price_data, vol_data, args.lookback)
            
            if features:
                all_features[ticker] = features
                print(f"{len(features)} features")
            else:
                print("Insufficient data")
                
        except Exception as e:
            print(f"Error: {e}")
    
    # Save feature matrix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = FEATURES_DIR / f"features_{args.date}.json"
    
    # Convert numpy types to native Python types for JSON serialization
    serializable = {}
    for ticker, feats in all_features.items():
        serializable[ticker] = {k: float(v) if isinstance(v, (np.floating,)) else v 
                                for k, v in feats.items()}
    
    with open(output_file, "w") as f:
        json.dump(serializable, f, indent=2, default=str)
    
    # Summary
    print(f"\n{'=' * 60}")
    print(f"Features built: {len(all_features)} tickers")
    print(f"Features per ticker: {len(next(iter(all_features.values()))) if all_features else 0}")
    print(f"Output: {output_file}")
    
    # Output JSON for n8n
    output = {
        "timestamp": datetime.now().isoformat(),
        "date": args.date,
        "tickers_processed": len(all_features),
        "features_per_ticker": len(next(iter(all_features.values()))) if all_features else 0,
        "output_file": str(output_file)
    }
    print(f"\nJSON_OUTPUT:{json.dumps(output)}")

if __name__ == "__main__":
    main()
