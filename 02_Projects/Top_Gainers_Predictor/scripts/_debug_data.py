"""Debug yfinance data fetching with tracebacks."""
import sys, os, traceback, json
sys.path.insert(0, r'C:\Users\pcnsl\OneDrive\Documents\openclaw\02_Projects\Top_Gainers_Predictor\scripts')
os.chdir(r'C:\Users\pcnsl\OneDrive\Documents\openclaw')

import yfinance as yf
import numpy as np
import requests
import re

# Load HF token
VAULT = os.getcwd()
text = open(os.path.join(VAULT, '03_Knowledge', 'api_keys.md'), encoding='utf-8').read()
m = re.search(r'HUGGINGFACE_TOKEN:\s+(\S+)', text)
HF_TOKEN = m.group(1) if m else ''
HF_API = "https://router.huggingface.co/hf-inference/models"
HF_MODEL = "ahmedrachid/FinancialBERT-Sentiment-Analysis"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}", "Content-Type": "application/json"}

ticker = 'AAPL'
try:
    data = yf.download(ticker, period='1mo', progress=False, auto_adjust=True)
    print(f'Data shape: {data.shape}')
    print(f'Columns type: {type(data.columns)}')
    print(f'Columns: {data.columns.tolist()}')
    
    # Handle MultiIndex
    if hasattr(data.columns, 'levels'):
        close = data.xs('Close', axis=1, level=0)
        cs = close.iloc[:, 0] if close.shape[1] > 1 else close
        cs = cs.squeeze()
        print(f'Close series type: {type(cs)}, len: {len(cs)}')
        print(f'Close values: {cs.values[:5]}')
        
        ret1 = float(cs.pct_change(1).iloc[-1]) if len(cs) > 1 else 0
        print(f'ret1: {ret1}')
    else:
        print('Single index columns')
        cs = data['Close']
        print(f'Close: {cs.values[:5]}')
        
except Exception as e:
    print(f'Error: {e}')
    traceback.print_exc()
