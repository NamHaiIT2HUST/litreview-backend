#!/usr/bin/env python3
"""
Background daemon to sweep and submit AI logs periodically.
"""
import time
import subprocess
import sys
from pathlib import Path

def main():
    interval = 60  # seconds
    print(f"[ai-log-daemon] Started auto-sync daemon (every {interval}s)...", flush=True)
    while True:
        try:
            subprocess.run([sys.executable, "scripts/log_antigravity.py", "--auto"], capture_output=True)
            res = subprocess.run([sys.executable, "scripts/submit_log.py"], capture_output=True, text=True)
            if res.stderr and "Submitted" in res.stderr:
                print(f"[ai-log-daemon] {res.stderr.strip()}", flush=True)
        except Exception as e:
            print(f"[ai-log-daemon] Error: {e}", file=sys.stderr, flush=True)
        time.sleep(interval)

if __name__ == '__main__':
    main()
