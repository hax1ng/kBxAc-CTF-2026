# kBxAc CTF 2026 — Writeups

Solutions, exploits, and writeups for the challenges solved at **kBxAc CTF 2026**,
a Jeopardy-style Capture The Flag event hosted on CTFd.

| | |
|---|---|
| **Event** | kBxAc CTF 2026 |
| **Dates** | Fri, 09 Oct 2026 14:30 EDT — Sat, 10 Oct 2026 14:30 EDT |
| **Format** | Jeopardy (CTFd) |
| **Flag format** | `kBxAc{...}` |
| **Solved by** | [hax1ng](https://github.com/hax1ng) |
| **Challenges solved** | 26 |

Every solved challenge has its own directory with a standalone writeup
(`README.md`), the final solve script(s)/exploit, and the essential challenge
files needed to follow along.

---

## Challenges

### Crypto
| Challenge | Points | Writeup |
|---|---:|---|
| Crossword 1 | 1000 | [writeup](crypto/crossword-1/) |
| Crossword 2 | 1000 | [writeup](crypto/crossword-2/) |
| Dead Validator | 1000 | [writeup](crypto/dead-validator/) |
| Ghost in the Group | 1000 | [writeup](crypto/ghost-in-the-group/) |
| Icarus Enclave | 1000 | [writeup](crypto/icarus-enclave/) |
| Ten Symbols | 1000 | [writeup](crypto/ten-symbols/) |
| Weiner | 1000 | [writeup](crypto/weiner/) |

### Forensics
| Challenge | Points | Writeup |
|---|---:|---|
| C-Laude | 1000 | [writeup](forensics/c-laude/) |
| Ghost Frame | 1000 | [writeup](forensics/ghost-frame/) |
| Hidden Patronus | 1000 | [writeup](forensics/hidden-patronus/) |
| Who Let the Dog Out | 983 | [writeup](forensics/who-let-the-dog-out/) |
| 💉 (Syringe) | 1000 | [writeup](forensics/syringe/) |

### Misc
| Challenge | Points | Writeup |
|---|---:|---|
| Game of Life | 751 | [writeup](misc/game-of-life/) |
| Insanity Check | 1000 | [writeup](misc/insanity-check/) |
| Invisible Scan | 1000 | [writeup](misc/invisible-scan/) |

### N-day
| Challenge | Points | Writeup |
|---|---:|---|
| PDF Strikes Again | 1000 | [writeup](nday/pdf-strikes-again/) |
| XXXLSXXX | 1000 | [writeup](nday/xxxlsxxx/) |

### Pwn
| Challenge | Points | Writeup |
|---|---:|---|
| lets get to library | 1000 | [writeup](pwn/lets-get-to-library/) |
| Most Secure Bank Of Endia | 999 | [writeup](pwn/most-secure-bank-of-endia/) |
| Original Unlimited Codex 100% Free | 1000 | [writeup](pwn/original-unlimited-codex-100-free/) |

### Rev
| Challenge | Points | Writeup |
|---|---:|---|
| Patcher 1 | 999 | [writeup](rev/patcher-1/) |
| Patcher 2 | 1000 | [writeup](rev/patcher-2/) |
| Shherrr | 1000 | [writeup](rev/shherrr/) |
| simphell | 1000 | [writeup](rev/simphell/) |

### Web
| Challenge | Points | Writeup |
|---|---:|---|
| Lazarus | 1000 | [writeup](web/lazarus/) |
| Solevault | 1000 | [writeup](web/solevault/) |

> Points are the CTFd **dynamic** score recorded for each challenge (they fall as
> more teams solve), so they roughly track how few teams had each one.

---

## Overview

kBxAc CTF 2026 was a Jeopardy-style CTF on CTFd spanning Crypto, Forensics, Misc,
N-day, Pwn, Rev, and Web. This repository collects our solves across all seven
categories; each writeup is meant to be read start-to-finish — the recon, the
"aha" moment, the underlying vulnerability or trick, and a reproducible solve.

A few that stood out:

- **Web — Lazarus:** an auth bypass built on the gap between a *case-sensitive*
  framework check (CVE-2025-29927 middleware skip) and a *case-insensitive* app
  check of the same header — `Middleware` slips through where `middleware` is
  eaten — chained into admin cache poisoning.
- **Web — Solevault:** SQL injection that evades a signature-based WAF by swapping
  the famous `OR 1=1` tautology for the equivalent `OR(1)`.
- **N-day — PDF Strikes Again / XXXLSXXX:** real n-day exploitation of known bugs
  in native parsing libraries (PyMuPDF / libxlsxwriter), driven to shell.
- **Pwn — Original Unlimited Codex 100% Free:** a full glibc 2.43 heap chain
  (House of Einherjar → tcache poisoning → `environ` stack leak → ORW ROP under
  seccomp).
- **Crypto — Dead Validator / Icarus Enclave:** multi-stage recovery chains where
  each cracked layer leaked the key material for the next.
- **Crypto — Crossword 1 / 2:** themed crosswords whose grids reconstruct some of
  the longest flags you will ever paste into a submit box.

---

## Repository Layout

```
<category>/<challenge-slug>/
├── README.md        # the writeup
├── solve.py …       # final solve script(s) / exploit (name varies)
└── …                # essential challenge files (source, handout, binary, capture, …)
```

Categories: `crypto/`, `forensics/`, `misc/`, `nday/`, `pwn/`, `rev/`, `web/`.

> Oversized originals — multi-MB media, vendored libraries, and decompiler dumps —
> are intentionally omitted and either linked or described in the relevant writeup.
> Challenge connection strings/URLs that were handed to every competitor are kept
> for context; the event infrastructure is no longer online.
