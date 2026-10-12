# Icarus Enclave

**Category:** Crypto · **Points:** 1000 · **Author:** HexAsh

> At 03:17, the Icarus Enclave went silent. The system was found partially wiped, leaving behind a single image and a sealed recovery package... "If you found this, the recovery chain has already begun."

**Flag:** `kBxAc{7HE_one_F@Ult_open5_EV3Ry_L4Yer_OF_7he_iCARUs_Re(0V3ry_(Hain}`

---

## TL;DR

A four-stage recovery chain, each stage handing you the key to the next:

1. A **Base65536** string hidden in the PNG's Unicode comment decodes to the 16 raw bytes that are the password for the encrypted ZIP.
2. A deliberately **faulty RSA-CRT signature** lets one `gcd` factor the modulus and recover the private key.
3. That private key (via HKDF) opens an **AES-256-GCM** recovery vault.
4. The vault authenticates with `SHA-256(secret || message)`, so a **length-extension attack** forges a token that is itself the key material for the final AES-GCM decryption.

[`solve.py`](solve.py) automates stages 2–5; stage 1 is a quick manual decode described below.

## Stage 1 — Base65536 hidden in the image

The archive held `IMG_0427.png` (a couple of plain teal rectangles — no useful LSB) and a password-protected `icarus-enclave.zip`. The metadata is the interesting part:

```bash
exiftool -a -u -g1 IMG_0427.png
# Comment: \U00020E53\U000253D1\U00009439\U000283BF\U00024559\U00024977\U000241EA\U0000A5F3
```

Eight very high, unusual Unicode code points → a strong tell for **Base65536** (like Base64, but each character carries two bytes instead of six bits). Decoding:

```javascript
import { decode } from "base65536";
const hidden = String.fromCodePoint(0x20E53,0x253D1,0x09439,0x283BF,0x24559,0x24977,0x241EA,0x0A5F3);
console.log(Buffer.from(decode(hidden)).toString("hex"));   // 5388d1cd395fbffd59bf77c3eabbf36d
```

Crucially this is the **hex display of a 16-byte password** — the ZIP password is the raw binary, not the 32-character text:

```python
password = bytes.fromhex("5388d1cd395fbffd59bf77c3eabbf36d")
# zipfile.ZipFile(...).read(name, pwd=password)  -> challenge.json, recovery_vault.json, task.txt
```

The extracted `challenge.json` and `recovery_vault.json` are included under [`extracted/`](extracted/).

## Stage 2 — The faulty RSA-CRT signature

`challenge.json` labels its algorithm `icarus-rsa-crt-fault-v1` and supplies `n`, `e = 65537`, a message, a correct signature, and a faulty signature of the same message.

RSA-CRT speeds up signing by computing modulo `p` and `q` separately and recombining. If a fault corrupts only one half, the faulty signature is correct mod one prime but wrong mod the other — so the difference between the correct and faulty signatures is a multiple of one secret prime, and **one `gcd` factors `n`:**

```python
p = math.gcd(n, correct_sig - faulty_sig)
q = n // p
d = pow(e, -1, (p - 1) * (q - 1))
```

One broken signature leaks the entire private key. This is a classic reason RSA-CRT implementations must verify their output before releasing it.

## Stage 3 — Opening the recovery vault

`recovery_vault.json` is AES-256-GCM with HKDF-SHA256 key derivation. The input key material is the recovered private exponent `d` serialised as an unsigned **128-byte big-endian** integer:

```python
key = HKDF(algorithm=SHA256(), length=32, salt=salt, info=b"icarus-enclave/recovery-v1").derive(d.to_bytes(128, "big"))
vault_plain = AESGCM(key).decrypt(nonce, ciphertext, None)
```

The vault reveals the final authentication mechanism: `SHA-256(secret || message)` with a 32-byte secret, a known message/tag, and some text to append.

## Stage 4 — SHA-256 length extension

`SHA-256(secret || message)` is **not** a secure MAC. SHA-256's final digest *is* its internal state, so knowing the original message, its tag, and the secret's length lets you continue hashing and forge a valid tag for `secret || message || padding || attacker_data` — without ever learning the secret.

Here the secret is 32 bytes and the message 28 bytes (60 bytes processed before padding). `solve.py` reimplements the SHA-256 compression function and glue-padding directly (a tool like `hash_extender` does the same job):

```python
forged_msg, forged_tag = length_extend(orig_tag, orig_msg, append, secret_len=32)
token = base64.urlsafe_b64encode(forged_msg + b"." + forged_tag).rstrip(b"=")
```

The glue-padding bytes must stay in the forged message — ugly, but they're part of what SHA-256 actually hashed.

## Stage 5 — Final decryption

The vault's token format is `base64url(forged_message || "." || forged_tag)`, and that **unpadded token is itself the IKM** for the last HKDF/AES-GCM:

```python
final_key = HKDF(algorithm=SHA256(), length=32, salt=..., info=b"icarus-enclave/final-v1").derive(token)
flag = AESGCM(final_key).decrypt(final_nonce, final_ciphertext, None)
```

## Running It

```
$ python3 solve.py
[2] recovered RSA private exponent (1019 bits)
[3] vault key = 79a0563a44ec845ffdd370b4187b64e24a5093436f9819f9aae4c2aa316c909f
[4] forged token = YWN0aW9uPXJlcXVlc3Qmc2NvcGU9bGltaXRlZIAAAAAA...hq4F_kzRVuljOe3nf0dv6rwBRWCdZdOqutfiUDwiZLU
[5] FLAG = kBxAc{7HE_one_F@Ult_open5_EV3Ry_L4Yer_OF_7he_iCARUs_Re(0V3ry_(Hain}
```

## Key Takeaways

- Metadata can hold far more than readable text — always check PNG comments / EXIF for odd Unicode (Base65536) or encoded blobs.
- **Encoded binary ≠ its printable hex.** The ZIP password was 16 raw bytes, not the 32-char hex string.
- RSA-CRT without output verification is fragile: a single faulty signature factors the modulus.
- `SHA-256(secret || message)` is forgeable by length extension — use **HMAC-SHA256** for authentication.
- AES-GCM is strong, but useless if its key is derived from attacker-forgeable material.
