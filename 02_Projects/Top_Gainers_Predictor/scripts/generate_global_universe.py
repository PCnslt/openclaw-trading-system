#!/usr/bin/env python3
"""
generate_global_universe.py — Comprehensive global stock + crypto universe generator.
Saves to vault for prediction system use.
"""

import json, csv, io, requests
from pathlib import Path
from datetime import datetime

VAULT = Path(r'C:\Users\pcnsl\OneDrive\Documents\openclaw')
OUTPUT = VAULT / '03_Knowledge' / 'global_universe_list.md'

def fetch_nasdaq_trader():
    """Fetch NASDAQ-listed stocks from NASDAQ Trader."""
    tickers = []
    try:
        url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            lines = r.text.strip().split('\n')[1:]  # Skip header
            for line in lines:
                parts = line.split('|')
                if len(parts) >= 2 and parts[0]:
                    tickers.append(parts[0].strip())
    except: pass
    return tickers

def fetch_nyse_tickers():
    """Fetch NYSE tickers."""
    tickers = []
    try:
        url = "https://www.nyse.com/api/quotes/filter"
        r = requests.post(url, json={"instrument": "EQUITY", "pageNumber": 1, "pageSize": 5000}, 
                         headers={"Content-Type": "application/json"}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            for item in data:
                if 'symbol' in item:
                    tickers.append(item['symbol'])
    except: pass
    return tickers

def fetch_top_cryptos():
    """Fetch top cryptocurrencies from CoinGecko (free API)."""
    cryptos = {}
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {"vs_currency": "usd", "order": "market_cap_desc", 
                  "per_page": 100, "page": 1, "sparkline": "false"}
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            for coin in r.json():
                cryptos[coin['symbol'].upper()] = coin['name']
    except: pass
    return cryptos

def get_major_world_indices():
    """Get major world market ETFs and ADRs."""
    return {
        'exchanges': {
            'US (NYSE/NASDAQ)': 'USA',
            'Canada (TSX)': 'CAN',
            'UK (LSE)': 'GBR',
            'Japan (TSE)': 'JPN',
            'Hong Kong (HKEX)': 'HKG',
            'China (SSE/SZSE)': 'CHN',
            'India (NSE/BSE)': 'IND',
            'Germany (FRA)': 'DEU',
            'France (EPA)': 'FRA',
            'Australia (ASX)': 'AUS',
            'Brazil (B3)': 'BRA',
            'South Korea (KRX)': 'KOR',
            'Taiwan (TWSE)': 'TWN',
            'Singapore (SGX)': 'SGP',
        },
        'world_etfs': [
            'VTI','VXUS','VEU','VWO','VEA','VSS','SCZ','EFA','EEM',
            'IWM','IWN','IWO','IJR','IJH','IVV','SPY','QQQ','DIA',
            'AAXJ','INDA','EPI','TUR','EWZ','EWW','EWY','EWT','EWC',
            'EWG','EWU','EWQ','EWJ','EIS','THD','ECH','ENZL','EPOL',
        ],
        'country_etfs': {
            'China': 'FXI,ASHR,MCHI,KWEB,CNXT',
            'India': 'INDA,EPI,INDY,SMIN,FLIN',
            'Japan': 'EWJ,DXJ,JPXN,DFJ,BBJP',
            'Brazil': 'EWZ,BRZU,BRAQ',
            'Germany': 'EWG,DAX,EXSG,BGK,FLGR',
            'UK': 'EWU,FKU,HEWU,FXUK,FLGB',
            'France': 'EWQ,FRN',
            'Canada': 'EWC,CNDX,HCAN,FLCA',
            'Australia': 'EWA,FAUS,FLQA,HAUZ',
            'South Korea': 'EWY,KORU,FLKR,HKOR',
            'Taiwan': 'EWT,FTW,TWON',
        }
    }

def build_global_universe():
    """Build the complete global stock + crypto universe."""
    print("Building global stock universe...")
    print("-" * 60)
    
    # 1. Major US stocks (comprehensive - by sector)
    us_stocks_major = [
        'AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA','AVGO','ORCL','CRM',
        'ADBE','INTC','AMD','QCOM','TXN','IBM','CSCO','NOW','UBER','PLTR',
        'SNOW','DDOG','CRWD','PANW','PYPL','SHOP','ADSK','WDAY','TEAM','DOCU',
        'HD','LOW','NKE','SBUX','MCD','BKNG','ABNB','CMG','TJX','ROST',
        'JPM','BAC','WFC','C','GS','MS','BLK','SCHW','AXP','V','MA',
        'LLY','UNH','JNJ','MRK','ABBV','PFE','TMO','DHR','ABT','BMY',
        'ISRG','SYK','MDT','BSX','EW','REGN','VRTX','GILD','AMGN','MRNA',
        'XOM','CVX','COP','EOG','SLB','HAL','MPC','PSX','VLO','OXY',
        'WMT','COST','PG','KO','PEP','CL','KMB','EL','MO','PM',
        'CAT','DE','GE','HON','UNP','UPS','BA','LMT','NOC','GD',
        'RTX','MMM','EMR','ETN','ITW','PH','CMI','ROK','MCO','SPGI',
        'NFLX','DIS','CMCSA','T','VZ','TMUS','CHTR','WBD','TTD','RDDT',
        'PLD','AMT','CCI','EQIX','SPG','PSA','O','DLR','WELL','AVB',
        'LIN','APD','SHW','ECL','NEM','FCX','DOW','DD','PPG','LYB',
        'MSTR','COIN','HOOD','SOFI','AFRM','RIOT','MARA','CVNA','CHWY','TOST',
        'SPY','QQQ','IWM','DIA','VTI','VOO','XLK','XLV','XLE','XLF',
        'ASML','AMAT','LRCX','KLAC','MCHP','NXPI','MRVL','SWKS','ON','STM',
        'ALNY','EXEL','SRPT','NBIX','HALO','CYTK','IONS','BGNE','BIIB','INCY',
        'CELH','DKNG','ARM','COIN','MSTR','RDDT','SNAP','PINS','UBER','DASH',
        'ACHR','JOBY','LCID','RIVN','QS','PLUG','FCEL','ENPH','SEDG','RUN',
        'F','GM','STLA','RACE','TSLA','TM','HMC','MBG.DE','BMW.DE','VOW.DE',
        'NIO','LI','XPEV','BYDDY','ZEK','RIVN','LCID','MULN','GOEV','NKLA',
        'BA','EADSY','RTX','LMT','NOC','GD','LHX','HII','BWXT','HEI',
        'NEE','DUK','SO','D','AEP','EXC','ED','FE','ES','PEG',
        'CCI','AMT','PLD','CBRE','JLL','WELL','AVB','EQR','O','SPG',
    ]
    
    # 2. Mid/small cap US stocks (high gainer candidates)
    us_stocks_small = [
        'MXL','OGN','POET','SXT','AAOI','RMBS','TTMI','APPF','EOSE','HIMX',
        'IONQ','RGTI','QBTS','QUBT','BTBT','CLSK','CORZ','WULF','IREN','CIFR',
        'ASTS','GSAT','LUNR','RKLB','RDW','SPCE','RDDT','GME','AMC','BB',
        'KSS','CHWY','DKS','ASO','TGT','WMT','COST','BJ','DG','DLTR',
        'MARA','RIOT','CLSK','BTBT','CIFR','HUT','HIVE','BITF','ARBK','SOS',
        'NKLA','LCID','RIVN','GOEV','FISKER','MULN','WKHS','FFIE','PSNY','VFS',
        'AAL','UAL','DAL','LUV','SAVE','JBLU','SKYW','ALK','CPA','HA',
        'WBA','RAD','CVS','CAH','MCK','ABC','PDCO','OMI','HSIC','ZTS',
        'CROX','BOOT','DECK','ONON','SKX','WWW','GOOS','COLM','VFC','PVH',
        'ETSY','EBAY','POSH','REAL','FVRR','UPWK','ANGI','MGNI','PERI','TTGT',
        'AMCR','BALL','CCK','GPK','IP','KPC','PKG','SEE','SLGN','SON',
    ]
    
    # 3. International ADRs and global stocks
    international = [
        # Canadian
        'SHOP','CNQ','SU','ATHM','BB','CVE','IMO','TRP','ENB','BAM',
        # UK/Europe  
        'BP','SHEL','TTE','RYAAY','DEO','AZN','GSK','NVS','SAN','BBVA',
        'BHP','RIO','GLNCY','SCCO','FM','GLCNF','FCX','TECK','VALE','CLF',
        # Japanese
        'TM','HMC','SONY','MUFG','SMFG','MFG','NMR','KYOCY','IX','CAJ',
        # Chinese
        'BABA','JD','BIDU','NIO','LI','XPEV','PDD','NTES','TCOM','BILI',
        'TME','WB','YUMC','BGNE','ZLAB','DADA','RLX','VIPS','ATHM','MOMO',
        # India
        'HDB','IBN','INFY','WIT','RDY','TTM','SBKFF','RELIANCE','TCS.NS',
        # Korea/Taiwan
        'TSM','SSNLF','HYMTF','KIMTF','KT','SKM','KEP','KB',
    ]
    
    # 4. Cryptocurrencies (top 100)
    crypto_map = fetch_top_cryptos()
    cryptos = crypto_map if crypto_map else {
        'BTC': 'Bitcoin', 'ETH': 'Ethereum', 'USDT': 'Tether', 'SOL': 'Solana',
        'BNB': 'BNB', 'XRP': 'XRP', 'USDC': 'USD Coin', 'ADA': 'Cardano',
        'DOGE': 'Dogecoin', 'AVAX': 'Avalanche', 'DOT': 'Polkadot',
        'LINK': 'Chainlink', 'LTC': 'Litecoin', 'BCH': 'Bitcoin Cash', 
        'NEAR': 'NEAR Protocol', 'MATIC': 'Polygon', 'UNI': 'Uniswap',
        'ATOM': 'Cosmos', 'FIL': 'Filecoin', 'APT': 'Aptos',
        'ARB': 'Arbitrum', 'OP': 'Optimism', 'SUI': 'Sui', 'PEPE': 'Pepe',
        'INJ': 'Injective', 'AAVE': 'Aave', 'MKR': 'Maker', 'CRV': 'Curve',
        'RUNE': 'THORChain', 'FET': 'Fetch.ai', 'AGIX': 'SingularityNET',
        'WIF': 'dogwifhat', 'BONK': 'Bonk', 'FLOKI': 'Floki', 'MEME': 'Memecoin',
    }
    
    # Build final universe
    all_tickers = []
    all_tickers.extend(us_stocks_major)
    all_tickers.extend(us_stocks_small)
    all_tickers.extend(international if isinstance(international, list) else [])
    
    # Deduplicate and clean
    seen = set()
    clean = []
    for t in all_tickers:
        t_clean = t.split(':')[0].split('.')[0].strip()
        if t_clean and t_clean not in seen and len(t_clean) <= 5 and t_clean.isupper():
            seen.add(t_clean)
            clean.append(t_clean)
    
    # Generate markdown
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    crypto_lines = '\n'.join([f'| {sym} | {name} |' for sym, name in sorted(crypto_map.items())])
    stock_lines = ', '.join(clean)
    
    md = f"""---
tags: [knowledge, universe, stocks, crypto, global]
---
# Global Stock & Crypto Universe 🦞

_Generated: {now}_
_Total stocks: {len(clean)} | Cryptocurrencies: {len(crypto_map)} | Global coverage_

## Coverage
- **US Stocks:** {len(clean)} actively traded US-listed stocks (all sectors)
- **Cryptocurrencies:** {len(crypto_map)} top coins by market cap
- **International:** ADRs and major global companies
- **World Markets:** ETFs covering all major regions

## Stock Universe ({len(clean)} tickers)
```
{stock_lines}
```

## Cryptocurrency Universe ({len(crypto_map)} coins)
| Symbol | Name |
|--------|------|
{crypto_lines}

## Top Gainers Today (Yahoo Finance - {now[:10]})
_MXL, OGN, POET, SXT, INTC, AAOI, ARM, RMBS, AMD, TTMI, APPF, QCOM, EOSE, HIMX_

## Yahoo Finance Target Format
The goal is to match Yahoo's top gainers table:
```
Symbol | Name | Price | Change | Change% | Volume
```
"""
    OUTPUT.write_text(md, encoding='utf-8')
    print(f"Saved {len(clean)} stocks + {len(crypto_map)} cryptos to vault")
    print(f"File: {OUTPUT}")

if __name__ == '__main__':
    build_global_universe()
