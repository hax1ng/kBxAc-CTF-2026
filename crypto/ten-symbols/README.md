# Ten Symbols

**Category:** Crypto · **Points:** 1000 · **Author:** devildev

> Top 10 ciphers that no one can crack
>
> (Flag note: add `_` between every word and wrap everything in `kBxAc{...}`.)

**Flag:** `kBxAc{ten_different_voices_whisper_from_the_dark_but_their_words_are_only_fragments_of_a_single_story_follow_every_symbol_until_the_hidden_truth_steps_into_the_light}`

---

## TL;DR

Despite the name, this is less about *breaking* encryption and more about **recognising ten different ways of writing the alphabet**. The ZIP contains ten pictures; each uses a different symbol system. Decode them in filename order, restore the word spaces, and you get one long sentence that becomes the flag.

## What We're Given

`chall.zip` unpacks to `img1.png` … `img10.png` (included here under [`images/`](images/)). Their numbering is the order of the final message. The key realisation: **each image switches alphabets** — one decoder won't work for all ten.

## The Core Concept — one cipher per image

| # | Symbol system | Decodes to |
|---|---|---|
| [`img1`](images/img1.png) | [Lunar alphabet (Leandro Katz)](https://www.dcode.fr/lunar-alphabet-leandro-katz) — moon-phase glyphs | **TEN DIFFERENT** |
| [`img2`](images/img2.png) | [Pigpen cipher](https://www.dcode.fr/pigpen-cipher) — fence shapes with/without dots | **VOICES WHISPER** |
| [`img3`](images/img3.png) | [Flag semaphore](https://commons.wikimedia.org/wiki/File:Semaphore_Signals_A-Z.jpg) — two arm/flag positions per letter | **FROM THE DARK** |
| [`img4`](images/img4.png) | [Chinese/Samurai scout code](https://www.dcode.fr/chinese-code) — horizontal strokes = vowel group, vertical = consonant | **BUT THEIR WORDS** |
| [`img5`](images/img5.png) | [Braille](https://en.wikipedia.org/wiki/Braille) — 2×3 dot cells | **ARE ONLY FRAGMENTS** |
| [`img6`](images/img6.png) | [Morse code](https://en.wikipedia.org/wiki/Morse_code) | **OF A SINGLE STORY** |
| [`img7`](images/img7.png) | [Bacon's cipher](https://en.wikipedia.org/wiki/Bacon%27s_cipher) — two marks → groups of five | **FOLLOW EVERY** |
| [`img8`](images/img8.png) | [Zu alphabet from *FEZ*](https://www.dcode.fr/fez-alphabet) | **SYMBOL UNTIL THE** |
| [`img9`](images/img9.png) | [Alien Language glyphs](https://www.dcode.fr/alien-language) | **HIDDEN TRUTH STEPS** |
| [`img10`](images/img10.png) | [Theban alphabet](https://www.dcode.fr/theban-alphabet) | **INTO THE LIGHT** |

### Details that trip people up

- **img3 (semaphore):** letters depend on *both* arm positions. If a chart gives nonsense, flip your perspective — the image shows the signaller facing you, while many charts show them from behind.
- **img4 (scout code):** looks like decorative tally marks but is coordinate-like — e.g. 1 horizontal + 1 vertical = **B**, 5 horizontal + 0 vertical = **U**. Read each cluster separately.
- **img5 (Braille):** don't read the cell as a picture of a letter; treat it as six numbered on/off dot positions and look the pattern up.
- **img6 (Morse):** `--- ..-. .- ... .. -. --. .-.. . ... - --- .-. -.--` → `OFASINGLESTORY`.
- **img7 (Bacon):** every **five** marks = one letter; `AABAB ABBBA ABABB …` → `FOL…` → `FOLLOWEVERY`.
- **img9:** line 1 is `HIDDENTRUTH`, line 2 is `STEPS` — a line break in an image isn't necessarily a word break.

Several images have no visible spaces; the spaces were restored from the English sentence afterwards, **not** by treating every image row/line break as a space.

## Putting It Together

Reading `img1` → `img10`:

> Ten different voices whisper from the dark, but their words are only fragments of a single story. Follow every symbol until the hidden truth steps into the light.

Lowercase it, replace word spaces with `_`, drop punctuation, and wrap per the description:

```
kBxAc{ten_different_voices_whisper_from_the_dark_but_their_words_are_only_fragments_of_a_single_story_follow_every_symbol_until_the_hidden_truth_steps_into_the_light}
```

## Key Takeaways

- A "ten ciphers" challenge is really a **cipher-identification drill**. Build a mental (or bookmarked) catalogue of symbol alphabets — [dcode.fr](https://www.dcode.fr/) is invaluable for identifying unknown glyph sets.
- Don't assume one scheme spans the whole challenge; the twist here is that every panel changes alphabet.
- Image structure (line breaks, rows) is a presentation detail — recover word boundaries from the decoded *language*, not the layout.
