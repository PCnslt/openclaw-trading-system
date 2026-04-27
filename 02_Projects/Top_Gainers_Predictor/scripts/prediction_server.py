#!/usr/bin/env python3
"""
prediction_server.py — Lightweight HTTP server for n8n webhook triggers.
Calls the prediction pipeline directly (no subprocess).
"""

import http.server, json, sys, os, io, contextlib
from pathlib import Path

VAULT = Path(__file__).resolve().parents[3]
SCRIPTS = Path(__file__).resolve().parent
os.chdir(VAULT)
sys.path.insert(0, str(SCRIPTS))

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/run-prediction":
            self.run()
        elif self.path == "/health":
            self.send_json(200, {"status": "ok"})
        else:
            self.send_json(404, {"error": "not found"})
    
    def run(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        
        # Capture stdout and run the pipeline
        f = io.StringIO()
        output = {}
        try:
            with contextlib.redirect_stdout(f):
                from predict_gainers import main
                main()
            # Extract JSON output
            for line in f.getvalue().split("\n"):
                if line.startswith("JSON_OUTPUT:"):
                    output = json.loads(line[12:])
                    break
            if not output:
                output = {"stdout": f.getvalue()[-1000:]}
        except Exception as e:
            output = {"error": str(e), "traceback": __import__('traceback').format_exc()}
        
        self.wfile.write(json.dumps(output, indent=2, default=str).encode("utf-8"))
    
    def send_json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))
    
    def log_message(self, *args): pass

if __name__ == "__main__":
    port = 18888
    srv = http.server.HTTPServer(("127.0.0.1", port), Handler)
    print(f"Prediction server on http://127.0.0.1:{port}")
    print(f"GET /run-prediction -> runs real pipeline")
    print(f"GET /health -> health check")
    srv.serve_forever()
