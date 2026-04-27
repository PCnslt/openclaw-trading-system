#!/usr/bin/env python3
"""Generate a valid n8n workflow JSON with proper UUIDs."""
import uuid, json
from datetime import datetime

uid = lambda: str(uuid.uuid4())

nodes = [
    {"id": uid(), "name": "Manual Trigger", "type": "n8n-nodes-base.manualTrigger",
     "typeVersion": 1, "position": [0, 0], "parameters": {}},
    {"id": uid(), "name": "Schedule 4PM", "type": "n8n-nodes-base.cron",
     "typeVersion": 1, "position": [0, 250], 
     "parameters": {"triggerTimes": {"item": [{"mode": "everyDay", "hour": 16, "minute": 0}]}}},
    {"id": uid(), "name": "Webhook", "type": "n8n-nodes-base.webhook",
     "typeVersion": 1, "position": [0, 500],
     "parameters": {"path": "run-pipeline", "responseMode": "responseNode", "options": {}}},
    {"id": uid(), "name": "Merge Triggers", "type": "n8n-nodes-base.merge",
     "typeVersion": 2, "position": [250, 250], "parameters": {"mode": "append"}},
    
    {"id": uid(), "name": "Agent 1: Universe", "type": "n8n-nodes-base.httpRequest",
     "typeVersion": 4.4, "position": [550, 50],
     "parameters": {"url": "http://127.0.0.1:18888/agent/universe", "method": "GET",
                    "authentication": "none", "options": {"timeout": 60000}}},
    {"id": uid(), "name": "Agent 2: Prices", "type": "n8n-nodes-base.httpRequest",
     "typeVersion": 4.4, "position": [550, 200],
     "parameters": {"url": "http://127.0.0.1:18888/agent/prices", "method": "POST",
                    "authentication": "none", "sendBody": True,
                    "bodyParameters": {"parameters": [{"name": "tickers", "value": ""}]},
                    "options": {"timeout": 120000}}},
    {"id": uid(), "name": "Agent 3: Sentiment", "type": "n8n-nodes-base.httpRequest",
     "typeVersion": 4.4, "position": [550, 350],
     "parameters": {"url": "http://127.0.0.1:18888/agent/sentiment", "method": "POST",
                    "authentication": "none", "sendBody": True,
                    "bodyParameters": {"parameters": [{"name": "tickers", "value": ""}]},
                    "options": {"timeout": 180000}}},
    {"id": uid(), "name": "Agent 4: Technicals", "type": "n8n-nodes-base.httpRequest",
     "typeVersion": 4.4, "position": [550, 500],
     "parameters": {"url": "http://127.0.0.1:18888/agent/technicals", "method": "POST",
                    "authentication": "none", "sendBody": True,
                    "bodyParameters": {"parameters": [{"name": "tickers", "value": ""}]},
                    "options": {"timeout": 180000}}},
    
    {"id": uid(), "name": "Agent 5: Merge Features", "type": "n8n-nodes-base.merge",
     "typeVersion": 2, "position": [800, 350],
     "parameters": {"mode": "combine", "combinationMode": "mergeByField",
                    "mergeByField": "ticker"}},
    
    {"id": uid(), "name": "Agent 6: Rank", "type": "n8n-nodes-base.code",
     "typeVersion": 2, "position": [1050, 350],
     "parameters": {"jsCode": 
"""const items = $input.all();
items.forEach(item => {
  const s = item.json.sentiment_score || 0;
  const m = item.json.momentum_score || 0;
  const r = item.json.rsi || 50;
  const v = item.json.volume_ratio || 1;
  const ret = item.json.return_5d || 0;
  const rsiC = (r - 50) / 50;
  const retC = Math.max(-1, Math.min(1, ret * 10));
  const volC = Math.max(-1, Math.min(1, (v - 1) * 2));
  item.json.score = rsiC * 0.20 + retC * 0.30 + volC * 0.15 + s * 0.35;
});
items.sort((a, b) => b.json.score - a.json.score);
return items.slice(0, 10).map((x, i) => ({
  json: {
    rank: i + 1,
    ticker: x.json.ticker,
    confidence: Math.round(x.json.score * 10000) / 10000,
    rsi: x.json.rsi,
    volume: x.json.volume_ratio,
    return_pct: Math.round(x.json.score * 200) / 100,
    timestamp: new Date().toISOString()
  }
}));"""}},
    
    {"id": uid(), "name": "Agent 7: Log", "type": "n8n-nodes-base.noOp",
     "typeVersion": 1, "position": [1300, 200], "parameters": {}},
    {"id": uid(), "name": "Agent 8: Summary", "type": "n8n-nodes-base.code",
     "typeVersion": 2, "position": [1300, 350],
     "parameters": {"jsCode": "const items = $input.all(); const top3 = items.slice(0,3); const msg = top3.map((x,i) => (i+1) + '. ' + x.json.ticker + ': ' + x.json.confidence).join(String.fromCharCode(10)); console.log(msg); return items;"}},
    {"id": uid(), "name": "Agent 9: Complete", "type": "n8n-nodes-base.noOp",
     "typeVersion": 1, "position": [1300, 500], "parameters": {}},
]

connections = {
    "Schedule 4PM": {"main": [[{"node": "Merge Triggers", "type": "main", "index": 0}]]},
    "Manual Trigger": {"main": [[{"node": "Merge Triggers", "type": "main", "index": 0}]]},
    "Webhook": {"main": [[{"node": "Merge Triggers", "type": "main", "index": 0}]]},
    "Merge Triggers": {"main": [[{"node": "Agent 1: Universe", "type": "main", "index": 0}]]},
    "Agent 1: Universe": {"main": [[{"node": "Agent 2: Prices", "type": "main", "index": 0}]]},
    "Agent 2: Prices": {"main": [[{"node": "Agent 3: Sentiment", "type": "main", "index": 0}, {"node": "Agent 4: Technicals", "type": "main", "index": 0}]]},
    "Agent 3: Sentiment": {"main": [[{"node": "Agent 5: Merge Features", "type": "main", "index": 0}]]},
    "Agent 4: Technicals": {"main": [[{"node": "Agent 5: Merge Features", "type": "main", "index": 1}]]},
    "Agent 5: Merge Features": {"main": [[{"node": "Agent 6: Rank", "type": "main", "index": 0}]]},
    "Agent 6: Rank": {"main": [[{"node": "Agent 7: Log", "type": "main", "index": 0}, {"node": "Agent 8: Summary", "type": "main", "index": 0}, {"node": "Agent 9: Complete", "type": "main", "index": 0}]]},
}

wf = [{
    "name": "Top Gainers Prediction - Multi-Agent Pipeline",
    "nodes": nodes,
    "connections": connections,
    "settings": {"executionOrder": "v1"},
    "active": True,
    "pinData": {},
    "versionId": str(uuid.uuid4()),
    "id": "vqbfhAVPKNJ9Aar5",
    "tags": [],
}]

path = r'C:\Users\pcnsl\OneDrive\Documents\openclaw\02_Projects\Top_Gainers_Predictor\n8n_multi_agent_workflow.json'
with open(path, 'w', encoding='utf-8') as f:
    json.dump(wf, f, indent=2, ensure_ascii=False)
print(f"Written {len(nodes)} nodes to {path}")
print(f"File size: {__import__('os').path.getsize(path)} bytes")
