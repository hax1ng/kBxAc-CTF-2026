import os
import re
import subprocess
import time

from flask import (Flask, Response, jsonify, render_template, request,
                   session)

app = Flask(__name__)
app.secret_key = os.urandom(32)

LEDGERD = os.environ.get("LEDGERD_PATH", "/opt/boe/bin/ledgerd")

MAX_FIELD_LEN = 16

_RATE = {}
RATE_LIMIT, RATE_WINDOW = 10, 10.0


def _rate_ok(ip: str) -> bool:
    now = time.time()
    hits = [t for t in _RATE.get(ip, []) if now - t < RATE_WINDOW]
    hits.append(now)
    _RATE[ip] = hits
    return len(hits) <= RATE_LIMIT


def _valid_field(value: str) -> bool:
    if value is None:
        return False
    if len(value) > MAX_FIELD_LEN:
        return False
    if not value.isprintable():
        return False
    return True


@app.before_request
def ensure_session():
    session.setdefault("role", "guest")
    session.setdefault("branch", "HQ-01")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/vault/auth", methods=["POST"])
def vault_auth():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "?")
    if not _rate_ok(ip):
        return jsonify(ok=False, error="Rate limit exceeded. Try again shortly."), 429

    data = request.get_json(silent=True) or request.form
    user = (data.get("user") or "").strip()
    pw   = (data.get("pass") or "").strip()

    if re.search(r"('|--|\bunion\b|\bor\b\s+\d+=\d+)", (user + pw), re.I):
        return jsonify(ok=False,
                       error="Intrusion attempt logged. Nice try."), 200

    if not (_valid_field(user) and _valid_field(pw)):
        return jsonify(ok=False,
                       error="Invalid branch credentials."), 400

    frame = f"{user}|{pw}\n"
    try:
        proc = subprocess.run(
            [LEDGERD],
            input=frame,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=5,
        )
        out = proc.stdout
    except Exception as exc:
        return jsonify(ok=False, error=f"Ledger daemon error: {exc}"), 500

    unlocked = "VAULT SEAL INTEGRITY VERIFIED" in out
    return jsonify(ok=unlocked, ledger=out), 200


@app.route("/robots.txt")
def robots():
    return Response("User-agent: *\nDisallow: /admin\n",
                    mimetype="text/plain")


@app.route("/admin", methods=["GET"])
def admin_login():
    return Response(
        """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">
<html><head><meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1">
<title>Bank of Endia - Staff Login</title></head>
<body bgcolor="#C0C0C0" text="#000000">
<center><table width="480" cellpadding="10" cellspacing="0" border="2" bgcolor="#FFFFFF"><tr><td>
<center><font face="Times New Roman, serif" size="4"><b>BANK OF ENDIA</b></font><br>
<font face="Arial, sans-serif" size="2">The Most Secure Bank of Endia<br><b>Staff Login — Branch Managers Only</b></font></center>
<hr>
<form method="POST" action="/admin">
<font face="Arial, sans-serif" size="2"><b>Username:</b></font><br>
<input name="username" type="text" size="20" maxlength="32"><br><br>
<font face="Arial, sans-serif" size="2"><b>Password:</b></font><br>
<input name="password" type="password" size="20" maxlength="32"><br><br>
<input type="submit" value=" Login ">
</form>
<hr>
<font face="Arial, sans-serif" size="1">Failed logins are reported to the branch security office.<br>
Last updated: March 12, 1998</font>
</td></tr></table></center>
</body></html>""",
        mimetype="text/html",
    )


@app.route("/admin", methods=["POST"])
def admin_auth():
    data = request.get_json(silent=True) or request.form
    username = (data.get("username") or data.get("user") or "").strip()
    password = (data.get("password") or data.get("pass") or "").strip()
    blob = f"{username} {password}"
    if re.search(r"('|--|\bunion\b|\bselect\b|\bor\b\s+\d+=\d+|\bor\b\s+['\"]?\w+['\"]?\s*=\s*['\"]?\w+)", blob, re.I):
        return jsonify(ok=False,
                       error="Intrusion attempt logged. Incident #BOE-1998-0042. Nice try."), 200
    if not username or not password:
        return jsonify(ok=False,
                       error="Missing staff credentials."), 400
    return jsonify(ok=False,
                   error="Forbidden. Invalid staff credentials. This endpoint requires role=branch-manager."), 403


@app.route("/health")
def health():
    return jsonify(status="ok", daemon="ledgerd/3.2")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
