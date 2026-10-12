# Patcher 2

**Category:** Rev · **Points:** 1000 · **Author:** ayushch

> I think i'm expert now. `nc 136.65.158.41 1337`
>
> Patch budget — `patchme1`: ≤2 bytes · `patchme2`: ≤4 bytes · `patchme3`: ≤3 bytes · `patchme4`: ≤3 bytes. (5 server attempts max.)

**Flag:** `kBxAc{pppppppatching_paaaaaaatching_patttttttching_are_you_still_patching}`

> **Files:** original binaries in [`patcher2.zip`](patcher2.zip). The exact byte patches are documented below, so the large binaries themselves are not needed to follow the solve.

**Goal:** patch four executables so that each prints `WIN`, without changing more than the allowed number of bytes.

---

## The idea, in plain English

The challenge gave us four broken programs. We were **not** allowed to rewrite them or add new code. Instead, we could change a tiny number of bytes in each program—2, 4, 3, and 3 bytes respectively. Think of it like fixing four machines by flipping a few switches rather than replacing their parts.

The service checked the patched programs and gave the flag only if **all four** printed `WIN`. I worked on local copies first, so the limited remote attempts were only used after everything worked.

## Getting started

The archive in `attachments/patcher2.zip` contains `patchme1` through `patchme4`. I extracted them and used `file` to see what they were:

| Program | What it is | Byte limit |
| --- | --- | ---: |
| `patchme1` | Small C++ ELF | 2 |
| `patchme2` | Go ELF | 4 |
| `patchme3` | Rust ELF | 3 |
| `patchme4` | Rust ELF | 3 |

Running the originals did not produce `WIN`: the first printed just `W`, and the other three printed nothing. I used `objdump -d -Mintel` to read their assembly. You do **not** need to understand every instruction here. The important ones are:

- `jmp`: go somewhere else and **do not** come back here.
- `call`: go somewhere else, then **return** to the next instruction.
- `jne`: jump if the last comparison was **not equal**.
- `je`: jump if it **was equal**.

One byte can change one of these instructions, which is exactly what we need.

## `patchme1`: let the printing functions fall through

This program already had code to print `W`, `I`, and `N`, but its main function only called the `W` helper. The helpers were laid out consecutively. The first two ended by *jumping* to C++'s output routine. Since a jump does not return, execution never continued into the next helper.

I changed each of those two jumps (`E9`) into a call (`E8`). Now the output routine returns, execution falls through the padding to the next helper, and the program prints `W`, then `I`, then `N`.

| File offset | Service address | Original → new | Effect |
| --- | --- | --- | --- |
| `0x4f3` | `0x4004f3` | `e9 → e8` | Return after printing `W` |
| `0x513` | `0x400513` | `e9 → e8` | Return after printing `I` |

That is exactly **2 changed bytes**.

## `patchme2`: dodge the failed checks

Go binaries contain a lot of runtime code, so the disassembly looked intimidating at first. Its Go function-name table pointed me to `main.main` near address `0x4b63a0`. The interesting part was much smaller than the whole binary: it changed some numbers, checked whether the numbers and pointers matched expected values, and printed the `W`, `I`, and `N` characters only after passing those checks.

The original values did not satisfy the checks. Instead of trying to repair every number and pointer—which would take too many bytes—I changed the branches that decide whether to print:

| File offset | Service address | Original → new | What it does |
| --- | --- | --- | --- |
| `0xb6459` | `0x4b6459` | `75 → 74` | Invert the first conditional jump, reaching the `W` print path |
| `0xb64ea` | `0x4b64ea` | `74 → eb` | Make the second jump unconditional, reaching the `I` print path |
| `0xb655d` | `0x4b655d` | `76 → 13` | Shorten a jump so it lands at the `N` print path instead of skipping it |

The last edit is a little different: `76` and `13` are not instruction names. They are the **distance** of a short jump. Changing the distance makes the existing jump land where we want. This uses **3 of the 4 allowed bytes**.

## `patchme3` and `patchme4`: flip three decisions each

Both Rust programs had the same overall shape: compute a value, compare it against a target, and skip a print if it does not match. They used different calculations—`patchme3` had bit-mixing operations, while `patchme4` had a small table-driven calculation—but the final decisions were easy to spot.

In each program there were three `jne` instructions (`75`), one after each comparison. On the original run, those comparisons failed, so `jne` skipped printing. Replacing `jne` with `je` (`74`) reversed that decision: a failed comparison now continues into the print code. Repeating this for all three checks produced `WIN`.

| Program | File offsets | Service addresses | Change at each offset |
| --- | --- | --- | --- |
| `patchme3` | `0x5975`, `0x59a0`, `0x59cb` | `0x405975`, `0x4059a0`, `0x4059cb` | `75 → 74` |
| `patchme4` | `0x59aa`, `0x59cc`, `0x59f5` | `0x4059aa`, `0x4059cc`, `0x4059f5` | `75 → 74` |

Each uses **exactly 3 changed bytes**.

## Testing and submission

I applied the edits to copies under `solved/`, ran all four copies, and checked that they printed `WIN`. I also compared each patched file with its original to confirm the number of changed bytes stayed within the limit.

The service accepts one-byte patches as an address and a new hex byte. For these files, the service addresses shown above are the file offsets plus `0x400000`; it also accepts raw file offsets. After entering the patches above, it reported:

```text
[+] patchme1: WIN
[+] patchme2: WIN
[+] patchme3: WIN
[+] patchme4: WIN

All patches WIN!
```

**Flag:** `kBxAc{pppppppatching_paaaaaaatching_patttttttching_are_you_still_patching}`

The main lesson: with a strict byte limit, it is often cheaper to change **control flow** (where the program goes next) than to fix all the data that made it take the wrong path.
