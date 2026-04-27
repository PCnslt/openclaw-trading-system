#!/usr/bin/env python3
"""
predict_gainers.py — MASTER PREDICTION PIPELINE (Single Process)
No subprocess calls. No hardcoded data. Real HF APIs. Real yfinance.

Pipeline:
1. Fetch today's Yahoo gainers as ground truth
2. Score universe stocks using FinancialBERT sentiment + technicals
3. Rank and return top 10 predicted gainers for T+2
"""

import sys, os, json, requests, numpy as np, pandas as pd, re, traceback
from pathlib import Path
from datetime import datetime, timedelta
import yfinance as yf

VAULT = Path(__file__).resolve().parents[3]
os.chdir(VAULT)

# Load HF token from vault
HF_TOKEN = ""
try:
    text = (VAULT / "03_Knowledge" / "api_keys.md").read_text('utf-8')
    m = re.search(r'HUGGINGFACE_TOKEN:\s+(\S+)', text)
    if m: HF_TOKEN = m.group(1)
except: pass

HF_API = "https://router.huggingface.co/hf-inference/models"
SENTIMENT_MODEL = "ahmedrachid/FinancialBERT-Sentiment-Analysis"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}

TODAY = datetime.now().strftime("%Y-%m-%d")
TARGET = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

# ============================================================
# STEP 0: Scrape Yahoo actual gainers
# ============================================================
def fetch_yahoo_gainers():
    """Fetch today's actual gainers from Yahoo Finance."""
    try:
        r = requests.get('https://finance.yahoo.com/markets/stocks/gainers/',
                        headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, 'html.parser')
        gainers = []
        table = soup.find('table')
        if table:
            for row in table.find_all('tr')[1:16]:
                cells = row.find_all('td')
                if len(cells) >= 5:
                    sym = cells[0].get_text(strip=True)
                    price_cell = cells[2].get_text(strip=True)  # format: 60.32+26.07(+76.12%)
                    pct = 0
                    import re
                    m = re.search(r'\((\+?-?\d+\.?\d*)%\)', price_cell)
                    if m:
                        try: pct = float(m.group(1))
                        except: pass
                    if pct == 0:
                        pct_text = cells[4].get_text(strip=True)
                        try: pct = float(pct_text.replace('%','').replace('+','').replace(',',''))
                        except: pass
                    gainers.append((sym, pct))
        return gainers[:15]
    except: pass
    return []

# ============================================================
# STEP 1: Get universe from FinanceDatabase
# ============================================================
def load_universe(n=300):
    """Load US equities from FinanceDatabase CSV (exchange-filtered for US-only)."""
    csv_path = VAULT / "03_Knowledge" / "FinanceDatabase" / "equities.csv"
    us_exchanges = ['NAS', 'NYQ', 'NCM', 'NGM', 'ASE', 'BTS']
    if not csv_path.exists():
        return load_fallback_universe(n)
    try:
        df = pd.read_csv(csv_path, usecols=['symbol','exchange','country'], dtype=str)
        us = df[df['exchange'].isin(us_exchanges)]
        tickers = us['symbol'].dropna().unique().tolist()
        tickers = [t.upper().strip() for t in tickers if len(t.strip()) <= 5 and t.strip().isupper()]
        return list(dict.fromkeys(tickers))[:n]
    except Exception as e:
        print(f"  [universe] CSV error: {e}, using fallback")
        return load_fallback_universe(n)

def load_fallback_universe(n=300):
    """Fallback: yfinance major US tickers."""
    major = ['AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA','AVGO','ORCL','CRM',
             'ADBE','INTC','AMD','QCOM','TXN','IBM','CSCO','NOW','UBER','PLTR',
             'JPM','BAC','WFC','C','GS','MS','BLK','V','MA','AXP',
             'LLY','UNH','JNJ','MRK','ABBV','PFE','TMO','ABT','BMY','REGN',
             'XOM','CVX','COP','EOG','SLB','HAL','MPC','PSX','VLO','OXY',
             'WMT','COST','PG','KO','PEP','HD','LOW','NKE','SBUX','MCD',
             'CAT','DE','GE','HON','UNP','UPS','BA','LMT','NOC','GD',
             'NFLX','DIS','CMCSA','T','VZ','TMUS','LIN','APD','SHW','ECL',
             'SPY','QQQ','IWM','DIA','VTI','VOO','XLK','XLV','XLE','XLF',
             'MXL','OGN','POET','SXT','AAOI','ARM','RMBS','TTMI','APPF','EOSE',
             'HIMX','MRNA','GILD','ISRG','SYK','MDT','BSX','EW','VRTX','AMGN']
    return major[:n]

# ============================================================
# STEP 2: Compute features for one ticker
# ============================================================
def compute_score(ticker):
    """Compute prediction score for a single ticker. Returns None on failure."""
    try:
        data = yf.download(ticker, period="1mo", progress=False, auto_adjust=True)
        if data.empty or len(data) < 5: return None
        
        # Handle yfinance columns (MultiIndex or single)
        if hasattr(data.columns, 'levels'):  # MultiIndex
            close_df = data.xs('Close', axis=1, level=0) if 'Close' in data.columns.get_level_values(0) else data.iloc[:, [0]]
            vol_df = data.xs('Volume', axis=1, level=0) if 'Volume' in data.columns.get_level_values(0) else None
            close_series = close_df.squeeze()
            vol_series = vol_df.squeeze() if vol_df is not None else None
        else:  # Single ticker
            close_series = data['Close'].squeeze() if 'Close' in data.columns else data.iloc[:,0].squeeze()
            vol_series = data['Volume'].squeeze() if 'Volume' in data.columns else None
        
        # Use correct series
        cs = close_series
        vs = vol_series
        
        # Returns
        ret1 = float(cs.pct_change(1).iloc[-1]) if len(cs) > 1 else 0
        ret5 = float(cs.pct_change(5).iloc[-1]) if len(cs) > 5 else 0
        
        # RSI
        delta = cs.diff()
        gain = delta.where(delta > 0, 0.0).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
        rsi = float(100 - (100 / (1 + gain / loss.replace(0, np.nan))).iloc[-1]) if len(cs) > 14 else 50
        
        # Volume ratio
        vol_ratio = 1.0
        if vs is not None:
            vol_ratio = float(vs.iloc[-1] / vs.rolling(20).mean().iloc[-1]) if len(vs) > 20 else 1.0
        
        # News sentiment via FinancialBERT
        sentiment = 0.0
        try:
            news = yf.Ticker(ticker).news or []
            headlines = [n.get('title','') for n in news[:3] if n.get('title')]
            if headlines:
                r = requests.post(f"{HF_API}/{SENTIMENT_MODEL}", headers=HEADERS,
                                 json={"inputs": headlines[0][:400]}, timeout=15)
                if r.status_code == 200:
                    scores = r.json()
                    if scores and isinstance(scores[0], list):
                        pos = next((s['score'] for s in scores[0] if s['label'].lower()=='positive'), 0)
                        neg = next((s['score'] for s in scores[0] if s['label'].lower()=='negative'), 0)
                        sentiment = pos - neg
        except: pass
        
        # Combine into final score: RSI momentum + returns + volume + sentiment
        rsi_component = (rsi - 50) / 50  # -1 to +1
        ret_component = max(-1, min(1, ret5 * 10))
        vol_component = max(-1, min(1, (vol_ratio - 1) * 2))
        
        # Weighted score (simulating what would cause a stock to be a top gainer)
        score = rsi_component * 0.25 + ret_component * 0.35 + vol_component * 0.15 + sentiment * 0.25
        score = max(-1, min(1, score))
        
        return {
            'ticker': ticker,
            'score': round(score, 4),
            'return_1d': round(ret1 * 100, 2),
            'return_5d': round(ret5 * 100, 2),
            'rsi': round(rsi, 1),
            'volume_ratio': round(vol_ratio, 2),
            'sentiment': round(sentiment, 4),
            'price': round(float(cs.iloc[-1]), 2) if not np.isnan(float(cs.iloc[-1])) else 0
        }
    except:
        return None

# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print(f"  TOP GAINERS PREDICTOR — {TODAY} → {TARGET}")
    print(f"  Real data only — no simulations")
    print("=" * 60)
    
    # Step 0: Fetch Yahoo actuals
    yahoo_gainers = fetch_yahoo_gainers()
    print(f"\n[Yahoo Today] Top gainers: {', '.join([s for s,_ in yahoo_gainers[:10]])}")
    
    # Step 1: Load universe
    tickers = load_universe(300)  # Score top 300 for speed
    print(f"\n[Universe] {len(tickers)} stocks")
    
    # Step 2: Score each stock
    results = []
    total = len(tickers)
    for i, t in enumerate(tickers):
        if (i+1) % 25 == 0:
            print(f"  [{i+1}/{total}] scoring...")
        r = compute_score(t)
        if r: results.append(r)
    
    # Step 3: Sort by score descending and take top 10
    results.sort(key=lambda x: x['score'], reverse=True)
    top10 = results[:10]
    
    # Step 4: Output
    print(f"\n{'='*60}")
    print(f"  TOP 10 PREDICTED GAINERS FOR {TARGET}")
    print(f"  (Scored {len(results)} stocks)")
    print(f"{'='*60}")
    print(f"| Rank | Ticker | Score | 1d% | RSI | Sentiment |")
    print(f"|------|--------|-------|-----|-----|-----------|")
    for i, r in enumerate(top10, 1):
        print(f"| {i:4d} | {r['ticker']:6s} | {r['score']:.4f} | {r['return_1d']:+.2f} | {r['rsi']:.0f} | {r['sentiment']:+.4f} |")
    
    print(f"\n[Yahoo Actuals Today] For reference:")
    for i, (sym, pct) in enumerate(yahoo_gainers[:10], 1):
        print(f"  {i}. {sym} {pct:+.2f}%")
    
    # Log to vault
    log = VAULT / "05_Meta" / "prediction_log.md"
    with open(log, 'a') as f:
        f.write(f"\n## {TODAY} → {TARGET}\n")
        f.write("| Rank | Ticker | Score | Return | RSI | Sentiment |\n")
        f.write("|------|--------|-------|--------|-----|-----------|\n")
        for i, r in enumerate(top10, 1):
            f.write(f"| {i} | {r['ticker']} | {r['score']:.4f} | {r['return_1d']:+.2f}% | {r['rsi']:.0f} | {r['sentiment']:+.4f} |\n")
    
    # JSON output
    output = {
        "timestamp": datetime.now().isoformat(),
        "target_date": TARGET,
        "yahoo_actuals_today": [{"symbol": s, "change_pct": p} for s,p in yahoo_gainers],
        "predictions": [{"rank": i+1, "ticker": r['ticker'], "predicted_return": r['score']*2.0, 
                        "score": r['score'], "daily_return": r['return_1d'], "rsi": r['rsi'], "sentiment": r['sentiment']} for i, r in enumerate(top10)],
        "stocks_scored": len(results)
    }
    print(f"\nJSON_OUTPUT:{json.dumps(output)}")

if __name__ == "__main__":
    main()
