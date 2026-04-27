#!/usr/bin/env python3
"""
predict_gainers.py — Master Orchestrator for Top 10 Gainers Prediction

Runs the full pipeline:
1. Sentiment Analysis (FinTwitBERT)
2. Time Series & Technical (TimesFM + indicators)
3. Final Prediction (Kronos-base)
4. Ranking & Output

Pipeline: HF_FREE models ONLY — no paid APIs (dual-API policy enforced).

Usage:
  python predict_gainers.py [--tickers TICKER1 TICKER2 ...]
  python predict_gainers.py --universe  # use full stock universe

Output: Top 10 predicted gainers for T+2, logged to vault + stdout.
"""

import sys
import os
import json
import subprocess
import csv
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd

VAULT_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = VAULT_ROOT / "02_Projects" / "Top_Gainers_Predictor" / "scripts"
LOG_DIR = VAULT_ROOT / "05_Meta"
os.chdir(VAULT_ROOT)

TARGET_OFFSET = 2  # Predict T+2

def run_module(script_path, args=None):
    """Run a Python pipeline module and return its JSON output."""
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    
    # Extract JSON_OUTPUT from stdout
    for line in result.stdout.split("\n"):
        if line.startswith("JSON_OUTPUT:"):
            return json.loads(line[12:])
    
    # Fallback: try parsing entire stdout
    try:
        return json.loads(result.stdout)
    except:
        print(f"  [module] Warning: could not parse output from {script_path.name}")
        return {}

def get_ticker_universe():
    """Get the stock universe. Start with major US stocks."""
    # In production, expand via yfinance
    major_tickers = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "JPM", "V",
        "JNJ", "WMT", "PG", "MA", "UNH", "HD", "DIS", "PYPL", "ADBE", "NFLX",
        "CRM", "INTC", "AMD", "BA", "NKE", "KO", "PEP", "MRK", "ABBV", "TMO",
        "AVGO", "ACN", "DHR", "TXN", "QCOM", "AMGN", "COST", "ABT", "NEE", "WFC",
        "UPS", "IBM", "LIN", "HON", "LOW", "SBUX", "CVX", "XOM", "UNP", "RTX",
        "SPY", "QQQ", "IWM", "DIA", "PLTR", "TSM", "LLY", "VZ", "T", "C",
        "GS", "MS", "SCHW", "BLK", "BKNG", "UBER", "LYFT", "SNAP", "RIVN", "LCID",
        "MRNA", "PFE", "GILD", "REGN", "VRTX", "ISRG", "SYK", "MDT", "BSX", "EW",
        "CAT", "DE", "GE", "MMM", "HON", "LMT", "NOC", "GD", "BA", "RTX"
    ]
    return major_tickers

def log_prediction(predictions, base_date):
    """Log predictions to vault CSV and markdown."""
    log_csv = LOG_DIR / "prediction_log.csv"
    log_md = LOG_DIR / "prediction_log.md"
    
    target_date = (datetime.strptime(base_date, "%Y-%m-%d") + timedelta(days=TARGET_OFFSET)).strftime("%Y-%m-%d")
    
    # CSV log
    is_new = not log_csv.exists()
    with open(log_csv, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["prediction_date", "target_date", "rank", "ticker", "predicted_return"])
        for p in predictions:
            writer.writerow([base_date, target_date, p["rank"], p["ticker"], p["predicted_return"]])
    
    # Markdown log
    md_header = "---\ntags: [meta, predictions, log]\n---\n# Prediction Log 🦞\n\n"
    if log_md.exists():
        md_header = ""
    
    with open(log_md, "a") as f:
        if not log_md.exists() or log_md.stat().st_size == 0:
            f.write(md_header)
        f.write(f"\n## {base_date} → {target_date}\n")
        f.write("| Rank | Ticker | Predicted Return |\n")
        f.write("|------|--------|-----------------|\n")
        for p in predictions:
            f.write(f"| {p['rank']} | {p['ticker']} | {p['predicted_return']:+.4f}% |\n")
    
    print(f"  Logged to {log_csv} and {log_md}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Top 10 Gainers Predictor")
    parser.add_argument("--tickers", type=str, nargs="+", default=None)
    parser.add_argument("--universe", action="store_true", help="Use full stock universe")
    parser.add_argument("--date", type=str, default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()
    
    base_date = args.date
    print(f"{'=' * 60}")
    print(f"  TOP 10 GAINERS PREDICTOR (T+{TARGET_OFFSET})")
    print(f"  HF Free Models Only — Dual-API Policy Enforced")
    print(f"  Base date: {base_date}")
    print(f"{'=' * 60}")
    
    # Get universe
    if args.universe:
        tickers = get_ticker_universe()
    elif args.tickers:
        tickers = args.tickers
    else:
        # Use a smaller default set for testing
        tickers = ["AAPL", "MSFT", "TSLA", "AMZN", "NVDA", "GOOGL", "META", "PLTR", "AMD", "AVGO"]
    
    print(f"\nUniverse: {len(tickers)} tickers")
    print(f"\n{'-' * 60}")
    
    # Step 1: Sentiment
    print(f"\n[Step 1/3] Sentiment Analysis (FinTwitBERT)")
    print(f"{'-' * 40}")
    sentiment_output = run_module(SCRIPTS_DIR / "sentiment_pipeline.py", tickers)
    sentiment_scores = sentiment_output.get("sentiment_scores", {})
    
    # Save intermediate
    with open(SCRIPTS_DIR / ".." / ".cache_sentiment.json", "w") as f:
        json.dump(sentiment_output, f)
    
    # Step 2: Time Series
    print(f"\n[Step 2/3] Time Series & Technical (TimesFM + Indicators)")
    print(f"{'-' * 40}")
    momentum_output = run_module(SCRIPTS_DIR / "timeseries_pipeline.py", tickers)
    momentum_scores = momentum_output.get("momentum_scores", {})
    
    with open(SCRIPTS_DIR / ".." / ".cache_momentum.json", "w") as f:
        json.dump(momentum_output, f)
    
    # Step 3: Final Prediction (Kronos)
    print(f"\n[Step 3/3] Final Market Movement Prediction (Kronos-base)")
    print(f"{'-' * 40}")
    kronos_args = [
        "--sentiment", str(SCRIPTS_DIR / ".." / ".cache_sentiment.json"),
        "--momentum", str(SCRIPTS_DIR / ".." / ".cache_momentum.json")
    ]
    prediction_output = run_module(SCRIPTS_DIR / "kronos_pipeline.py", kronos_args)
    top_10 = prediction_output.get("top_10", [])
    
    # Results
    print(f"\n{'=' * 60}")
    print(f"  TOP 10 PREDICTED GAINERS")
    target_date = (datetime.strptime(base_date, "%Y-%m-%d") + timedelta(days=TARGET_OFFSET)).strftime("%Y-%m-%d")
    print(f"  Prediction for: {target_date}")
    print(f"{'=' * 60}")
    print(f"| Rank | Ticker | Predicted Return |")
    print(f"|------|--------|-----------------|")
    for p in top_10:
        print(f"| {p['rank']:4d} | {p['ticker']:6s} | {p['predicted_return']:+.4f}% |")
    
    # Log to vault
    log_prediction(top_10, base_date)
    
    # Final output for n8n
    output = {
        "timestamp": datetime.now().isoformat(),
        "base_date": base_date,
        "target_date": target_date,
        "model_chain": [
            "StephanAkkerman/FinTwitBERT (sentiment)",
            "google/timesfm-1.0-200m (timeseries)",
            "NeoQuasar/Kronos-base (prediction)"
        ],
        "top_10": top_10,
        "n_tickers_analyzed": len(tickers),
        "dual_api_policy": "HF free models only, no DeepSeek for predictions"
    }
    print(f"\nJSON_OUTPUT:{json.dumps(output)}")

if __name__ == "__main__":
    main()
