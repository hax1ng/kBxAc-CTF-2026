# Weiner

**Category:** Crypto · **Points:** 1000 · **Author:** 4r$h4d0w

> Small things dont matter in life ;)

**Flag:** `kBxAc{WheN_pr!vate_KeY_!$_7oO_sMA1l_(OnTinuEd_Fr@ctioNs_cruMble_7he_WH0le_vaUL7_0pEn}`

---

## TL;DR

Classic **Wiener's attack** on RSA. We're given `n`, `e`, `c` (`chall.txt`). The private exponent `d` was chosen far too small, so `d` appears among the continued-fraction convergents of `e/n` — recover it without factoring `n` the hard way, then decrypt. The title ("Weiner") and the hint ("small things") point straight at it.

## What We're Given

Three large integers in [`chall.txt`](chall.txt) — `n` (~1024-bit modulus), `e` (public exponent, suspiciously large), and `c` (ciphertext). The private exponent `d` is missing. Recovering `d` from `n` and `e` normally means factoring `n`, which isn't practical for a 1024-bit modulus in a CTF.

## The Vulnerability / Core Concept

RSA keys satisfy `e·d ≡ 1 (mod φ(n))`, i.e. `e·d − 1 = k·φ(n)` for some integer `k`, so:

```
e / φ(n) ≈ k / d
```

For a normal modulus `φ(n)` is close to `n`, so `e/n ≈ k/d`. **Wiener's attack** uses the fact that when `d` is unusually small, the fraction `k/d` shows up among the **continued-fraction convergents** of `e/n`. Continued fractions produce a short list of especially good rational approximations, so instead of guessing an enormous key we just test each convergent.

For every convergent `k/d`:

1. Require `(e·d − 1) % k == 0`, giving a candidate `φ(n) = (e·d − 1)/k`.
2. Since `φ(n) = n − (p + q) + 1`, set `S = p + q = n − φ(n) + 1`; then `p, q` are the roots of `x² − S·x + n = 0`.
3. The discriminant `S² − 4n` must be a perfect square, and `p·q` must equal `n`.

If all checks pass, we've found the real factors and private exponent.

## Building the Exploit

Pure-Python, no crypto library needed — see [`solve.py`](solve.py):

```python
def continued_fraction(a, b):
    while b:
        yield a // b
        a, b = b, a % b

# build convergents k/d from the CF terms of e/n; test each candidate d
for term in continued_fraction(e, n):
    k = term * num_one_back + num_two_back
    d = term * den_one_back + den_two_back
    ...
    if (e * d - 1) % k: continue
    phi = (e * d - 1) // k
    S = n - phi + 1
    disc = S*S - 4*n
    if disc < 0: continue
    r = isqrt(disc)
    if r*r != disc: continue
    p, q = (S + r)//2, (S - r)//2
    if p * q != n: continue
    m = pow(c, d, n)            # decrypt
    print(m.to_bytes((m.bit_length()+7)//8, "big").decode())
```

## Running It

```
$ python3 solve.py
d = 2378116478248560756476009321494134642478824061833792867773378514405535037437
kBxAc{WheN_pr!vate_KeY_!$_7oO_sMA1l_(OnTinuEd_Fr@ctioNs_cruMble_7he_WH0le_vaUL7_0pEn}
```

That `d` looks gigantic to a human, but it's small *relative to the modulus* — which is exactly the condition Wiener's attack needs. In cryptography, size is always relative.

## Key Takeaways

- RSA doesn't become secure just because the numbers look huge — **the private exponent must also be generated safely.** If `d < n^0.25` (roughly), Wiener's attack recovers it almost instantly.
- Continued-fraction convergents turn "find a tiny `d`" into testing a short candidate list, bypassing factoring entirely.
- Verify each candidate by reconstructing `p, q` and checking `p·q == n` — this stops a random convergent from being mistaken for the answer.
