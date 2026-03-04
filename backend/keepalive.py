#!/usr/bin/env python3
"""Keep Railway backend warm by pinging /health every 4 minutes."""
import requests
import time

URL = "https://legacy-lens-production-5e14.up.railway.app/health"

while True:
    try:
        resp = requests.get(URL, timeout=10)
        print(f"{time.strftime('%H:%M:%S')} — {resp.status_code} {resp.json()}")
    except Exception as e:
        print(f"{time.strftime('%H:%M:%S')} — ERROR: {e}")
    time.sleep(240)  # ping every 4 minutes
