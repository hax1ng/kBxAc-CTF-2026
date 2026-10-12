#!/usr/bin/env python3
"""
Crossword 1 — kBxAc CTF 2026 (Crypto, 1000pts)
Solve a FOOTBALL-themed codeword (cipher crossword) and build the flag.

Pipeline:
  1. OCR the PNG grid -> number per cell (1..26), clustering cells by exact pixel pattern.
  2. Solve the codeword: every across/down run must be a valid football word.
     Constraint-propagation on the number->letter bijection pins all 26 letters.
  3. Build flag per instructions.txt: read each row's letters L->R, join rows with '_', wrap kBxAc{}.
"""
import json, hashlib
from collections import defaultdict
import numpy as np
from PIL import Image

PNG = 'attachments/crossword.png'

# ---------- 1. OCR grid ----------
# hash(36x36 box pixels) -> digit, read off a rendered montage of the 26 clusters
HASHMAP = {
 '030da477':18,'0749ee55':22,'0b8ba828':20,'261ed34c':12,'29b980b8':6,
 '2b10f23d':10,'2d7ca7f1':3,'4bcf8cc0':16,'55c00b3b':25,'58fc8119':5,
 '6414040f':15,'654419a6':14,'71612fff':9,'744b9507':4,'882a9434':23,
 '89eab039':11,'9650b396':26,'99c8c1df':8,'9daca0d4':19,'a8bc18fb':13,
 'b2a3c572':1,'c8c09a67':7,'d120c43f':24,'dd976f45':2,'fa555215':21,'fe3d8a88':17}

ab = (np.array(Image.open(PNG).convert('L')) > 128).astype(np.uint8)
H, W = ab.shape
nrows, ncols = H // 40, W // 40           # 40px cell pitch -> 31 x 45
grid = [[0]*ncols for _ in range(nrows)]
for r in range(nrows):
    for c in range(ncols):
        box = ab[r*40+2:r*40+38, c*40+2:c*40+38]
        if box.mean() > 0.3:              # white box == filled cell
            grid[r][c] = HASHMAP[hashlib.md5(box.tobytes()).hexdigest()[:8]]

# ---------- 2. solve codeword ----------
def entries():
    out = []
    for r in range(nrows):               # across
        c = 0
        while c < ncols:
            if grid[r][c]:
                s = c
                while c < ncols and grid[r][c]: c += 1
                if c-s >= 2: out.append([grid[r][x] for x in range(s, c)])
            else: c += 1
    for c in range(ncols):               # down
        r = 0
        while r < nrows:
            if grid[r][c]:
                s = r
                while r < nrows and grid[r][c]: r += 1
                if r-s >= 2: out.append([grid[x][c] for x in range(s, r)])
            else: r += 1
    return out

def sig(seq):
    mp = {}; o = []
    for x in seq:
        mp.setdefault(x, len(mp)); o.append(mp[x])
    return tuple(o)

words = set()
for path in ('/usr/share/dict/american-english',):
    for line in open(path):
        w = line.strip().upper()
        if w.isalpha() and len(w) >= 2: words.add(w)
try:
    from wordfreq import top_n_list
    for w in top_n_list('en', 100000):
        w = w.upper()
        if w.isalpha() and len(w) >= 2: words.add(w)
except Exception:
    pass
# football terms missing from general dictionaries
for w in ("goalkeeper keeper striker forward winger midfielder defender captain referee linesman "
          "offside penalty corner freekick header volley tackle dribble assist crossbar goalpost "
          "stadium manager coach substitute substitution formation football soccer league champions "
          "championship pitch fullback sweeper centreback playmaker kickoff relegation quarterfinal "
          "semifinal shootout possession counterattack touchline shinpad yellowcard redcard "
          "penaltyshootout targetman extratime injurytime futsal tactics worldcup tournament").split():
    words.add(w.upper())

by_sig = defaultdict(list)
for w in words: by_sig[(len(w), sig(w))].append(w)
ent = entries()
cands = [by_sig.get((len(e), sig(e)), []) for e in ent]

num2let, let2num = {}, {}
def consistent(e, w):
    for n, ch in zip(e, w):
        if num2let.get(n, ch) != ch or let2num.get(ch, n) != n: return False
    return True
def apply(e, w):
    for n, ch in zip(e, w):
        num2let[n] = ch; let2num[ch] = n

changed = True
matched = [None]*len(ent)
while changed:                           # propagate: an entry with one consistent candidate pins letters
    changed = False
    for i, e in enumerate(ent):
        if matched[i]: continue
        cl = [w for w in cands[i] if consistent(e, w)]
        if len(cl) == 1:
            apply(e, cl[0]); matched[i] = cl[0]; changed = True

assert len(num2let) == 26, f"only pinned {len(num2let)} letters"
print("key (number->letter 1..26):", ''.join(num2let[n] for n in range(1, 27)))

# ---------- 3. build flag (per instructions.txt) ----------
rows = [''.join(num2let[grid[r][c]] for c in range(ncols) if grid[r][c]) for r in range(nrows)]
flag = 'kBxAc{' + '_'.join(rows) + '}'
print(flag)
open('flag.txt', 'w').write(flag + '\n')
