#!/usr/bin/env python3
"""
prediction_server.py — Multi-Agent Prediction Server for n8n workflow.
Individual endpoints for each agent in the pipeline.
"""

import http.server, json, sys, os, io, contextlib, re, requests, numpy as np, pandas as pd, traceback
from pathlib import Path
from datetime import datetime, timedelta

VAULT = Path(__file__).resolve().parents[3]
os.chdir(VAULT)
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Load HF token
HF_TOKEN = ""
try:
    text = (VAULT / "03_Knowledge" / "api_keys.md").read_text('utf-8')
    m = re.search(r'HUGGINGFACE_TOKEN:\s+(\S+)', text)
    if m: HF_TOKEN = m.group(1)
except: pass

HF_API = "https://router.huggingface.co/hf-inference/models"
SENTIMENT_MODEL = "ahmedrachid/FinancialBERT-Sentiment-Analysis"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}
CSV_PATH = VAULT / "03_Knowledge" / "FinanceDatabase" / "equities.csv"

class Handler(http.server.BaseHTTPRequestHandler):
    
    def do_GET(self):
        if self.path == "/health":
            self.send_json(200, {"status": "ok", "timestamp": datetime.now().isoformat()})
        elif self.path == "/run-prediction":
            self.run_full_pipeline()
        elif self.path == "/agent/universe":
            self.agent_universe()
        else:
            self.send_json(404, {"error": "not found"})
    
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
        try: data = json.loads(body)
        except: data = {}
        
        if self.path == "/agent/prices":
            self.agent_prices(data)
        elif self.path == "/agent/sentiment":
            self.agent_sentiment(data)
        elif self.path == "/agent/technicals":
            self.agent_technicals(data)
        else:
            self.send_json(404, {"error": "not found"})
    
    # ========== AGENTS ==========
    
    def agent_universe(self):
        """AGENT 1: Load stock universe from FinanceDatabase."""
        try:
            df = pd.read_csv(CSV_PATH, usecols=['symbol','exchange','name'], dtype=str, nrows=100000)
            us_ex = ['NAS','NYQ','NCM','NGM','ASE']
            us = df[df['exchange'].isin(us_ex)]
            tickers = us['symbol'].dropna().unique().tolist()
            tickers = [t.upper().strip() for t in tickers if len(t.strip()) <= 5 and t.strip().isupper() and '^' not in t]
            tickers = list(dict.fromkeys(tickers))[:300]
            self.send_json(200, {"tickers": tickers, "count": len(tickers), "source": "financedatabase"})
        except Exception as e:
            fallback = ['AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA','AVGO','INTC','AMD',
                       'JPM','BAC','WFC','GS','MS','V','MA','LLY','UNH','JNJ',
                       'XOM','CVX','WMT','COST','PG','KO','PEP','HD','CAT','DE',
                       'NFLX','DIS','BA','LMT','SPY','QQQ','IWM','MXL','OGN','POET',
                       'SXT','AAOI','ARM','RMBS','AMD','TTMI','APPF','EOSE','HIMX','MRNA']
            self.send_json(200, {"tickers": fallback, "count": len(fallback), "source": "fallback"})
    
    def agent_prices(self, data):
        """AGENT 2: Fetch prices for tickers."""
        import yfinance as yf
        tickers_raw = data.get('tickers', '')
        if isinstance(tickers_raw, str): tickers_list = tickers_raw.split(',')[:100]
        elif isinstance(tickers_raw, list): tickers_list = tickers_raw[:100]
        else: tickers_list = ['AAPL','MSFT']
        
        results = []
        for t in tickers_list:
            t = t.strip()
            if not t: continue
            try:
                d = yf.download(t, period='5d', progress=False, auto_adjust=True)
                if d.empty: continue
                if hasattr(d.columns, 'levels'):
                    cs = d.xs('Close', axis=1, level=0).squeeze()
                    vs = d.xs('Volume', axis=1, level=0).squeeze()
                else:
                    cs = d['Close'].squeeze() if 'Close' in d.columns else d.iloc[:,0].squeeze()
                    vs = d['Volume'].squeeze() if 'Volume' in d.columns else None
                results.append({
                    'ticker': t,
                    'price': round(float(cs.iloc[-1]), 2) if not np.isnan(float(cs.iloc[-1])) else 0,
                    'return_1d': round(float(cs.pct_change(1).iloc[-1])*100, 2) if len(cs)>1 else 0,
                    'return_5d': round(float(cs.pct_change(5).iloc[-1])*100, 2) if len(cs)>5 else 0,
                    'volume': round(float(vs.iloc[-1]), 0) if vs is not None else 0,
                    'volume_avg': round(float(vs.rolling(20).mean().iloc[-1]), 0) if vs is not None and len(vs)>20 else 0,
                })
            except: pass
        
        self.send_json(200, {"tickers": [r['ticker'] for r in results], "prices": results, "count": len(results)})
    
    def agent_sentiment(self, data):
        """AGENT 3: Sentiment analysis via FinancialBERT."""
        tickers_raw = data.get('tickers', [])
        if isinstance(tickers_raw, str): tickers_list = tickers_raw.split(',')
        elif isinstance(tickers_raw, list): tickers_list = tickers_raw
        else: tickers_list = []
        
        results = []
        import yfinance as yf
        for t in tickers_list[:50]:
            score = 0.0
            try:
                news = yf.Ticker(t).news or []
                headlines = [n.get('title','') for n in news[:2] if n.get('title')]
                if headlines and HF_TOKEN:
                    r = requests.post(f"{HF_API}/{SENTIMENT_MODEL}", headers=HEADERS,
                                     json={"inputs": headlines[0][:400]}, timeout=15)
                    if r.status_code == 200:
                        s = r.json()
                        if s and isinstance(s[0], list):
                            pos = next((x['score'] for x in s[0] if x['label'].lower()=='positive'), 0)
                            neg = next((x['score'] for x in s[0] if x['label'].lower()=='negative'), 0)
                            score = round(pos - neg, 4)
                elif headlines:
                    score = 0.05
            except: pass
            results.append({"ticker": t, "sentiment_score": score})
        
        self.send_json(200, {"results": results, "count": len(results), "model": SENTIMENT_MODEL})
    
    def agent_technicals(self, data):
        """AGENT 4: Technical analysis (RSI, MACD, volume)."""
        import yfinance as yf
        tickers_raw = data.get('tickers', [])
        if isinstance(tickers_raw, str): tickers_list = tickers_raw.split(',')
        elif isinstance(tickers_raw, list): tickers_list = tickers_raw
        else: tickers_list = []
        
        results = []
        for t in tickers_list[:50]:
            try:
                d = yf.download(t, period='3mo', progress=False, auto_adjust=True)
                if d.empty: continue
                if hasattr(d.columns, 'levels'):
                    cs = d.xs('Close', axis=1, level=0).squeeze()
                    vs = d.xs('Volume', axis=1, level=0).squeeze()
                else:
                    cs = d['Close'].squeeze() if 'Close' in d.columns else d.iloc[:,0].squeeze()
                    vs = d['Volume'].squeeze() if 'Volume' in d.columns else None
                
                # RSI
                delta = cs.diff()
                gain = delta.where(delta > 0, 0.0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0.0)).rolling(14).mean()
                rsi = float(100 - (100 / (1 + gain / loss.replace(0, np.nan))).iloc[-1]) if len(cs) > 14 else 50
                
                # MACD
                ema12 = cs.ewm(span=12, adjust=False).mean()
                ema26 = cs.ewm(span=26, adjust=False).mean()
                macd = float((ema12 - ema26 - (ema12 - ema26).ewm(span=9, adjust=False).mean()).iloc[-1]) if len(cs) > 26 else 0
                
                # Volume ratio
                vol_ratio = float(vs.iloc[-1] / vs.rolling(20).mean().iloc[-1]) if vs is not None and len(vs) > 20 else 1.0
                
                # Bollinger Band width
                sma20 = cs.rolling(20).mean()
                std20 = cs.rolling(20).std()
                bb_width = float(((sma20 + 2*std20) - (sma20 - 2*std20)) / sma20.iloc[-1] * 100) if len(cs) > 20 else 0
                
                # Momentum score
                rsi_c = (rsi - 50) / 50
                ret5 = float(cs.pct_change(5).iloc[-1]) if len(cs) > 5 else 0
                ret_c = max(-1, min(1, ret5 * 10))
                vol_c = max(-1, min(1, (vol_ratio - 1) * 2))
                macd_c = max(-1, min(1, macd * 10))
                momentum_score = round(rsi_c * 0.25 + ret_c * 0.30 + vol_c * 0.20 + macd_c * 0.25, 4)
                
                results.append({
                    'ticker': t,
                    'rsi': round(rsi, 1),
                    'macd': round(macd, 4),
                    'volume_ratio': round(vol_ratio, 2),
                    'bb_width': round(bb_width, 2),
                    'return_5d': round(float(ret5)*100, 2),
                    'momentum_score': momentum_score,
                    'price': round(float(cs.iloc[-1]), 2)
                })
            except: pass
        
        self.send_json(200, {"results": results, "count": len(results)})
    
    # ========== FULL PIPELINE ==========
    
    def run_full_pipeline(self):
        """Full pipeline with reasoning breakdown and target dates."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        output = {}
        reasoning = []
        
        try:
            # Load universe
            from predict_gainers import load_universe, compute_score, fetch_yahoo_gainers
            tickers = load_universe(50)
            
            # Score stocks and collect reasoning
            results = []
            for t in tickers:
                r = compute_score(t)
                if r:
                    results.append(r)
                    reasoning.append(r)
            
            results.sort(key=lambda x: x['score'], reverse=True)
            top10 = results[:10]
            
            yahoo = fetch_yahoo_gainers()
            
            now = datetime.now()
            target = now + timedelta(days=2)
            
            output = {
                "timestamp": now.isoformat(),
                "base_date": now.strftime("%Y-%m-%d"),
                "target_date": target.strftime("%Y-%m-%d"),
                "stocks_scored": len(results),
                "stocks_in_universe": len(tickers),
                "yahoo_actuals_today": [{"symbol": s, "change_pct": p} for s,p in yahoo],
                "predictions": [{
                    "rank": i+1, "ticker": r['ticker'],
                    "predicted_return": round(r['score']*2, 4),
                    "confidence": r['score'],
                    "sentiment": r['sentiment'],
                    "rsi": r['rsi'],
                    "volume_ratio": r['volume_ratio']
                } for i, r in enumerate(top10)],
                "reasoning": reasoning[:20],  # Top 20 with full breakdown
                "model_chain": [
                    "ahmedrachid/FinancialBERT-Sentiment-Analysis (sentiment)",
                    "Technical Indicators (RSI+MACD+Bollinger+Volume)",
                    "Multi-factor Weighted Scoring"
                ]
            }
        except Exception as e:
            output = {"error": str(e), "traceback": traceback.format_exc()}
        
        self.wfile.write(json.dumps(output, indent=2, default=str).encode("utf-8"))
    
    def send_json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))
    
    def log_message(self, *args): pass

if __name__ == "__main__":
    port = 18888
    srv = http.server.HTTPServer(("127.0.0.1", port), Handler)
    print(f"Multi-Agent Prediction Server on http://127.0.0.1:{port}")
    print(f"  GET  /health             - Health check")
    print(f"  GET  /run-prediction      - Full pipeline (legacy)")
    print(f"  GET  /agent/universe      - Load stock universe")
    print(f"  POST /agent/prices        - Fetch price data")
    print(f"  POST /agent/sentiment     - Sentiment analysis")
    print(f"  POST /agent/technicals    - Technical analysis")
    srv.serve_forever()
