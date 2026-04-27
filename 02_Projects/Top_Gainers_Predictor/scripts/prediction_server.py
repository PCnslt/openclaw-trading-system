#!/usr/bin/env python3
"""
prediction_server.py — Simple HTTP server that n8n calls to trigger the prediction pipeline.

Runs on port 18888. n8n sends GET /run-prediction to trigger a pipeline run.
Returns JSON with the top 10 predictions.

Usage: python prediction_server.py (starts in background)
"""

import http.server
import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

VAULT_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_DIR = Path(__file__).resolve().parent
PYTHON = r"C:\Users\pcnsl\AppData\Local\Programs\Python\Python312\python.exe"
os.chdir(VAULT_ROOT)

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/run-prediction":
            self.run_prediction()
        elif self.path == "/health":
            self.respond(200, {"status": "ok"})
        else:
            self.respond(404, {"error": "not found"})
    
    def run_prediction(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        try:
            # Run the prediction pipeline
            script = SCRIPTS_DIR / "predict_gainers.py"
            result = subprocess.run(
                [PYTHON, "-X", "utf8", str(script)],
                capture_output=True, text=True, timeout=300,
                cwd=VAULT_ROOT
            )
            
            # Extract JSON_OUTPUT
            output = None
            for line in result.stdout.split("\n"):
                if line.startswith("JSON_OUTPUT:"):
                    output = json.loads(line[12:])
                    break
            
            if output is None:
                # Try parsing full stdout
                try:
                    output = json.loads(result.stdout)
                except:
                    output = {"error": "parse_failed", "stdout": result.stdout[-500:], "stderr": result.stderr[-500:]}
            
            self.wfile.write(json.dumps(output, indent=2).encode("utf-8"))
            
        except subprocess.TimeoutExpired:
            self.wfile.write(json.dumps({"error": "timeout"}).encode("utf-8"))
        except Exception as e:
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
    
    def respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
    
    def log_message(self, format, *args):
        pass  # Suppress HTTP log output

if __name__ == "__main__":
    port = 18888
    server = http.server.HTTPServer(("127.0.0.1", port), Handler)
    print(f"Prediction server on http://127.0.0.1:{port}")
    print("n8n workflow -> GET /run-prediction -> returns JSON")
    server.serve_forever()
