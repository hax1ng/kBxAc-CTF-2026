#!/usr/bin/env python3

# The checker compares the input against this encrypted 37-byte list.  In the
# ELF it is stored as a backwards-linked chain of GHC list/Char closures.
ciphertext = bytes.fromhex(
    "918c86acbdd6a59187deaaf2cea0ce99b69e88919881eacaa5b8cd9fa7f2c9afcb9481f287"
)

# The checker cycles this six-byte key and XORs it with the encrypted list.
key = bytes.fromhex("facefeeddead")

flag = bytes(value ^ key[index % len(key)] for index, value in enumerate(ciphertext))
print(flag.decode())
