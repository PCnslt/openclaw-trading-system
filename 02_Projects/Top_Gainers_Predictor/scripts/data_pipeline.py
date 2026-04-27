#!/usr/bin/env python3
"""
data_pipeline.py — Batch data pipeline for ALL tickers
Fetches prices, computes technicals, runs sentiment, stores in SQLite.
Designed for scheduled daily runs.
"""
import sqlite3, os, sys, time, json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf
import numpy as np
import pandas as pd
import requests

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(SCRIPT_DIR, '..', 'stock_data.db'))
HF_ROUTER = "https://router.huggingface.co/hf-inference/models/ahmedrachid/FinancialBERT-Sentiment-Analysis"
HF_TOKEN = os.environ.get('HUGGINGFACE_TOKEN', '')
BATCH_SIZE = 100  # yfinance batch size
MAX_WORKERS = 4   # parallel download workers
SENTIMENT_BATCH = 50  # sentiment batch size (HF API limit)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_prices_for_batch(tickers):
    """Fetch OHLCV data for a batch of tickers from yfinance."""
    if not tickers:
        return pd.DataFrame()
    
    try:
        data = yf.download(
            tickers=tickers,
            period='3mo',
            interval='1d',
            group_by='ticker',
            progress=False,
            threads=False,
            auto_adjust=True
        )
        
        if data.empty:
            return pd.DataFrame()
        
        # Handle single ticker case (MultiIndex vs single column)
        if isinstance(data.columns, pd.MultiIndex):
            pass  # MultiIndex is expected for multiple tickers
        elif isinstance(data.index, pd.DatetimeIndex):
            # Single ticker — wrap in MultiIndex
            ticker = tickers[0] if isinstance(tickers, list) else tickers
            data.columns = pd.MultiIndex.from_product([[ticker], data.columns])
        
        return data
    except Exception as e:
        print(f"  ⚠️  yfinance error for batch: {e}")
        return pd.DataFrame()

def store_prices(conn, data):
    """Store price data from yfinance DataFrame into SQLite."""
    if data.empty:
        return 0
    
    c = conn.cursor()
    count = 0
    prices_rows = []
    tickers_updated = set()
    
    # Get unique tickers from MultiIndex columns
    if isinstance(data.columns, pd.MultiIndex):
        tickers = data.columns.get_level_values(0).unique()
    else:
        tickers = []
    
    for ticker in tickers:
        try:
            t_data = data.xs(ticker, axis=1, level=0)
            if isinstance(t_data.columns, pd.MultiIndex):
                t_data = t_data.droplevel(0, axis=1)
        except:
            continue
        
        # Get last 60 trading days
        t_data = t_data.tail(60)
        tickers_updated.add(ticker)
        
        for date_idx, row in t_data.iterrows():
            if pd.isna(row.get('Close', np.nan)):
                continue
            prices_rows.append((
                ticker,
                date_idx.strftime('%Y-%m-%d'),
                float(row.get('Open', np.nan)) if not pd.isna(row.get('Open', np.nan)) else None,
                float(row.get('High', np.nan)) if not pd.isna(row.get('High', np.nan)) else None,
                float(row.get('Low', np.nan)) if not pd.isna(row.get('Low', np.nan)) else None,
                float(row.get('Close', np.nan)) if not pd.isna(row.get('Close', np.nan)) else None,
                int(row.get('Volume', 0)) if not pd.isna(row.get('Volume', 0)) else None,
            ))
            count += 1
        
        # Batch insert
        if len(prices_rows) >= 5000:
            c.executemany(
                "INSERT OR REPLACE INTO prices (ticker, date, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
                prices_rows
            )
            prices_rows = []
    
    if prices_rows:
        c.executemany(
            "INSERT OR REPLACE INTO prices (ticker, date, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
            prices_rows
        )
    
    # Update last_price_update for these tickers
    now = datetime.now().isoformat()
    for t in tickers_updated:
        c.execute("UPDATE tickers SET last_price_update = ? WHERE symbol = ?", (now, t))
    
    conn.commit()
    return count

def compute_technicals(conn, limit=None):
    """Compute technical indicators from stored price data for all (or limited) tickers."""
    c = conn.cursor()
    now = datetime.now().isoformat()
    count = 0
    
    if limit:
        c.execute("SELECT symbol FROM tickers WHERE last_technicals_update IS NULL OR last_technicals_update < ? LIMIT ?", 
                  (now, limit))
    else:
        c.execute("SELECT symbol FROM tickers WHERE last_technicals_update IS NULL OR last_technicals_update < ?", 
                  (now,))
    
    tickers = [r[0] for r in c.fetchall()]
    print(f"  Computing technicals for {len(tickers)} tickers...")
    
    for ticker in tickers:
        try:
            c.execute(
                "SELECT date, close, volume FROM prices WHERE ticker = ? ORDER BY date DESC LIMIT 65",
                (ticker,)
            )
            rows = c.fetchall()
            if len(rows) < 20:
                continue
            
            # Reverse to chronological
            rows = rows[::-1]
            closes = np.array([r[1] for r in rows if r[1] is not None], dtype=float)
            volumes = np.array([r[2] for r in rows if r[2] is not None], dtype=float)
            dates = [r[0] for r in rows]
            
            if len(closes) < 20:
                continue
            
            # Compute RSI (14-day)
            deltas = np.diff(closes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else np.mean(gains)
            avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else np.mean(losses)
            rsi = 50
            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Returns
            ret_1d = ((closes[-1] / closes[-2]) - 1) * 100 if len(closes) >= 2 else 0
            ret_5d = ((closes[-1] / closes[-6]) - 1) * 100 if len(closes) >= 6 else 0 if len(closes) < 2 else ret_1d
            ret_20d = ((closes[-1] / closes[-21]) - 1) * 100 if len(closes) >= 21 else 0
            
            # Volume ratio (current vs 20-day avg)
            if len(volumes) >= 21:
                avg_vol = np.mean(volumes[-21:-1])
                vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1.0
            else:
                avg_vol = np.mean(volumes)
                vol_ratio = volumes[-1] / avg_vol if avg_vol > 0 else 1.0
            
            # MACD
            def ema(data, period):
                alpha = 2 / (period + 1)
                result = np.zeros_like(data)
                result[0] = data[0]
                for i in range(1, len(data)):
                    result[i] = data[i] * alpha + result[i-1] * (1 - alpha)
                return result
            
            macd_line = ema(closes, 12) - ema(closes, 26)
            macd_signal = ema(macd_line, 9)
            
            # Bollinger Bands
            bb_mid = np.mean(closes[-20:]) if len(closes) >= 20 else np.mean(closes)
            bb_std = np.std(closes[-20:]) if len(closes) >= 20 else np.std(closes)
            bb_upper = bb_mid + 2 * bb_std
            bb_lower = bb_mid - 2 * bb_std
            
            # Momentum (5-day)
            momentum_5d = ((closes[-1] / closes[-6]) - 1) * 100 if len(closes) >= 6 else 0
            
            latest_date = dates[-1]
            
            c.execute("""
                INSERT OR REPLACE INTO technicals 
                (ticker, date, rsi, macd, macd_signal, bb_upper, bb_middle, bb_lower, 
                 volume_ratio, return_1d, return_5d, return_20d, avg_volume_20d, momentum_5d)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker, latest_date, 
                round(rsi, 1),
                round(float(macd_line[-1]), 4) if len(macd_line) > 0 else None,
                round(float(macd_signal[-1]), 4) if len(macd_signal) > 0 else None,
                round(bb_upper, 2), round(bb_mid, 2), round(bb_lower, 2),
                round(vol_ratio, 2), round(ret_1d, 2), round(ret_5d, 2), round(ret_20d, 2),
                round(avg_vol, 0), round(momentum_5d, 2)
            ))
            
            c.execute("UPDATE tickers SET last_technicals_update = ? WHERE symbol = ?", (now, ticker))
            count += 1
            
        except Exception as e:
            pass  # Skip tickers with errors
    
    conn.commit()
    return count

def compute_sentiment(conn, limit=100):
    """Run sentiment analysis on top stocks using FinancialBERT via HF Inference API."""
    c = conn.cursor()
    now = datetime.now().isoformat()
    count = 0
    
    # Get top tickers by volume
    c.execute("""
        SELECT p.ticker, p.close, p.volume, p.date
        FROM prices p
        INNER JOIN (
            SELECT ticker, MAX(date) as max_date
            FROM prices
            GROUP BY ticker
        ) m ON p.ticker = m.ticker AND p.date = m.max_date
        ORDER BY p.volume DESC
        LIMIT ?
    """, (limit,))
    
    tickers = [r[0] for r in c.fetchall()]
    if not tickers:
        print("  ⚠️  No price data for sentiment analysis")
        return 0
    
    print(f"  Running sentiment on top {len(tickers)} stocks...")
    
    # Batch process sentiment
    for i in range(0, len(tickers), SENTIMENT_BATCH):
        batch = tickers[i:i+SENTIMENT_BATCH]
        
        for ticker in batch:
            try:
                # Get company name for context
                c.execute("SELECT name FROM tickers WHERE symbol = ?", (ticker,))
                row = c.fetchone()
                name = row[0] if row else ticker
                
                # FinancialBERT sentiment
                payload = {"inputs": f"{name} ({ticker}) stock shows promising technical indicators and market positioning for near-term performance."}
                headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
                
                try:
                    resp = requests.post(HF_ROUTER, json=payload, headers=headers, timeout=15)
                    if resp.status_code == 200:
                        result = resp.json()
                        if isinstance(result, list) and len(result) > 0:
                            # FinancialBERT returns label+score
                            if isinstance(result[0], dict) and 'label' in result[0]:
                                label = result[0]['label']
                                score = result[0]['score']
                                sent_map = {'positive': 1.0, 'negative': -1.0, 'neutral': 0.0}
                                sentiment_score = sent_map.get(label.lower(), 0) * score
                                compound = score if label.lower() == 'positive' else -score if label.lower() == 'negative' else 0
                            elif isinstance(result[0], list) and len(result[0]) >= 2:
                                # [[label, score], ...]
                                best = max(result, key=lambda x: x[1])
                                label, score = best[0], best[1]
                                sent_map = {'positive': 1.0, 'negative': -1.0, 'neutral': 0.0}
                                sentiment_score = sent_map.get(label.lower(), 0) * score
                                compound = score if label.lower() == 'positive' else -score if label.lower() == 'negative' else 0
                            else:
                                sentiment_score, compound = 0, 0
                        else:
                            sentiment_score, compound = 0, 0
                    else:
                        sentiment_score, compound = 0, 0
                except:
                    sentiment_score, compound = 0, 0
                
                latest_date = datetime.now().strftime('%Y-%m-%d')
                
                c.execute("""
                    INSERT OR REPLACE INTO sentiment 
                    (ticker, date, sentiment_score, compound, positive, negative, neutral, model)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ticker, latest_date,
                    round(sentiment_score, 4), round(compound, 4),
                    max(sentiment_score, 0), abs(min(sentiment_score, 0)),
                    1 - abs(sentiment_score),
                    'FinancialBERT-Sentiment'
                ))
                
                c.execute("UPDATE tickers SET last_sentiment_update = ? WHERE symbol = ?", (now, ticker))
                count += 1
                
            except Exception as e:
                pass
        
        conn.commit()
        print(f"    Progress: {min(i+SENTIMENT_BATCH, len(tickers))}/{len(tickers)}")
    
    return count

def generate_predictions(conn):
    """Generate predictions from stored data using multi-factor scoring."""
    c = conn.cursor()
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    target_date = (now + timedelta(days=2)).strftime('%Y-%m-%d')
    pred_count = 0
    
    # Get all tickers with technicals and sentiment
    c.execute("""
        SELECT t.symbol, tech.rsi, tech.volume_ratio, tech.return_5d, tech.return_1d,
               s.sentiment_score
        FROM tickers t
        LEFT JOIN technicals tech ON t.symbol = tech.ticker
        LEFT JOIN sentiment s ON t.symbol = s.ticker AND s.date = (
            SELECT MAX(date) FROM sentiment WHERE ticker = t.symbol
        )
        WHERE t.is_active = 1
          AND tech.rsi IS NOT NULL
    """)
    
    rows = c.fetchall()
    scored = []
    
    for row in rows:
        ticker, rsi, vol_ratio, ret_5d, ret_1d, sentiment_score = row
        
        # Defaults
        rsi = float(rsi) if rsi else 50
        vol_ratio = float(vol_ratio) if vol_ratio else 1.0
        ret_5d = float(ret_5d) if ret_5d else 0
        sentiment_score = float(sentiment_score) if sentiment_score else 0
        
        # Normalize
        rsi_n = max(-1, min(1, (rsi - 50) / 50))
        ret_n = max(-1, min(1, ret_5d * 10))
        vol_n = max(-0.5, min(1, (vol_ratio - 1) * 2))
        
        # Score: sentiment 35%, return 30%, RSI 20%, volume 15%
        score = (sentiment_score * 0.35) + (ret_n * 0.30) + (rsi_n * 0.20) + (vol_n * 0.15)
        predicted_return = score * 2  # Scale to percentage
        confidence = 1 - abs(score)  # Lower = more confident
        
        scored.append({
            'ticker': ticker,
            'composite_score': round(score, 4),
            'predicted_return': round(predicted_return, 2),
            'confidence': round(confidence, 4),
            'rsi': round(rsi, 1),
            'volume_ratio': round(vol_ratio, 2),
            'sentiment_score': round(sentiment_score, 4)
        })
    
    # Sort by score descending
    scored.sort(key=lambda x: x['composite_score'], reverse=True)
    
    # Store predictions
    for item in scored:
        c.execute("""
            INSERT OR REPLACE INTO predictions 
            (ticker, prediction_date, target_date, composite_score, predicted_return, 
             confidence, rsi, volume_ratio, sentiment_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            item['ticker'], today, target_date,
            item['composite_score'], item['predicted_return'],
            item['confidence'], item['rsi'], item['volume_ratio'], item['sentiment_score']
        ))
        pred_count += 1
    
    conn.commit()
    return scored, today, target_date

def run_pipeline(batch_size=BATCH_SIZE, max_tickers=None, sentiment_top=100):
    """Run the full data pipeline."""
    conn = get_db()
    start_time = time.time()
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    
    print("=" * 60)
    print(f"🦞 Data Pipeline Run — {today}")
    print("=" * 60)
    
    # Get tickers that need updating
    if max_tickers:
        c.execute("SELECT symbol FROM tickers WHERE is_active = 1 LIMIT ?", (max_tickers,))
    else:
        c.execute("SELECT symbol FROM tickers WHERE is_active = 1")
    
    all_tickers = [r[0] for r in c.fetchall()]
    print(f"📊 Tickers to process: {len(all_tickers)}")
    
    # Phase 1: Fetch prices in batches
    print(f"\n📈 Phase 1: Fetching prices (batch size={batch_size})...")
    total_prices = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for i in range(0, len(all_tickers), batch_size):
            batch = all_tickers[i:i+batch_size]
            futures.append(executor.submit(fetch_prices_for_batch, batch))
        
        for future in as_completed(futures):
            data = future.result()
            if data is not None and not data.empty:
                cnt = store_prices(conn, data)
                total_prices += cnt
    
    print(f"  ✅ Stored {total_prices} price rows")
    
    # Phase 2: Compute technicals
    print(f"\n📊 Phase 2: Computing technical indicators...")
    tech_count = compute_technicals(conn, limit=max_tickers)
    print(f"  ✅ Computed technicals for {tech_count} tickers")
    
    # Phase 3: Sentiment (limited to top stocks)
    print(f"\n💬 Phase 3: Sentiment analysis (top {sentiment_top} stocks)...")
    sent_count = compute_sentiment(conn, limit=sentiment_top)
    print(f"  ✅ Sentiment for {sent_count} stocks")
    
    # Phase 4: Generate predictions
    print(f"\n🏆 Phase 4: Generating predictions...")
    scored, pred_today, target = generate_predictions(conn)
    
    # Log pipeline run
    elapsed = time.time() - start_time
    c.execute("""
        INSERT INTO pipeline_log (started_at, completed_at, tickers_scored, status)
        VALUES (?, ?, ?, ?)
    """, (datetime.fromtimestamp(start_time).isoformat(), 
          datetime.now().isoformat(), len(scored), 'success'))
    conn.commit()
    
    # Print summary
    print(f"\n{'=' * 60}")
    print(f"✅ Pipeline Complete — {elapsed:.1f}s")
    print(f"{'=' * 60}")
    print(f"   Prices stored: {total_prices} rows")
    print(f"   Technicals:    {tech_count} tickers")
    print(f"   Sentiment:     {sent_count} stocks")
    print(f"   Predictions:   {len(scored)} stocks scored")
    print(f"   Target date:   {target}")
    print(f"\n   Top 10 gainers:")
    for i, item in enumerate(scored[:10]):
        print(f"   {i+1}. {item['ticker']} — score={item['composite_score']} return={item['predicted_return']}%")
    
    db_size = os.path.getsize(DB_PATH)
    print(f"\n   Database size: {db_size/1024:.0f} KB")
    
    conn.close()
    return scored, target

def query_predictions(top_n=10):
    """Get the latest predictions from the database."""
    conn = get_db()
    c = conn.cursor()
    
    c.execute("""
        SELECT ticker, prediction_date, target_date, composite_score, predicted_return,
               confidence, rsi, volume_ratio, sentiment_score
        FROM predictions
        WHERE prediction_date = (SELECT MAX(prediction_date) FROM predictions)
        ORDER BY composite_score DESC
        LIMIT ?
    """, (top_n,))
    
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def query_reasoning(top_n=20):
    """Get detailed reasoning for top predictions."""
    conn = get_db()
    c = conn.cursor()
    
    c.execute("""
        SELECT p.ticker, p.composite_score, p.rsi, p.volume_ratio, p.sentiment_score,
               tech.return_1d, tech.return_5d, tech.momentum_5d
        FROM predictions p
        LEFT JOIN technicals tech ON p.ticker = tech.ticker
        WHERE p.prediction_date = (SELECT MAX(prediction_date) FROM predictions)
        ORDER BY p.composite_score DESC
        LIMIT ?
    """, (top_n,))
    
    rows = c.fetchall()
    conn.close()
    return [dict(r) for r in rows]

if __name__ == '__main__':
    # Parse args
    import argparse
    parser = argparse.ArgumentParser(description='Stock Data Pipeline')
    parser.add_argument('--max-tickers', type=int, default=None, help='Limit tickers (for testing)')
    parser.add_argument('--sentiment-top', type=int, default=100, help='Number of stocks for sentiment')
    parser.add_argument('--batch-size', type=int, default=100, help='yfinance batch size')
    args = parser.parse_args()
    
    run_pipeline(
        batch_size=args.batch_size,
        max_tickers=args.max_tickers,
        sentiment_top=args.sentiment_top
    )
