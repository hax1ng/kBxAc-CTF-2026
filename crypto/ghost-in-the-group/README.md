# Ghost in the Group

**Category:** Crypto · **Points:** 1000 · **Author:** HexAsh

> A custom Diffie-Hellman implementation is being used to protect a secret message. The public parameters look large enough to discourage direct attacks, but the group structure contains an important weakness. Can you analyze the group, recover the private exponent, derive the shared secret, and decrypt the protected message?

**Flag:** `kBxAc{tHE_9host_Is_ON_7H3_way_t0_the_HEl1_aNd_HeAveN_ci7y_oF_goD}`

---

## TL;DR

Finite-field Diffie-Hellman with a **badly chosen prime**. The numbers look enormous (246-bit `p`), but size isn't everything: `p − 1` factors almost entirely into small primes, so the discrete log is cheap via **Pohlig-Hellman**. Recover the client's private exponent, rebuild the shared secret, run it through the supplied HKDF, and decrypt the AES-256-GCM message.

## What We're Given

The captured handshake (`report.txt`, also packed in `ghostgroup.zip`) hands us `p`, generator `g`, both public values `A`, `B`, and all the key-derivation/decryption parameters:

```
p = 88000753428701489113490993450865560865075124813304102617544373043200000001
g = 18935151604271057755988199578124546584801734055481457746415726705868881325
A = 856648410561794340416538813121044592228714914232497557125907449024211481
B = 31388649449514431261745477998552915328450496654874229059581132104017862585

HKDF = SHA-256,  salt = 4a927d5cbda2656dd113c68d0bf48f82,  info = ghost-in-the-group/aes-gcm
AES-256-GCM,  nonce = 3aa4af98c6b9091299366131
```

Recovering `a` from `A = g^a mod p` is the **discrete logarithm problem** — which should be far too expensive in a well-chosen group. This group is not well chosen.

## The Vulnerability / Core Concept

For a prime modulus, the nonzero residues form a group of size `p − 1`. Factoring it:

```
p-1 = 2^24 · 3^12 · 5^8 · 7^6 · 11^4 · 13^3 · 17^3 · 19^2 · 23^2 · 29^2 · 31^2
      · 37 · 41 · 43 · 47 · 53 · 59 · 61 · 67 · 224723727924929
```

Although `p` is 246 bits, **almost all of `p − 1` is small primes** — the largest factor is only 48 bits. That's exactly where **Pohlig-Hellman** shines: instead of one discrete log over ~2²⁴⁶ elements, solve a handful of tiny discrete logs on the prime-power factors and glue them back together with CRT. Think of one huge combination lock that's really a stack of small independent locks. Sage also confirms `ord(g) = p − 1`, so `g` generates the full group.

## Building the Exploit

Sage's `discrete_log` performs Pohlig-Hellman for us. See [`solve.sage`](solve.sage):

```python
a = discrete_log(Mod(A, p), Mod(g, p))     # client's private exponent
assert power_mod(g, a, p) == A             # verify it reproduces A
shared_secret = power_mod(B, a, p)         # B^a == g^(ab) == shared secret
```

We only need *one* party's private exponent to recreate the shared secret. Serialise it as a 31-byte big-endian integer (246 bits → 31 bytes), feed it to HKDF-SHA256, then split the 16-byte GCM tag off the payload and decrypt:

```python
encoded_secret = int(shared_secret).to_bytes((int(p).bit_length() + 7)//8, "big")
key = HKDF(encoded_secret, 32, salt, SHA256, context=b"ghost-in-the-group/aes-gcm")
cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
plaintext = cipher.decrypt_and_verify(encrypted[:-16], encrypted[-16:])
```

## Running It

```
$ sage solve.sage
a = 53944777076991060880461909956496619677578017501388253514125195691409173417
shared secret = 36734514407515518832425967850731174205611656973964011408577534249779258717
AES key = 7d97413de22cfc672a6e88225937ebe17dc04b198e06874a558041ca412442d0
FLAG = kBxAc{tHE_9host_Is_ON_7H3_way_t0_the_HEl1_aNd_HeAveN_ci7y_oF_goD}
```

The GCM tag verifying is confirmation that the exponent, secret encoding, HKDF parameters, and ciphertext split are all correct.

## Key Takeaways

- **Large-looking parameters are not automatically secure.** For finite-field Diffie-Hellman the *structure* of the group matters as much as the size of the modulus.
- A **smooth** group order (`p − 1` made of small factors) breaks the discrete log via Pohlig-Hellman. Safe DH primes are chosen so `p − 1` has a large prime factor (ideally a safe prime `p = 2q + 1`).
- Once one private exponent is recovered, the rest of the protocol runs exactly as designed — just for the attacker too.
