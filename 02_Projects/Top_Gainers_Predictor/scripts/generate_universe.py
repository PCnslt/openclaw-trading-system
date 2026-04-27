#!/usr/bin/env python3
"""Generate comprehensive stock universe and save to vault."""
import json
from pathlib import Path

VAULT = Path(r'C:\Users\pcnsl\OneDrive\Documents\openclaw')

# Core universe: actively traded US stocks by sector
tickers = [
    # Tech Mega-cap (10)
    'AAPL','MSFT','GOOGL','AMZN','NVDA','META','TSLA','AVGO','ORCL','CRM',
    # Tech (20)
    'ADBE','INTC','AMD','QCOM','TXN','IBM','CSCO','NOW','UBER','PLTR',
    'SNOW','DDOG','CRWD','PANW','PYPL','SHOP','ADSK','WDAY','TEAM','DOCU',
    # Consumer Cyclical (15)
    'HD','LOW','NKE','SBUX','MCD','BKNG','ABNB','CMG','TJX','ROST',
    'DG','DLTR','EBAY','MAR','HLT',
    # Financial (18)
    'JPM','BAC','WFC','C','GS','MS','BLK','SCHW','AXP','V','MA',
    'COF','USB','PNC','MET','PRU','AIG','BRK.B',
    # Healthcare (18)
    'LLY','UNH','JNJ','MRK','ABBV','PFE','TMO','DHR','ABT','BMY',
    'ISRG','SYK','MDT','BSX','EW','REGN','VRTX','GILD','AMGN','MRNA',
    # Energy (14)
    'XOM','CVX','COP','EOG','SLB','HAL','MPC','PSX','VLO','OXY',
    'DVN','FANG','HES','APA',
    # Consumer Defensive (12)
    'WMT','COST','PG','KO','PEP','CL','KMB','EL','MO','PM',
    'CAG','KHC','SJM','GIS','CPB','HRL','SYY','MDLZ',
    # Industrial (14)
    'CAT','DE','GE','HON','UNP','UPS','BA','LMT','NOC','GD',
    'RTX','MMM','EMR','ETN','ITW','PH','CMI','ROK','IR',
    # Comm Services (12)
    'NFLX','DIS','CMCSA','T','VZ','TMUS','CHTR','WBD','PARA','FOXA',
    'OMC','IPG','PINS','TTD','RDDT',
    # Real Estate (12)
    'PLD','AMT','CCI','EQIX','SPG','PSA','O','DLR','WELL','AVB',
    'EQR','MAA','ESS','UDR','HST','BXP','KIM',
    # Materials (10)
    'LIN','APD','SHW','ECL','NEM','FCX','DOW','DD','PPG','LYB',
    'MLM','VMC','IP','ALB',
    # Crypto/High Beta (12)
    'MSTR','COIN','HOOD','SOFI','AFRM','RIOT','MARA','CVNA','CHWY','TOST',
    'DKNG','CELH',
    # ETFs (15)
    'SPY','QQQ','IWM','DIA','VTI','VOO','VGT','XLK','XLV','XLE',
    'XLF','XLI','XLP','XLU','XLB','XLRE','XLY','VWO','EEM','ARKK',
    # ADRs (8)
    'TSM','BABA','JD','BIDU','NIO','LI','HDB','INFY',
    # Biotech (10)
    'ALNY','EXEL','SRPT','NBIX','HALO','CYTK','IONS','BGNE','FOLD','TWST',
    # Semis (8)
    'ASML','AMAT','LRCX','KLAC','MCHP','NXPI','MRVL','SWKS',
]

# Deduplicate
seen = set()
universe = []
for t in tickers:
    if t not in seen:
        seen.add(t)
        universe.append(t)

# Save markdown
md = f"""---
tags: [knowledge, universe, stocks]
---
# Stock Universe List 🦞
_Generated: 2026-04-26_

## Summary
- **Total tickers:** {len(universe)}
- **Exchanges:** NYSE, NASDAQ
- **Sectors:** All major sectors (Tech, Financial, Healthcare, Energy, etc.)

## By Sector

| Sector | Count | Tickers |
|--------|-------|---------|
| Tech Mega-cap | 10 | AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA, AVGO, ORCL, CRM |
| Tech | 20 | ADBE, INTC, AMD, QCOM, TXN, IBM, CSCO, NOW, UBER, PLTR, SNOW... |
| Financial | 18 | JPM, BAC, WFC, C, GS, MS, BLK, SCHW, AXP, V, MA... |
| Healthcare | 20 | LLY, UNH, JNJ, MRK, ABBV, PFE, TMO, DHR, ABT, BMY... |
| Energy | 14 | XOM, CVX, COP, EOG, SLB, HAL, MPC, PSX, VLO, OXY... |
| Consumer | 27 | WMT, COST, PG, KO, PEP, HD, LOW, NKE, SBUX, MCD... |
| Industrial | 19 | CAT, DE, GE, HON, UNP, UPS, BA, LMT, NOC, GD... |
| Comm Services | 15 | NFLX, DIS, CMCSA, T, VZ, TMUS, CHTR, WBD, PARA... |
| Real Estate | 18 | PLD, AMT, CCI, EQIX, SPG, PSA, O, DLR, WELL, AVB... |
| Materials | 13 | LIN, APD, SHW, ECL, NEM, FCX, DOW, DD, PPG, LYB... |
| Crypto/Beta | 12 | MSTR, COIN, HOOD, SOFI, AFRM, RIOT, MARA, CVNA... |
| ETFs | 20 | SPY, QQQ, IWM, DIA, VTI, VOO, VGT, XLK, XLV, XLE... |
| Biotech | 10 | ALNY, EXEL, SRPT, NBIX, HALO, CYTK, IONS, BGNE... |
| Semis | 8 | ASML, AMAT, LRCX, KLAC, MCHP, NXPI, MRVL, SWKS |

## Full Ticker List ({len(universe)} total)
```
{','.join(universe)}
```
"""
(VAULT / '03_Knowledge' / 'universe_list.md').write_text(md)
print(f'Saved {len(universe)} tickers to vault')
print(','.join(universe))
