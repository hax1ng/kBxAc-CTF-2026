#!/usr/bin/env python3
"""
Icarus Enclave - kBxAc CTF 2026 (Crypto)

A four-stage recovery chain. Stage 1 is done out-of-band (see the README): a
Base65536 string hidden in the PNG's Unicode comment decodes to the 16 raw
bytes that are the password for icarus-enclave.zip, which yields challenge.json
and recovery_vault.json. This script automates stages 2-4:

  2. RSA-CRT fault: gcd(n, correct_sig - faulty_sig) factors n, giving d.
  3. HKDF(d as 128-byte big-endian) -> AES-256-GCM key that opens the vault.
  4. The vault authenticates with SHA-256(secret||message); a length-extension
     attack forges a token that is itself the IKM for the final HKDF/AES-GCM.

ZIP password (stage 1 output): 5388d1cd395fbffd59bf77c3eabbf36d (raw bytes).
"""
import base64
import json
import math
import struct

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def hkdf(ikm, salt, info, length=32):
    return HKDF(algorithm=hashes.SHA256(), length=length, salt=salt, info=info).derive(ikm)


# ---- Stage 2: factor n from the faulty CRT signature -----------------------
chal = json.load(open("extracted/challenge.json"))
n = int(chal["n"])
e = int(chal["e"])
good = int(chal["correct_signature"])
bad = int(chal["faulty_signature"])

p = math.gcd(n, good - bad)
q = n // p
assert p * q == n and p not in (1, n)
d = pow(e, -1, (p - 1) * (q - 1))
print(f"[2] recovered RSA private exponent ({d.bit_length()} bits)")

# ---- Stage 3: open the recovery vault --------------------------------------
vault = json.load(open("extracted/recovery_vault.json"))
kd, enc = vault["key_derivation"], vault["encryption"]
vault_key = hkdf(
    d.to_bytes(128, "big"),
    bytes.fromhex(kd["salt_hex"]),
    kd["info"].encode(),
)
vault_plain = AESGCM(vault_key).decrypt(
    bytes.fromhex(enc["nonce_hex"]), bytes.fromhex(enc["ciphertext_hex"]), None
)
v = json.loads(vault_plain)
print(f"[3] vault key = {vault_key.hex()}")

# ---- Stage 4: SHA-256 length extension -------------------------------------
MASK = 0xFFFFFFFF
K = [
    0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5, 0x3956C25B, 0x59F111F1,
    0x923F82A4, 0xAB1C5ED5, 0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3,
    0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174, 0xE49B69C1, 0xEFBE4786,
    0x0FC19DC6, 0x240CA1CC, 0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
    0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7, 0xC6E00BF3, 0xD5A79147,
    0x06CA6351, 0x14292967, 0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13,
    0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85, 0xA2BFE8A1, 0xA81A664B,
    0xC24B8B70, 0xC76C51A3, 0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
    0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5, 0x391C0CB3, 0x4ED8AA4A,
    0x5B9CCA4F, 0x682E6FF3, 0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208,
    0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
]


def _rotr(x, n):
    return ((x >> n) | (x << (32 - n))) & MASK


def _compress(h, block):
    w = list(struct.unpack(">16I", block)) + [0] * 48
    for i in range(16, 64):
        s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
        s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) & MASK
    a, b, c, dd, ee, f, g, hh = h
    for i in range(64):
        S1 = _rotr(ee, 6) ^ _rotr(ee, 11) ^ _rotr(ee, 25)
        ch = (ee & f) ^ (~ee & g)
        t1 = (hh + S1 + ch + K[i] + w[i]) & MASK
        S0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
        maj = (a & b) ^ (a & c) ^ (b & c)
        t2 = (S0 + maj) & MASK
        hh, g, f, ee, dd, c, b, a = g, f, ee, (dd + t1) & MASK, c, b, a, (t1 + t2) & MASK
    return [(x + y) & MASK for x, y in zip(h, [a, b, c, dd, ee, f, g, hh])]


def _md_pad(msg_len):
    return b"\x80" + b"\x00" * ((55 - msg_len) % 64) + struct.pack(">Q", msg_len * 8)


def length_extend(orig_tag, orig_msg, append, secret_len):
    """Forge SHA-256(secret || orig_msg || glue_padding || append)."""
    glue = _md_pad(secret_len + len(orig_msg))
    processed = secret_len + len(orig_msg) + len(glue)
    tail = append + _md_pad(processed + len(append))
    h = list(struct.unpack(">8I", orig_tag))
    for i in range(0, len(tail), 64):
        h = _compress(h, tail[i:i + 64])
    return orig_msg + glue + append, struct.pack(">8I", *h)


auth = v["authentication"]
orig_msg = base64.b64decode(auth["message_b64"])
append = base64.b64decode(auth["extension_b64"])
forged_msg, forged_tag = length_extend(
    bytes.fromhex(auth["tag_hex"]), orig_msg, append, auth["secret_length"]
)
token = base64.urlsafe_b64encode(forged_msg + b"." + forged_tag).rstrip(b"=")
print(f"[4] forged token = {token.decode()}")

# ---- Stage 5: final decryption (token is the IKM) --------------------------
rel = v["release"]
rk = rel["kdf"]
final_key = hkdf(token, bytes.fromhex(rk["salt_hex"]), rk["info"].encode())
flag = AESGCM(final_key).decrypt(
    bytes.fromhex(rel["final_nonce_hex"]),
    bytes.fromhex(rel["final_ciphertext_hex"]),
    None,
)
print("[5] FLAG =", flag.decode())
