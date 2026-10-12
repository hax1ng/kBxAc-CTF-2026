#!/usr/bin/env python3
"""Solve kBxAc CTF 2026 / Crypto / Dead Validator."""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


ROOT = Path(__file__).resolve().parent
N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141


def main() -> None:
    chain = json.loads((ROOT / "extracted/chain.json").read_text())

    # A repeated ECDSA r means that the same ephemeral point (and here the
    # same nonce k) was used twice.
    by_r = defaultdict(list)
    for block in chain:
        for tx in block["transactions"]:
            by_r[int(tx["signature"]["r"], 16)].append(tx)

    duplicates = [(r, txs) for r, txs in by_r.items() if len(txs) > 1]
    assert len(duplicates) == 1
    r, (tx1, tx2) = duplicates[0]

    # The signer hashes the ASCII hexadecimal tx_hash a second time.
    def representative(tx: dict) -> int:
        digest = hashlib.sha256(tx["tx_hash"].encode("ascii")).digest()
        return int.from_bytes(digest, "big")

    z1, z2 = representative(tx1), representative(tx2)
    s1 = int(tx1["signature"]["s"], 16)
    s2 = int(tx2["signature"]["s"], 16)

    k = (z1 - z2) * pow((s1 - s2) % N, -1, N) % N
    d = (s1 * k - z1) * pow(r, -1, N) % N
    private_bytes = d.to_bytes(32, "big")

    # Confirm independently that the scalar produces the supplied public key.
    recovered_public = ec.derive_private_key(d, ec.SECP256K1()).public_key()
    supplied_public = serialization.load_pem_public_key(
        (ROOT / "extracted/wallet.pub").read_bytes()
    )
    assert recovered_public.public_numbers() == supplied_public.public_numbers()

    envelope = json.loads((ROOT / "extracted/validator_backup.enc").read_text())
    salt = bytes.fromhex(envelope["salt"])
    nonce = bytes.fromhex(envelope["nonce"])
    encrypted = bytes.fromhex(envelope["ciphertext"])

    # Version 2's SHA-256 KDF is domain-separated. Ordering matters:
    #     decoded salt || 32-byte scalar || b"dead-validator"
    key = hashlib.sha256(salt + private_bytes + b"dead-validator").digest()
    plaintext = AESGCM(key).decrypt(nonce, encrypted, None)
    recovered = json.loads(plaintext)
    flag = recovered["final_payload"]

    assert flag.startswith("kBxAc{") and flag.endswith("}")
    print(f"repeated r: {r:064x}")
    print(f"transactions: {tx1['txid']} and {tx2['txid']}")
    print(f"nonce k: {k:064x}")
    print(f"private d: {d:064x}")
    print(f"AES key: {key.hex()}")
    print(plaintext.decode())
    print(f"FLAG: {flag}")


if __name__ == "__main__":
    main()
