#!/usr/bin/env sage
# Ghost in the Group - kBxAc CTF 2026 (Crypto)
#
# Finite-field Diffie-Hellman with a badly chosen prime: p is 246 bits, but
# p-1 is almost entirely smooth (largest factor only 48 bits). That makes the
# discrete log cheap via Pohlig-Hellman, so we recover the client's private
# exponent a, rebuild the shared secret, and decrypt the AES-256-GCM payload.
#
# Run with:  sage solve.sage   (needs pycryptodome for the KDF + AES)
from sage.all import Integer, Mod, discrete_log, power_mod
from Crypto.Protocol.KDF import HKDF
from Crypto.Hash import SHA256
from Crypto.Cipher import AES

p = Integer(88000753428701489113490993450865560865075124813304102617544373043200000001)
g = Integer(18935151604271057755988199578124546584801734055481457746415726705868881325)
A = Integer(856648410561794340416538813121044592228714914232497557125907449024211481)
B = Integer(31388649449514431261745477998552915328450496654874229059581132104017862585)

print("factor(p-1) =", (p - 1).factor())           # confirms the smoothness
print("ord(g)      =", Mod(g, p).multiplicative_order())

# Pohlig-Hellman discrete log recovers the client's private exponent.
a = discrete_log(Mod(A, p), Mod(g, p))
assert power_mod(g, a, p) == A
print("a =", a)

# Either party's private exponent reproduces the shared secret.
shared_secret = power_mod(B, a, p)
encoded_secret = int(shared_secret).to_bytes((int(p).bit_length() + 7) // 8, "big")  # 31 bytes

# Supplied HKDF-SHA256 parameters -> AES-256 key.
salt = bytes.fromhex("4a927d5cbda2656dd113c68d0bf48f82")
info = b"ghost-in-the-group/aes-gcm"
key = HKDF(encoded_secret, 32, salt, SHA256, context=info)

# The last 16 bytes of the payload are the GCM tag.
nonce = bytes.fromhex("3aa4af98c6b9091299366131")
encrypted = bytes.fromhex(
    "c8ebf04f1a069781ea4245b921d8776a2259257d10cfc79bca9ada79fd5bb3b"
    "e57bae20f33f92c22731f8df4819c31af0d5edf1d76a9a3a6abbe5db90f718"
    "56742e713e8e3b1e99da9efd600b3a4c155ca"
)
ciphertext, tag = encrypted[:-16], encrypted[-16:]

cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
plaintext = cipher.decrypt_and_verify(ciphertext, tag)

print("shared secret =", shared_secret)
print("AES key       =", key.hex())
print("FLAG          =", plaintext.decode())
