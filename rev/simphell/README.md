# simphell

**Category:** Rev · **Points:** 1000

> Yet another simple challenge

**Flag:** `kBxAc{__y3t_4n0th3r_fl4g_v3ry_3a5y__}`

> **Files:** `chall` (the ~1 MB stripped Haskell/GHC ELF) and [`solve.py`](solve.py).

---

## TL;DR

The program is a stripped 64-bit Haskell executable. It stores an encrypted
37-byte flag in its data section and checks our input against the decrypted
result. The encryption is just XOR with the repeating six-byte key:

```text
fa ce fe ed de ad
```

Decrypting the embedded byte array gives:

```text
kBxAc{__y3t_4n0th3r_fl4g_v3ry_3a5y__}
```

## Initial inspection

I started with the usual basic checks:

```bash
file attachments/chall
strings -a attachments/chall | grep -iE 'flag|success|failure|secret'
```

`file` reported:

```text
ELF 64-bit LSB executable, x86-64, dynamically linked, stripped
```

The useful strings were:

```text
Enter the secret flag:
Success! Valid flag.
Failure! Invalid flag.
```

There were also lots of strings mentioning GHC, the Glasgow Haskell Compiler.
That told me this was a compiled Haskell program rather than a normal small C
binary.

Running it confirmed the expected behavior:

```bash
printf 'test\n' | ./attachments/chall
```

```text
Enter the secret flag: Failure! Invalid flag.
```

## Why the binary looks strange

Compiled Haskell programs include a fairly large runtime system. Even a tiny
program therefore contains a lot of code unrelated to the actual challenge.
The binary was also stripped, so there were no friendly function names.

Haskell values are represented as heap objects called **closures**. A list is
not stored as one ordinary C array. Instead, it is a chain of objects where
each object contains:

1. runtime information,
2. one list element,
3. a pointer to the rest of the list.

Pointers can also contain small tag bits. This is an optimization used by the
GHC runtime, but it means that blindly treating every pointer as the exact
start of an object can produce values that are off by one.

## Finding the interesting data

The challenge-specific strings were near virtual address `0x4bb048`, and
pointers to them led into a small application-specific area in `.data`. Near
that area was a long chain of Haskell list closures between approximately:

```text
0x4e1750 ... 0x4e1bd0
```

Each list element pointed to one of GHC's statically allocated character
objects. After removing the pointer tag and reading the character payload, the
list produced this 37-byte sequence:

```text
91 8c 86 ac bd d6 a5 91 87 de aa f2 ce a0 ce 99
b6 9e 88 91 98 81 ea ca a5 b8 cd 9f a7 f2 c9 af
cb 94 81 f2 87
```

This looked like ciphertext: it had exactly the length expected for a CTF
flag, but it was not readable ASCII.

There was also a much shorter static list whose values, in logical list order,
were:

```text
ce fe ed de ad
```

Dynamic analysis showed that the checker supplies `fa` as the first value and
then processes that short list. Together, these form the repeating key:

```text
fa ce fe ed de ad
```

The bytes are also a pretty obvious hint once written in hexadecimal:
`FA CE FE ED DE AD` resembles the hexspeak phrase “face feed dead.”

## Confirming the check in GDB

I set breakpoints in the small application-specific code region rather than
trying to understand the entire Haskell runtime.

One useful breakpoint was at `0x406238`. At that point, the program compared
the input length with the constant value `0x25`:

```text
0x25 = 37 decimal
```

So the correct input had to be exactly 37 characters long.

Another useful function began at `0x405f58`. It walked two Haskell lists and
created a new list lazily. The values passed through it showed the encrypted
list and the key stream being combined. The first pair was:

```text
ciphertext: 91
key:        fa
```

XORing them gives:

```text
0x91 XOR 0xfa = 0x6b = 'k'
```

The next bytes worked the same way:

```text
0x8c XOR 0xce = 0x42 = 'B'
0x86 XOR 0xfe = 0x78 = 'x'
0xac XOR 0xed = 0x41 = 'A'
0xbd XOR 0xde = 0x63 = 'c'
0xd6 XOR 0xad = 0x7b = '{'
```

That immediately produced the expected flag prefix `kBxAc{` and confirmed
both the operation and the key order.

## Decryption

XOR is reversible: applying the same key a second time recovers the original
text. The only extra detail is that the six-byte key repeats until all 37
ciphertext bytes have been processed.

The solver is:

```python
#!/usr/bin/env python3

ciphertext = bytes.fromhex(
    "918c86acbdd6a59187deaaf2cea0ce99"
    "b69e88919881eacaa5b8cd9fa7f2c9"
    "afcb9481f287"
)

key = bytes.fromhex("facefeeddead")

flag = bytes(
    value ^ key[index % len(key)]
    for index, value in enumerate(ciphertext)
)

print(flag.decode())
```

Running it gives:

```bash
python3 solve.py
```

```text
kBxAc{__y3t_4n0th3r_fl4g_v3ry_3a5y__}
```

## Verification

Finally, I passed the recovered flag back to the original executable:

```bash
python3 solve.py | ./attachments/chall
```

```text
Enter the secret flag: Success! Valid flag.
```

## Flag

```text
kBxAc{__y3t_4n0th3r_fl4g_v3ry_3a5y__}
```

## Takeaways

- A large binary does not necessarily mean the challenge logic is large. Most
  of this executable was the Haskell runtime.
- Searching for user-facing strings is still a good starting point in a
  stripped binary.
- GHC stores lists and characters as runtime objects, so tagged pointers and
  object layout matter when extracting data manually.
- A few carefully selected GDB breakpoints can be more useful than trying to
  decompile every runtime function.
- Recognizable constants such as `FA CE FE ED DE AD` can provide a strong hint
  about the intended transformation.
