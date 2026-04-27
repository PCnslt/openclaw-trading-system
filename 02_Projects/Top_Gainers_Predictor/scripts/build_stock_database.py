#!/usr/bin/env python3
"""
build_stock_database.py — Build SQLite database from FinanceDatabase CSVs
Creates the stock database with ALL US equities for prediction pipeline.
"""
import sqlite3, csv, os, json, sys
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'stock_data.db')
DB_PATH = os.path.normpath(DB_PATH)

FD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '03_Knowledge', 'FinanceDatabase')
FD_PATH = os.path.normpath(FD_PATH)

def init_db():
    """Create SQLite database with full schema."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.executescript('''
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        PRAGMA cache_size=-64000;  -- 64MB cache
        
        CREATE TABLE IF NOT EXISTS tickers (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            exchange TEXT,
            sector TEXT,
            industry TEXT,
            country TEXT,
            market_cap TEXT,
            is_active INTEGER DEFAULT 1,
            last_price_update TEXT,
            last_technicals_update TEXT,
            last_sentiment_update TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        
        CREATE TABLE IF NOT EXISTS prices (
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        );
        
        CREATE TABLE IF NOT EXISTS technicals (
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            rsi REAL,
            macd REAL,
            macd_signal REAL,
            bb_upper REAL,
            bb_middle REAL,
            bb_lower REAL,
            volume_ratio REAL,
            return_1d REAL,
            return_5d REAL,
            return_20d REAL,
            avg_volume_20d REAL,
            momentum_5d REAL,
            PRIMARY KEY (ticker, date)
        );
        
        CREATE TABLE IF NOT EXISTS sentiment (
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            sentiment_score REAL,
            compound REAL,
            positive REAL,
            negative REAL,
            neutral REAL,
            model TEXT,
            PRIMARY KEY (ticker, date)
        );
        
        CREATE TABLE IF NOT EXISTS predictions (
            ticker TEXT NOT NULL,
            prediction_date TEXT NOT NULL,
            target_date TEXT NOT NULL,
            composite_score REAL,
            predicted_return REAL,
            confidence REAL,
            rsi REAL,
            volume_ratio REAL,
            sentiment_score REAL,
            actual_return REAL,
            PRIMARY KEY (ticker, prediction_date)
        );
        
        CREATE TABLE IF NOT EXISTS pipeline_log (
            run_id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT,
            completed_at TEXT,
            tickers_scored INTEGER,
            status TEXT,
            error TEXT
        );
        
        CREATE INDEX IF NOT EXISTS idx_prices_ticker ON prices(ticker);
        CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);
        CREATE INDEX IF NOT EXISTS idx_technicals_ticker ON technicals(ticker);
        CREATE INDEX IF NOT EXISTS idx_sentiment_ticker ON sentiment(ticker);
        CREATE INDEX IF NOT EXISTS idx_predictions_date ON predictions(prediction_date);
    ''')
    
    conn.commit()
    return conn

def load_us_equities(conn):
    """Load ALL US equities from FinanceDatabase CSV into tickers table."""
    equity_csv = os.path.join(FD_PATH, 'equities.csv')
    if not os.path.exists(equity_csv):
        print(f"❌ FinanceDatabase not found at: {equity_csv}")
        return 0
    
    c = conn.cursor()
    
    # Count existing
    c.execute("SELECT COUNT(*) FROM tickers")
    existing = c.fetchone()[0]
    if existing > 0:
        print(f"ℹ️  Database already has {existing} tickers. Skipping load.")
        print(f"   To reload, delete {DB_PATH}")
        return existing
    
    print(f"📂 Loading from: {equity_csv}")
    
    # Major US exchanges
    us_exchanges = {'NAS', 'NMS', 'NYQ', 'NYS', 'ASE', 'PCX', 'NGM', 'NCM'}
    
    rows = []
    with open(equity_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['country'] == 'United States' and row['exchange'] in us_exchanges:
                rows.append((
                    row['symbol'],
                    row['name'][:200] if row['name'] else '',
                    row['exchange'],
                    row.get('sector', ''),
                    row.get('industry', ''),
                    row['country'],
                    row.get('market_cap', ''),
                    1  # is_active
                ))
    
    c.executemany(
        "INSERT OR IGNORE INTO tickers (symbol, name, exchange, sector, industry, country, market_cap, is_active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    
    print(f"✅ Loaded {len(rows)} US equities into database")
    
    # Print breakdown
    exchanges = {}
    for r in rows:
        ex = r[2]
        exchanges[ex] = exchanges.get(ex, 0) + 1
    for ex, cnt in sorted(exchanges.items(), key=lambda x: -x[1]):
        print(f"   {ex}: {cnt}")
    
    return len(rows)

def print_stats(conn):
    """Print database statistics."""
    c = conn.cursor()
    tables = ['tickers', 'prices', 'technicals', 'sentiment', 'predictions']
    for t in tables:
        c.execute(f"SELECT COUNT(*) FROM {t}")
        cnt = c.fetchone()[0]
        print(f"   {t}: {cnt:,} rows")
    
    c.execute("SELECT COUNT(*) FROM tickers WHERE last_price_update IS NOT NULL")
    priced = c.fetchone()[0]
    print(f"   tickers with price data: {priced}")
    
    c.execute("SELECT MIN(date), MAX(date) FROM prices")
    d = c.fetchone()
    if d[0]:
        print(f"   price date range: {d[0]} to {d[1]}")

if __name__ == '__main__':
    print("=" * 60)
    print("🦞 Stock Database Builder")
    print("=" * 60)
    print(f"📁 DB Path: {DB_PATH}")
    print(f"📁 FD Path: {FD_PATH}")
    print()
    
    conn = init_db()
    print("✅ Database schema created")
    
    total = load_us_equities(conn)
    
    print()
    print("📊 Database Stats:")
    print_stats(conn)
    print()
    print(f"✅ Database ready at: {DB_PATH}")
    conn.close()
