---
tags: [knowledge, universe, financedatabase, symbols]
---
# FinanceDatabase Global Symbol Universe 🦞

_Source: https://github.com/JerBouma/FinanceDatabase_
_Downloaded: 2026-04-26_

## Summary

| Asset Class | Symbols | File |
|------------|---------|------|
| Equities (Stocks) | ~158,429 | `03_Knowledge/FinanceDatabase/equities.csv` |
| Indices | ~91,183 | `03_Knowledge/FinanceDatabase/indices.csv` |
| Funds | ~57,881 | `03_Knowledge/FinanceDatabase/funds.csv` |
| ETFs | ~36,786 | `03_Knowledge/FinanceDatabase/etfs.csv` |
| Cryptocurrencies | ~3,367 | `03_Knowledge/FinanceDatabase/cryptos.csv` |
| Currencies (Forex) | ~2,556 | `03_Knowledge/FinanceDatabase/currencies.csv` |
| Money Markets | ~1,367 | `03_Knowledge/FinanceDatabase/moneymarkets.csv` |

**Total: ~351,569 symbols across all asset classes**

## Usage in Pipeline

The prediction pipeline (`scripts/predict_gainers.py`) uses:
- **US Equities**: Filtered from `equities.csv` (Country = "United States")
- **Global Equities**: All entries from `equities.csv`
- **Cryptos**: All entries from `cryptos.csv`
- **ETFs**: Filtered US-traded from `etfs.csv`

## Integration Script

```python
import pandas as pd
# Load universe
equities = pd.read_csv('03_Knowledge/FinanceDatabase/equities.csv')
us_stocks = equities[equities['Country'] == 'United States']
# Get symbols list
tickers = us_stocks['Symbol'].dropna().unique().tolist()
```
