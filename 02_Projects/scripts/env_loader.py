#!/usr/bin/env python3
"""
env_loader.py — Load API keys from Obsidian vault's api_keys.md file.
Never hardcodes keys. Never prints them. Reads from vault only.

Usage:
    from env_loader import get_api_key, get_all_keys

    news_key = get_api_key("NEWSAPI_ORG_API_KEY")
    binance_key = get_api_key("BINANCE_US_API_KEY")
"""

import os
import re
import json
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parents[2]
API_KEYS_FILE = VAULT_ROOT / "03_Knowledge" / "api_keys.md"

def parse_api_keys(filepath=None):
    """Parse API keys from vault markdown file. Returns dict."""
    if filepath is None:
        filepath = API_KEYS_FILE
    
    if not filepath.exists():
        return {}
    
    text = filepath.read_text(encoding="utf-8")
    keys = {}
    
    # Pattern: matches "- KEY_NAME: value" or "- KEY_NAME: value\n" 
    for line in text.split("\n"):
        line = line.strip()
        # Match lines like "- KEY_NAME: value"
        match = re.match(r"-\s*([A-Z_][A-Z_0-9]+)\s*:\s*(.+)$", line)
        if match:
            key_name = match.group(1)
            value = match.group(2).strip()
            # Skip placeholders
            if value.lower() in ["_(not set)_", "_(set)_", "none", "null", ""]:
                continue
            keys[key_name] = value
    
    return keys

def get_api_key(name, default=None):
    """Get a specific API key by name."""
    keys = parse_api_keys()
    return keys.get(name, default)

def get_all_keys():
    """Get all parsed API keys (use carefully - never print/leak)."""
    return parse_api_keys()

def get_env_dict():
    """Get dict suitable for setting environment variables."""
    return parse_api_keys()

def create_dotenv(filepath=None):
    """Create/update a .env file from vault keys (never commit this)."""
    if filepath is None:
        filepath = VAULT_ROOT / ".env"
    
    keys = parse_api_keys()
    
    # Read existing .env to preserve manual entries
    existing = {}
    if filepath.exists():
        for line in filepath.read_text().split("\n"):
            if "=" in line:
                k, v = line.split("=", 1)
                existing[k.strip()] = v.strip()
    
    # Merge: vault keys override, existing preserved if not in vault
    merged = {**existing, **keys}
    
    content = "# Auto-generated from vault api_keys.md\n"
    content += f"# Last updated: {__import__('datetime').datetime.now()}\n\n"
    for k, v in sorted(merged.items()):
        content += f"{k}={v}\n"
    
    filepath.write_text(content)
    return filepath

if __name__ == "__main__":
    # Test: load keys and print count (not values)
    keys = parse_api_keys()
    print(f"Loaded {len(keys)} API keys from vault")
    print(f"Available keys: {', '.join(sorted(keys.keys()))}")
    
    # Check for key ones we need
    needed = ["NEWSAPI_ORG_API_KEY", "ALPHAVANTAGE_API_KEY", 
              "FMP_API_KEY", "BINANCE_US_API_KEY", "BINANCE_US_SECRET_KEY",
              "OPENAI_API_KEY"]
    for key in needed:
        status = "[OK]" if key in keys else "[MISS]"
        print(f"  {status} {key}")
