# Dead Validator

**Category:** Crypto · **Points:** 1000 · **Author:** HydraRoot

> Validator V17 suddenly went offline, leaving behind a bunch of data. Something feels off. Go through what's left and see if you can figure out what happened and get the flag!

**Flag:** `kBxAc{Va1!D@tor_KeY_Le@k_e(D5@_nOnce_Fin@l_paYl0ad_rEcoVeRed}`

---

## TL;DR

Validator V17 signed hundreds of transactions with ECDSA on `secp256k1`. **Two signatures share the same `r` value**, meaning the validator reused its ephemeral nonce `k`. That single mistake lets us recover `k` and the long-term private scalar `d` with a couple of lines of modular arithmetic. Two format details then matter: the ECDSA message representative is `SHA-256` of the **ASCII text** of each transaction's hex `tx_hash` (hashed *again*), and the backup's AES key is `SHA256(salt || d_as_32_big_endian_bytes || b"dead-validator")`. Derive the key, authenticate-decrypt the AES-GCM backup, read the flag.

## What We're Given

The archive ([`extracted/`](extracted/)) contains four useful files:

| File | Purpose |
|---|---|
| `chain.json` | 127 blocks containing 508 signed transactions |
| `validator.log` | Validator status and diagnostic messages |
| `wallet.pub` | The validator's PEM-encoded `secp256k1` public key |
| `validator_backup.enc` | A JSON AES-256-GCM encrypted backup |

Near the end of `validator.log`:

```
[WARN] Signature verification anomaly detected
[WARN] Multiple signatures appear to reference the same curve point
[DEBUG] This should not normally occur during independent signing operations
```

That's a loud hint toward **ECDSA nonce reuse**. The encrypted backup advertises its scheme:

```json
{ "algorithm": "AES-256-GCM", "kdf": "SHA-256",
  "nonce": "d9e6bf2ca4275c96eec82f96",
  "salt": "5631372d76616c696461746f722d6261636b75702d7632", "ciphertext": "..." }
```

The salt decodes to the ASCII string `V17-validator-backup-v2`.

## The Vulnerability / Core Concept

An ECDSA signature is `(r, s)` with `R = kG`, `r = x(R) mod n`, `s = k⁻¹(z + r·d) mod n`. Because `r` comes from the point `kG`, **two signatures made with the same nonce have the same `r`.** Grouping all 508 transactions by `r` finds exactly one duplicate:

```
r = 3d4d1342600f0fd4bfa69dd025aa6379972bdc545f835a6e13b5ffac0f55f947   (TX-084, TX-119)
```

### The double-hash gotcha

The representative `z` is **not** the raw `tx_hash` — the signer hashes the 64 printable hex characters a second time:

```python
def representative(tx):
    digest = hashlib.sha256(tx["tx_hash"].encode("ascii")).digest()
    return int.from_bytes(digest, "big")
```

Using `bytes.fromhex(tx_hash)` instead would produce the wrong `z`, and therefore the wrong private key. Getting this right is what the public-key verification step later proves.

### Recovering `k` and `d`

For the two reused-nonce signatures, subtracting the signing equations cancels the private-key term:

```
s1 - s2 = k⁻¹·(z1 - z2)  mod n   →   k = (z1 - z2)·(s1 - s2)⁻¹  mod n
```

and then either equation yields the long-term secret:

```
d = (s1·k - z1)·r⁻¹  mod n
```

```python
n  = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
k  = (z1 - z2) * pow((s1 - s2) % n, -1, n) % n
d  = (s1 * k - z1) * pow(r, -1, n) % n
```

giving `d = 92e04eb4133be7ff314c37f715850c972a27833e434edb4b0d9e5484d32cb9ab`. We independently confirm `d` by deriving its public point and comparing against `wallet.pub` — the assertion passes, so the double-hash rule and the arithmetic are both correct.

## Building the Exploit

The AES key derivation is domain-separated — the envelope only says `"kdf": "SHA-256"`, but the real input is `salt || d_bytes || b"dead-validator"` (spelling, case, and position all matter):

```python
d_bytes = d.to_bytes(32, "big")                                  # fixed width; leading zeros count
key = hashlib.sha256(salt + d_bytes + b"dead-validator").digest()
plaintext = AESGCM(key).decrypt(nonce, encrypted, None)          # also verifies the GCM tag
```

A successful `AESGCM.decrypt` confirms the key encoding, KDF order, label, nonce, and ciphertext layout all at once. Full solver: [`solve.py`](solve.py).

## Running It

```
$ python3 solve.py
repeated r: 3d4d1342600f0fd4bfa69dd025aa6379972bdc545f835a6e13b5ffac0f55f947
transactions: TX-084 and TX-119
nonce k: 9fba2a04cadaa74ece53ecf99da61a8d3cdb0878a0b7514eb8701a80be3a2b13
private d: 92e04eb4133be7ff314c37f715850c972a27833e434edb4b0d9e5484d32cb9ab
AES key: d85521765b5ffe31c570a5ba63ca972a92e2a261581ce3263357ff7997918d66
FLAG: kBxAc{Va1!D@tor_KeY_Le@k_e(D5@_nOnce_Fin@l_paYl0ad_rEcoVeRed}
```

## Key Takeaways

- **ECDSA's nonce must be unique and secret for every signature.** Reusing it once turns two public signatures into enough equations to solve for the private key.
- Read the data-format details carefully: the *double* hash of the textual `tx_hash` and the domain-separated KDF are exactly the kind of implementation specifics that silently produce a "wrong" key with no error message.
- **Verify the recovered private key against the public key before trusting it** — it's a free, decisive check that catches a mistake in either the hashing rule or the modular arithmetic.
