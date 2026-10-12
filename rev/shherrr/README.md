# Shherrr

**Category:** Rev · **Points:** 1000

> Cheeta hi kehde!!

**Flag:** `kBxAc{sh3ll_c4lc_1s_br0k3n}`

> **Note:** the challenge binary (`chall`) is a ~19 MB stripped Raku ELF and is not committed here. The XOR constants recovered from it are reproduced below, and [`solve.py`](solve.py) decodes the flag from them.

---

## Short version

The program pretends to be a calculator, but all of its arithmetic operations are deliberately wrong. Hidden inside the binary is an array of encrypted character values and a five-number XOR key. Repeating that key over the array reveals the flag:

```text
kBxAc{sh3ll_c4lc_1s_br0k3n}
```

## First look at the binary

I started by asking Linux what kind of file we had:

```bash
file attachments/chall
```

The result showed that it was a stripped 64-bit Linux ELF executable:

```text
ELF 64-bit LSB executable, x86-64, dynamically linked, stripped
```

“Stripped” means that helpful names such as `main`, `decrypt_flag`, and variable names have been removed. That makes the disassembly less friendly, but the program's actual instructions and constant data still have to be present.

After making it executable, I ran it:

```bash
chmod +x attachments/chall
./attachments/chall
```

It displayed a simple prompt:

```text
> 
```

## The suspicious calculator

The program expects input resembling a basic calculation. Testing a few expressions showed that it was not doing normal arithmetic:

```text
1 + 2  -> 44
10 + 20 -> 242
```

More testing revealed the program's intentionally broken rules:

| Input operation | What the program actually calculates |
|---|---|
| `a + b` | `a * b + 42` |
| `a - b` | `3 * (a + b)` |
| `a * b` | `17 * (a - b)` |
| `a / b` | `a * b - 99` |

Invalid input usually caused it to print:

```text
shherrr
```

This calculator is mostly a distraction. The challenge title and the final flag both joke about the “shell calculator” being broken.

## Finding out what it was written in

Running `strings` exposed a useful source-file path:

```bash
strings -a attachments/chall | grep -Ei 'raku|chall\.raku|prompt|shherrr'
```

Among the results were strings like:

```text
/home/ayush/Desktop/kBxAc/rev/shherrr/chall.raku
prompt
shherrr
+^
chr
```

The `.raku` extension tells us that the original source was written in **Raku**. This also explains why the executable is unusually large for such a small program: it contains a lot of language-runtime machinery.

Two other strings were especially useful:

- `+^` is Raku's bitwise XOR operator.
- `chr` converts a number into the character represented by that number.

Together, those are a strong hint that the program decrypts text by XORing numbers and turning the results into characters.

## Locating the hidden flag routine

I inspected the program in a disassembler and followed the code responsible for the prompt and input handling. Most of it led to the fake calculator operations. A separate hidden branch built two arrays:

### Encrypted values

```text
78 75 b8 9f 21 68 44 a8 ed 2e
7f 68 a3 ea 2e 70 68 f1 ad 1d
71 45 f0 b5 71 7d 4a
```

These are hexadecimal numbers. Written as a Python list, they are:

```python
encrypted = [
    0x78, 0x75, 0xb8, 0x9f, 0x21,
    0x68, 0x44, 0xa8, 0xed, 0x2e,
    0x7f, 0x68, 0xa3, 0xea, 0x2e,
    0x70, 0x68, 0xf1, 0xad, 0x1d,
    0x71, 0x45, 0xf0, 0xb5, 0x71,
    0x7d, 0x4a,
]
```

### XOR key

```python
key = [19, 55, 192, 222, 66]
```

The decryption helper takes one encrypted number at a time, XORs it with a number from the key, calls `chr` on the result, and appends the character to the output. Because the encrypted array is longer than the key, the key repeats from the beginning.

In simpler terms, the operation is:

```text
plain[i] = encrypted[i] XOR key[i modulo 5]
```

The “modulo 5” part simply means that after using all five key values, we go back to the first one.

## Extracting the flag

There was no need to reconstruct the exact secret input that reaches the hidden branch. Once both arrays and the decryption logic were visible, the same calculation could be reproduced directly in Python:

```python
encrypted = [
    0x78, 0x75, 0xb8, 0x9f, 0x21,
    0x68, 0x44, 0xa8, 0xed, 0x2e,
    0x7f, 0x68, 0xa3, 0xea, 0x2e,
    0x70, 0x68, 0xf1, 0xad, 0x1d,
    0x71, 0x45, 0xf0, 0xb5, 0x71,
    0x7d, 0x4a,
]

key = [19, 55, 192, 222, 66]

flag = "".join(
    chr(value ^ key[index % len(key)])
    for index, value in enumerate(encrypted)
)

print(flag)
```

Running it gives:

```text
kBxAc{sh3ll_c4lc_1s_br0k3n}
```

As a quick example, the first encrypted value is `0x78`, or 120 in decimal. The first key value is 19:

```text
120 XOR 19 = 107
chr(107) = "k"
```

Repeating that process for every value produces the entire flag.

## Flag

```text
kBxAc{sh3ll_c4lc_1s_br0k3n}
```

## Takeaway

The main trick was not to get lost inside the large Raku runtime or spend too much time understanding the fake calculator. Searching for useful strings exposed the language and the XOR-related operations, and following those references led directly to the encrypted data and its key. Once those constants were recovered, decoding the flag was only a few lines of Python.
