# lets get to library

**Category:** Pwn · **Points:** 1000 · **Author:** k3rn3lbr3ach3r

> 🤓 &nbsp; `nc 104.154.133.139 1337`

**Flag:** `kBxAc{_H3y_l3ts_g0_t0_l1br4ry_t0g3th3r_t0_g3t_h3r_t0_g3t_b3tt3r_wh4t_3v3r_wh3n3v3r_1_d0nt_kn0w_wh4t_1_4m_typ1ng_}`

> **Files:** `letsgettolibrary` (committed). The exploit targets **glibc 2.39 / ld-2.39** — the libc is not committed here; drop in the matching copy to reproduce the remote offsets.

---

## The short version

The program asks for our name, but reads it with `gets()`: a function that keeps reading even after its destination buffer is full. That lets us overwrite not just the name, but the information the program uses to decide where to go next.

The catch is that this tiny binary has almost no useful ROP gadgets. In particular, it has no easy `pop rdi; ret` to choose an argument for a function call. Instead, I reused a few instructions already in `main()` to make it read into chosen places. I temporarily changed the `gets` entry in the GOT (a table of imported-function addresses) to point to `printf`. That gave me a format-string leak of libc, after which a normal libc ROP chain could run `system("cat flag.txt")`.

## What the program does

The important part of `main()` is essentially:

```c
char name[128];
printf("Enter your name to check out a book: ");
gets(name);
greet_reader();
```

`gets(name)` does not know that `name` is only 128 bytes long. Sending more than 128 bytes overwrites the saved frame pointer (`rbp`) and then the return address. The layout is:

```text
128 bytes of name | 8-byte saved rbp | 8-byte return address
```

There is no stack canary to catch this. The binary is also non-PIE, so its own addresses stay fixed, and its GOT is writable because it has only partial RELRO. NX is on, so putting shellcode in the input is not the convenient route.

## The useful trick in `main()`

At `0x4011a5`, `main()` computes `rbp - 0x80`, puts that address in `rdi`, and calls `gets@plt`:

```asm
0x4011a5  lea rax, [rbp-0x80]
0x4011a9  mov rdi, rax
0x4011b1  call gets@plt
```

If I control `rbp` and return to `0x4011a5`, I control **where the next input is written**. Returning through `leave; ret` lets me load another saved `rbp` and return address from a fake stack frame I placed earlier. In plain English: one oversized name lets me arrange a series of new “name” reads, each aimed at a different address.

I used writable memory around `0x404900` as a staging area. A lower area around `0x404050` held the format string and another fake frame. The first overflow sets the saved `rbp` to `0x404980` and the return address to `0x4011a5`; subsequent reads fill in the rest of the chain.

Why all the bouncing between fake frames? A libc function uses quite a bit of stack space. If I simply pivoted the stack next to the GOT and called `gets` or `printf`, their own stack usage would run into unmapped/read-only memory and crash. The fake frames keep the *call stack* high in writable memory, even when `rbp - 0x80` points somewhere low, such as the GOT.

## Turning `gets` into a leak

The GOT entry for `gets` is at `0x404010`. One controlled read changes it to `0x401040`, the binary's `printf@plt`. The next time `main()` thinks it is calling `gets`, it actually calls `printf`, with the controlled buffer as the format string.

I used that format string to read the already-resolved `setbuf` address from its GOT entry at `0x404000`. Printing a pointer as one string is unreliable: a pointer can contain a zero byte, which ends a C string early. Instead, the payload reads from `0x404000`, `0x404001`, and so on through `0x404005`, with each read padded to six characters. That lets the script reconstruct all six useful address bytes even when one of them is zero.

The format string also performs two tiny writes with `%hhn`:

```text
%c%c%c%c%c + six %6s reads + %45c  →  86 printed bytes (0x56)
%hhn                                    →  change gets@GOT's low byte to 0x56
%249c                                   →  335 total bytes (low byte 0x4f)
%hhn                                    →  adjust a fake frame pointer
```

Changing `gets@GOT` to `0x401056` points it at `gets@plt+6`, which invokes the PLT resolver and restores the real `gets`. The second byte-write moves the next fake frame up to `0x404f00`, giving that resolver enough room to use the stack without crashing.

The supplied libc says `setbuf` is at offset `0x8f740`, so:

```text
libc base = leaked setbuf address - 0x8f740
```

## Getting the flag

With libc's base known, the last input is a small ROP chain:

```text
ret                 # stack alignment
pop rdi; ret
address of "cat flag.txt"
system
pop rdi; ret
0
exit
```

The `pop rdi; ret` gadget is at libc offset `0x10f75b`; `system` is at `0x58740`, and `exit` at `0x47b90`. The command string lives at `0x404f80`, *above* the ROP stack. I first put it below the stack, but `system()` overwrote it while working—that was a fun little debugging detour.

I tested locally against the supplied libc and the provided `kBxAc{TEST_FLAG}` file. The local exploit printed the test flag and exited cleanly. Then I ran the same attack against the service; the remote version is saved as [`work/remote.py`](work/remote.py), while [`work/exploit.py`](work/exploit.py) is the local version.

```bash
python3 work/remote.py
```

## Flag

```text
kBxAc{_H3y_l3ts_g0_t0_l1br4ry_t0g3th3r_t0_g3t_h3r_t0_g3t_b3tt3r_wh4t_3v3r_wh3n3v3r_1_d0nt_kn0w_wh4t_1_4m_typ1ng_}
```
