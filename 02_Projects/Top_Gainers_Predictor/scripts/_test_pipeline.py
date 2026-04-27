"""Quick test of the prediction pipeline."""
import sys, os
sys.path.insert(0, r'C:\Users\pcnsl\OneDrive\Documents\openclaw\02_Projects\Top_Gainers_Predictor\scripts')
os.chdir(r'C:\Users\pcnsl\OneDrive\Documents\openclaw')
from predict_gainers import load_universe, compute_score, fetch_yahoo_gainers

tickers = load_universe(50)
print(f'Universe: {len(tickers)} tickers loaded')

results = []
for i, t in enumerate(tickers[:30]):
    r = compute_score(t)
    if r:
        results.append(r)
        print(f'  [{i+1}/30] {t}: score={r["score"]:.4f} ret1d={r["return_1d"]:+.2f}%')

results.sort(key=lambda x: x['score'], reverse=True)
print('\n' + '=' * 60)
print('  TOP 10 PREDICTED')
print('=' * 60)
for i, r in enumerate(results[:10], 1):
    print(f'  {i:2d}. {r["ticker"]:6s} | score={r["score"]:.4f} | 1d={r["return_1d"]:+.2f}% | RSI={r["rsi"]:.0f} | Vol={r["volume_ratio"]:.2f}x | Sent={r["sentiment"]:+.4f}')

yahoo = fetch_yahoo_gainers()
print(f'\nYahoo today: {[(s, f"{p:+.2f}%") for s,p in yahoo[:5]]}')
