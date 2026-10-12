# Patcher 1

**Category:** Rev · **Points:** 999 · **Author:** ayushch

> A stranger gave me these nasty files that dont run on my Windows 7 and asked to patch them for chocolate. `nc 34.29.70.60 1337`
>
> Patch budget — `patchme1`: ≤1 byte @ `0x400390–0x4003d0` · `patchme2`: ≤2 bytes @ `0x400390–0x400397` · `patchme3`: ≤3 bytes @ `0x4003a0–0x400456` & `0x400550–0x400567` · `patchme4`: ≤6 bytes @ `0x400390–0x40041e`. (5 server attempts max.)

**Flag:** `kBxAc{i_thought_patching_is_really_hard_but_it_turns_out_to_be_really_easy}`

> **Files:** original binaries in [`patcher1.zip`](patcher1.zip); the finished byte-patched binaries are in [`patched/`](patched/).

---

## The idea

We get four small Linux programs. The challenge is not to type a password into them; it is to **edit a few bytes of each program** so that every one prints `WIN`. Each file has its own byte limit and a small area where edits are allowed. That makes this more like carefully changing a few words in a recipe than rewriting the recipe from scratch.

The server asks for an address and a replacement byte for each edit. It displays addresses beginning with `0x400000`, while the offsets shown by `objdump` (and the offsets in the files) begin at zero. So, for example:

```text
server address 0x4003c2  =  file offset 0x3c2
```

I unpacked the archive and used `objdump` to see the machine instructions:

```bash
unzip attachments/patcher1.zip -d work
objdump -d -Mintel work/patchme1
```

An assembly instruction is just a sequence of bytes. Changing one byte can turn a conditional jump into an unconditional jump, or make a jump land somewhere else. That is the whole trick here.

## patchme1: make the winning branch automatic

Near file offset `0x3c2`, the program compares two calculated values. The important part is:

```asm
cmp eax, ecx
je  0x3cb       ; only go toward WIN if they are equal
```

The values are not equal, so the original program skips the winning path. The jump's opcode is `74`, meaning **jump if equal**. Replacing it with `eb` makes it an **unconditional jump**. The program now reaches its `WIN`-printing function regardless of the comparison.

```text
0x4003c2: 74 -> eb
```

That is exactly one changed byte, matching this file's limit.

## patchme2: jump past the guard

This program starts by setting a register to zero, then jumps to a tiny function that simply returns. Elsewhere, there is a function that checks whether a pointer leads to the number `0x1337`; if so, it prints `WIN`.

Rather than trying to create a valid pointer and satisfy that check in only two edits, I redirected the existing jump **past the check**, straight to the print code at offset `0x4b0`.

The jump's destination is stored as a *relative displacement*—a distance from the end of the jump instruction. Its original distance is `0x00f9`, landing at `0x490`. The new distance is `0x0119`, landing at `0x4b0`. In little-endian byte order, that means:

```text
0x400393: f9 -> 19
0x400394: 00 -> 01
```

Now the program prints `WIN` without touching the `0x1337` check.

## patchme3: bypass one check, fix the other

This one has a short loop over numbers stored on the stack. At the end, it checks those numbers before calling the `WIN` helper. Following the loop shows that the normal path does **not** satisfy the final check, but the pointer passed to the helper points to a value that has become zero.

I used two bytes to replace the final conditional jump with an unconditional jump directly to the helper call at `0x44f`:

```text
0x4003ff: 75 -> eb
0x400400: 07 -> 4e
```

The helper still checks its pointed-to value against `1`. Since the value is actually `0`, I changed that comparison's immediate byte:

```text
0x400552: 01 -> 00
```

The helper's check now succeeds and prints `WIN`. Total: three changed bytes, exactly the allowance.

## patchme4: take the shortcut

The fourth program has a much longer routine involving character comparisons and writes. Fortunately, the `WIN`-printing function is already present at offset `0x520`. With up to six edits available, we can replace the first five bytes of the program with a direct jump there:

```asm
jmp 0x520
```

The machine-code bytes are `e9 8b 01 00 00`. The `0x018b` part is again a relative distance: `0x520 - (0x390 + 5) = 0x18b`.

```text
0x400390: 48 -> e9
0x400391: 8d -> 8b
0x400392: 15 -> 01
0x400393: 19 -> 00
0x400394: 0f -> 00
```

I also changed `0x400395: 00 -> 90` when submitting, making it a `NOP` (a do-nothing instruction). That sixth edit is optional: execution jumps over it. The five-byte jump alone is enough.

## Checking the result

After editing copies of the four files, I ran each locally. All four printed `WIN`. The server then reported `WIN` for every patch and returned the flag. Two programs returned a nonzero process exit code after printing; that did not matter here because the challenge checked **stdout**, not the exit code.

**Flag:** `kBxAc{i_thought_patching_is_really_hard_but_it_turns_out_to_be_really_easy}`
