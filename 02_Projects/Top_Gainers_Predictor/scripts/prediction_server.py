#!/usr/bin/env python3
"""
prediction_server.py — Database-backed Prediction Server
Serves all endpoints from SQLite database (stock_data.db).
Does NOT do real-time API calls — data pipeline handles that.
"""
import http.server, json, sys, os, re, subprocess, time
from pathlib import Path
from datetime import datetime, timedelta

VAULT = Path(__file__).resolve().parents[3]
os.chdir(VAULT)
DB_PATH = Path(__file__).resolve().parent.parent / 'stock_data.db'

# Load HF token for sentiment fallback
HF_TOKEN = ""
try:
    text = (VAULT / "03_Knowledge" / "api_keys.md").read_text('utf-8')
    m = re.search(r'HUGGINGFACE_TOKEN:\s+(\S+)', text)
    if m: HF_TOKEN = m.group(1)
except:
    pass

import sqlite3

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def get_latest_prediction_date(conn):
    c = conn.cursor()
    c.execute("SELECT MAX(prediction_date) FROM predictions")
    row = c.fetchone()
    return row[0] if row and row[0] else None

class Handler(http.server.BaseHTTPRequestHandler):
    
    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2, default=str).encode("utf-8"))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
    
    def do_GET(self):
        path = self.path.split('?')[0]
        
        # Health check
        if path == '/health':
            db_exists = DB_PATH.exists()
            db_size = DB_PATH.stat().st_size if db_exists else 0
            try:
                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM tickers")
                tickers = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM prices")
                prices = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM technicals")
                techs = c.fetchone()[0]
                c.execute("SELECT COUNT(*) FROM predictions")
                preds = c.fetchone()[0]
                conn.close()
            except:
                tickers = prices = techs = preds = 0
            
            return self._json({
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "database": {
                    "path": str(DB_PATH),
                    "exists": db_exists,
                    "size_kb": round(db_size / 1024, 1) if db_exists else 0,
                    "tickers": tickers,
                    "prices": prices,
                    "technicals": techs,
                    "predictions": preds
                }
            })
        
        # Run prediction (read from database)
        if path == '/run-prediction':
            return self._handle_run_prediction()
        
        # Agent 1: Universe from database
        if path == '/agent/universe':
            return self._handle_universe()
        
        # Pipeline management
        if path == '/pipeline/status':
            return self._handle_pipeline_status()
        
        if path == '/pipeline/run':
            return self._handle_pipeline_run()
        
        # Database stats
        if path == '/stats':
            return self._handle_stats()
        
        # Reasoning breakdown
        if path == '/reasoning':
            return self._handle_reasoning()
        
        self._json({"error": "not found"}, 404)
    
    def do_POST(self):
        path = self.path.split('?')[0]
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len).decode('utf-8') if content_len else '{}'
        params = json.loads(body) if body else {}
        
        # Agent 2: Prices from database
        if path == '/agent/prices':
            return self._handle_prices(params)
        
        # Agent 3: Sentiment from database
        if path == '/agent/sentiment':
            return self._handle_sentiment(params)
        
        # Agent 4: Technicals from database
        if path == '/agent/technicals':
            return self._handle_technicals(params)
        
        self._json({"error": "not found"}, 404)
    
    def _handle_universe(self):
        """Return all tickers from database."""
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT symbol, name, exchange, sector FROM tickers WHERE is_active = 1 ORDER BY symbol")
            rows = c.fetchall()
            conn.close()
            return self._json({
                "tickers": [r[0] for r in rows],
                "count": len(rows),
                "source": "FinanceDatabase (SQLite)"
            })
        except Exception as e:
            return self._json({"error": str(e)}, 500)
    
    def _handle_prices(self, params):
        """Return prices from database for requested tickers."""
        tickers = params.get('tickers', [])
        if isinstance(tickers, str):
            tickers = [t.strip() for t in tickers.split(',') if t.strip()]
        
        try:
            conn = get_db()
            c = conn.cursor()
            results = []
            for ticker in tickers:
                c.execute(
                    "SELECT date, close, volume, open, high, low FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 60",
                    (ticker,)
                )
                rows = c.fetchall()
                if rows:
                    latest = rows[0]
                    results.append({
                        "ticker": ticker,
                        "latest_price": latest['close'],
                        "latest_volume": latest['volume'],
                        "latest_date": latest['date'],
                        "data_points": len(rows),
                        "price_history": [{"date": r['date'], "close": r['close'], "volume": r['volume']} for r in rows[:5]]
                    })
            conn.close()
            return self._json({"tickers": results, "count": len(results)})
        except Exception as e:
            return self._json({"error": str(e)}, 500)
    
    def _handle_sentiment(self, params):
        """Return sentiment from database for requested tickers."""
        tickers = params.get('tickers', [])
        if isinstance(tickers, str):
            tickers = [t.strip() for t in tickers.split(',') if t.strip()]
        
        try:
            conn = get_db()
            c = conn.cursor()
            results = []
            for ticker in tickers:
                c.execute(
                    "SELECT ticker, date, sentiment_score, compound FROM sentiment WHERE ticker = ? ORDER BY date DESC LIMIT 1",
                    (ticker,)
                )
                row = c.fetchone()
                if row:
                    results.append({
                        "ticker": row['ticker'],
                        "sentiment_score": row['sentiment_score'],
                        "compound": row['compound'],
                        "date": row['date'],
                        "model": "FinancialBERT"
                    })
            conn.close()
            return self._json({"sentiment": results, "count": len(results)})
        except Exception as e:
            return self._json({"error": str(e)}, 500)
    
    def _handle_technicals(self, params):
        """Return technicals from database for requested tickers."""
        tickers = params.get('tickers', [])
        if isinstance(tickers, str):
            tickers = [t.strip() for t in tickers.split(',') if t.strip()]
        
        try:
            conn = get_db()
            c = conn.cursor()
            results = []
            for ticker in tickers:
                c.execute(
                    """SELECT ticker, date, rsi, macd, macd_signal, bb_upper, bb_middle, bb_lower,
                       volume_ratio, return_1d, return_5d, return_20d, momentum_5d
                       FROM technicals WHERE ticker = ? ORDER BY date DESC LIMIT 1""",
                    (ticker,)
                )
                row = c.fetchone()
                if row:
                    results.append({
                        "ticker": row['ticker'],
                        "rsi": row['rsi'],
                        "macd": row['macd'],
                        "volume_ratio": row['volume_ratio'],
                        "return_1d": row['return_1d'],
                        "return_5d": row['return_5d'],
                        "return_20d": row['return_20d'],
                        "momentum_5d": row['momentum_5d'],
                        "bb_upper": row['bb_upper'],
                        "bb_middle": row['bb_middle'],
                        "bb_lower": row['bb_lower'],
                        "date": row['date']
                    })
            conn.close()
            return self._json({"technicals": results, "count": len(results)})
        except Exception as e:
            return self._json({"error": str(e)}, 500)
    
    def _handle_run_prediction(self):
        """Return predictions from database with full breakdown."""
        try:
            conn = get_db()
            c = conn.cursor()
            
            # Get latest prediction date
            pred_date = get_latest_prediction_date(conn)
            if not pred_date:
                conn.close()
                return self._json({
                    "status": "no_data",
                    "message": "No predictions found. Run the data pipeline first: /pipeline/run",
                    "target_date": (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
                    "base_date": datetime.now().strftime('%Y-%m-%d')
                })
            
            # Get top 10 predictions with full data
            c.execute("""
                SELECT p.ticker, p.prediction_date, p.target_date, p.composite_score, 
                       p.predicted_return, p.confidence, p.rsi, p.volume_ratio, p.sentiment_score
                FROM predictions p
                WHERE p.prediction_date = ?
                ORDER BY p.composite_score DESC
            """, (pred_date,))
            preds = c.fetchall()
            
            # Yahoo gainers (scraped separately or from database)
            yahoo = self._fetch_yahoo_gainers()
            
            # Detailed reasoning for top 20
            c.execute("""
                SELECT p.ticker, p.composite_score, p.rsi, p.volume_ratio, p.sentiment_score,
                       tech.return_1d, tech.return_5d, tech.momentum_5d
                FROM predictions p
                LEFT JOIN technicals tech ON p.ticker = tech.ticker
                WHERE p.prediction_date = ?
                ORDER BY p.composite_score DESC
                LIMIT 20
            """, (pred_date,))
            reasoning_rows = c.fetchall()
            
            # Stats
            c.execute("SELECT COUNT(*) FROM predictions WHERE prediction_date = ?", (pred_date,))
            total_scored = c.fetchone()[0]
            
            c.execute("SELECT COUNT(*) FROM tickers WHERE is_active = 1")
            total_tickers = c.fetchone()[0]
            
            conn.close()
            
            predictions = []
            for i, r in enumerate(preds[:10]):
                predictions.append({
                    "rank": i + 1,
                    "ticker": r['ticker'],
                    "predicted_return": r['predicted_return'],
                    "confidence": r['confidence'],
                    "composite_score": r['composite_score'],
                    "rsi": r['rsi'],
                    "volume_ratio": r['volume_ratio'],
                    "sentiment_score": r['sentiment_score']
                })
            
            reasoning = []
            for r in reasoning_rows:
                reasoning.append({
                    "ticker": r['ticker'],
                    "score": r['composite_score'],
                    "rsi": r['rsi'],
                    "volume_ratio": r['volume_ratio'],
                    "sentiment": r['sentiment_score'],
                    "return_1d": r['return_1d'],
                    "return_5d": r['return_5d'],
                    "momentum_5d": r['momentum_5d']
                })
            
            # Count stocks with RSI > 65 (momentum signal)
            momentum_count = sum(1 for r in reasoning if r['rsi'] and r['rsi'] > 65)
            vol_spike_count = sum(1 for r in reasoning if r['volume_ratio'] and r['volume_ratio'] > 1.5)
            
            return self._json({
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "base_date": pred_date,
                "target_date": preds[0]['target_date'] if preds else (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
                "stocks_scored": total_scored,
                "stocks_in_universe": total_tickers,
                "stocks_with_momentum": momentum_count,
                "stocks_with_volume_spike": vol_spike_count,
                "yahoo_actuals_today": yahoo,
                "predictions": predictions,
                "reasoning": reasoning,
                "model_chain": [
                    "ahmedrachid/FinancialBERT-Sentiment-Analysis (sentiment)",
                    "Technical Indicators (RSI+MACD+Bollinger+Volume)",
                    "Multi-factor Weighted Scoring (S:35% R:30% RSI:20% V:15%)"
                ],
                "data_source": "SQLite Database (FinanceDatabase + yfinance batch)"
            })
            
        except Exception as e:
            import traceback
            return self._json({"error": str(e), "traceback": traceback.format_exc()}, 500)
    
    def _handle_pipeline_status(self):
        """Show pipeline run history and database stats."""
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM pipeline_log ORDER BY run_id DESC LIMIT 10")
            logs = c.fetchall()
            
            c.execute("SELECT COUNT(*) FROM tickers WHERE is_active = 1")
            tickers = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM prices")
            prices = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM technicals")
            techs = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM sentiment")
            sents = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM predictions")
            preds = c.fetchone()[0]
            
            c.execute("SELECT MIN(date), MAX(date) FROM prices")
            date_range = c.fetchone()
            
            c.execute("SELECT COUNT(*) FROM tickers WHERE last_price_update IS NOT NULL")
            priced = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM tickers WHERE last_technicals_update IS NOT NULL")
            tech_updated = c.fetchone()[0]
            c.execute("SELECT COUNT(*) FROM tickers WHERE last_sentiment_update IS NOT NULL")
            sent_updated = c.fetchone()[0]
            
            conn.close()
            
            return self._json({
                "database": {
                    "path": str(DB_PATH),
                    "size_kb": round(DB_PATH.stat().st_size / 1024, 1),
                },
                "tables": {
                    "tickers": tickers,
                    "prices": prices,
                    "technicals": techs,
                    "sentiment": sents,
                    "predictions": preds
                },
                "coverage": {
                    "with_price_data": priced,
                    "with_technicals": tech_updated,
                    "with_sentiment": sent_updated,
                    "price_date_range": f"{date_range[0]} to {date_range[1]}" if date_range[0] else "none"
                },
                "pipeline_runs": [dict(r) for r in logs]
            })
        except Exception as e:
            return self._json({"error": str(e)}, 500)
    
    def _handle_pipeline_run(self):
        """Trigger the data pipeline in background."""
        try:
            script = Path(__file__).resolve().parent / 'data_pipeline.py'
            proc = subprocess.Popen(
                [sys.executable, '-X', 'utf8', str(script), '--max-tickers', '100', '--sentiment-top', '50'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATENO_WINDOW') else 0
            )
            return self._json({
                "status": "started",
                "message": "Pipeline started. Check /pipeline/status for progress.",
                "pid": proc.pid
            })
        except Exception as e:
            return self._json({"error": str(e)}, 500)
    
    def _handle_stats(self):
        """Return comprehensive database statistics."""
        try:
            conn = get_db()
            c = conn.cursor()
            
            c.execute("SELECT exchange, COUNT(*) as cnt FROM tickers WHERE is_active = 1 GROUP BY exchange ORDER BY cnt DESC")
            exchanges = {r[0]: r[1] for r in c.fetchall()}
            
            c.execute("SELECT market_cap, COUNT(*) as cnt FROM tickers WHERE is_active = 1 AND market_cap != '' GROUP BY market_cap ORDER BY cnt DESC")
            mcap = {r[0]: r[1] for r in c.fetchall()}
            
            c.execute("""
                SELECT sector, COUNT(*) as cnt FROM tickers 
                WHERE is_active = 1 AND sector != '' 
                GROUP BY sector ORDER BY cnt DESC LIMIT 10
            """)
            sectors = [{"sector": r[0], "count": r[1]} for r in c.fetchall()]
            
            conn.close()
            
            return self._json({
                "exchanges": exchanges,
                "market_caps": mcap,
                "top_sectors": sectors
            })
        except Exception as e:
            return self._json({"error": str(e)}, 500)
    
    def _handle_reasoning(self):
        """Return detailed reasoning breakdown for top predictions."""
        try:
            conn = get_db()
            c = conn.cursor()
            
            c.execute("SELECT MAX(prediction_date) FROM predictions")
            pred_date = c.fetchone()[0]
            if not pred_date:
                conn.close()
                return self._json({"reasoning": []})
            
            c.execute("""
                SELECT p.ticker, p.composite_score, p.rsi, p.volume_ratio, p.sentiment_score,
                       tech.return_1d, tech.return_5d, tech.momentum_5d
                FROM predictions p
                LEFT JOIN technicals tech ON p.ticker = tech.ticker
                WHERE p.prediction_date = ?
                ORDER BY p.composite_score DESC
                LIMIT 50
            """, (pred_date,))
            
            rows = c.fetchall()
            conn.close()
            
            reasoning = []
            for r in rows:
                signals = []
                if r['rsi'] and r['rsi'] > 65: signals.append("momentum")
                if r['rsi'] and r['rsi'] < 35: signals.append("oversold")
                if r['volume_ratio'] and r['volume_ratio'] > 1.5: signals.append("volume_spike")
                if r['sentiment_score'] and r['sentiment_score'] > 0.2: signals.append("positive_sentiment")
                if r['sentiment_score'] and r['sentiment_score'] < -0.2: signals.append("negative_sentiment")
                if r['return_5d'] and r['return_5d'] > 5: signals.append("uptrend")
                if r['return_5d'] and r['return_5d'] < -5: signals.append("downtrend")
                
                reasoning.append({
                    "ticker": r['ticker'],
                    "composite_score": r['composite_score'],
                    "rsi": r['rsi'],
                    "volume_ratio": r['volume_ratio'],
                    "sentiment_score": r['sentiment_score'],
                    "return_1d": r['return_1d'],
                    "return_5d": r['return_5d'],
                    "momentum_5d": r['momentum_5d'],
                    "signals": signals,
                    "signal_count": len(signals)
                })
            
            return self._json({"reasoning": reasoning, "count": len(reasoning)})
        except Exception as e:
            return self._json({"error": str(e)}, 500)
    
    def _fetch_yahoo_gainers(self):
        """Scrape Yahoo Finance top gainers for comparison."""
        try:
            import requests
            from bs4 import BeautifulSoup
            url = "https://finance.yahoo.com/gainers"
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(resp.text, 'html.parser')
            table = soup.find('table')
            if not table:
                return []
            
            rows = []
            for tr in table.find_all('tr')[1:]:
                cells = tr.find_all('td')
                if len(cells) >= 7:
                    symbol_cell = cells[0].find('a')
                    if symbol_cell:
                        symbol = symbol_cell.text.strip()
                        # Extract % change from price column
                        price_cell = cells[2].get_text(strip=True)
                        pct_match = re.search(r'\(([+-]?\d+\.?\d*)%\)', price_cell)
                        change_pct = float(pct_match.group(1)) if pct_match else 0
                        rows.append({"symbol": symbol, "change_pct": change_pct})
                        if len(rows) >= 15:
                            break
            return rows
        except:
            return []
    
    def log_message(self, format, *args):
        pass  # Suppress default logging


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 18888
    server = http.server.HTTPServer(('127.0.0.1', port), Handler)
    print(f"🦞 Prediction Server (DB-backed) on {port}")
    print(f"   Database: {DB_PATH}")
    print(f"   Endpoints: /health, /run-prediction, /agent/*, /pipeline/*, /stats, /reasoning")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.server_close()
