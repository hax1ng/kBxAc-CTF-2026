# Insanity Check

**Category:** Misc · **Points:** 1000

> The whole challenge is a single very long encoded string (see
> [`challenge.txt`](challenge.txt)). No binary, no remote service.

**Flag** (note the quotes, backslashes and backticks — they are part of it):

```text
kBxAc{0k"i_?99W..Rc-]1/0&GF?<>U4@M:s:c2Bj;H5>,=Z0>F>ZslJ4^_hF0/Xn\=CF'NC.qAb?>qW#3bCB';_C'j6od1dEH5;@>;J!P6S'T@=%$Uo<A-$^6<meZFXAkd05NjL/jF;#AP=g33GCiB8LZAV/3@QJFYYX"5s[t(2`l"24^;\F2KM>391E#`=&h"'=BRg><%KD94=W`p7R1r?-"&ec5uC--?n5/l}
```

---

## TL;DR

Base64-decode the blob **six** times. The result literally says
`here is the flag : <body>`. Stop there and wrap `<body>` in `kBxAc{...}`. The
`<body>` text happens to be valid ASCII85, and continuing to decode it reaches a
"wrong flag" decoy — that extra layer is deliberate misdirection.

## What We're Given

One long string ending in `==`, using only `A–Z a–z 0–9 + /` and padding —
textbook Base64. The event flag format is `kBxAc{...}`, and the decoded value
does **not** include the prefix/braces, so we add them ourselves.

## Initial Recon

Decode once → still Base64-looking → decode again → repeat. The sizes shrink
each round:

```text
1400 -> 1048 -> 784 -> 588 -> 440 -> 328 -> 244 bytes
```

After the sixth decode it finally becomes readable text:

```text
here is the flag : 0k"i_?99W..Rc-]1/0&GF?<>...
```

## The Trick

This is a *stopping-condition* puzzle, not a software bug. Layered-encoding
challenges train us to keep decoding while the output still resembles a known
encoding — and this one weaponises that reflex.

The text after `here is the flag : ` is valid ASCII85. If you ignore the
explicit marker and press on, four ASCII85 decodes yield a Base64 string, which
decodes to:

```text
HeHe_Haa_Hoo_HOO_you_got_the_wrong_flag_maybe_you_misread_something
```

That's the author's decoy — it even tells you that you misread the layer-six
instruction. The real flag body is the **unchanged** text right after the marker.

> Recognisable encoding is evidence that data *can* be decoded, not proof that
> it *should* be. A plain-language delimiter should win over "it still looks
> like base-something."

## Building the Exploit

See [`solve.py`](solve.py). It reads the blob from `challenge.txt` and
strict-decodes Base64 until the marker appears:

```python
PREFIX = b"here is the flag : "
rounds = 0
while not data.startswith(PREFIX):
    data = b64decode(data, validate=True)   # strict: reject malformed input
    rounds += 1
body = data.removeprefix(PREFIX).decode("ascii")
flag = f"kBxAc{{{body}}}"
```

`validate=True` matters — it stops Python from silently discarding unexpected
characters and masking a wrong turn. Preserving `body` byte-for-byte matters
just as much: nothing in it should be escaped or "cleaned up."

## Running It

```console
$ python3 solve.py
Base64 rounds: 6
kBxAc{0k"i_?99W..Rc-]1/0&GF?<>U4@M:s:c2Bj;H5>,=Z0>F>ZslJ4^_hF0/Xn\=CF'NC.qAb?>qW#3bCB';_C'j6od1dEH5;@>;J!P6S'T@=%$Uo<A-$^6<meZFXAkd05NjL/jF;#AP=g33GCiB8LZAV/3@QJFYYX"5s[t(2`l"24^;\F2KM>391E#`=&h"'=BRg><%KD94=W`p7R1r?-"&ec5uC--?n5/l}
```

## Key Takeaways

- Automating repeated Base64 is easy; the loop still needs a *meaningful* stop.
- Stop when the plaintext says it's the flag — don't decode something just
  because it resembles another encoding.
- A decoded message that announces it's the "wrong flag" is a cue to revisit an
  earlier decision, not to try another variation of the decoy.
- Preserve unusual flag characters exactly.
