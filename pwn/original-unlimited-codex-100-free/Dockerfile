FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY unlimited_codex_for_free .
COPY libc.so.6 .
COPY ld-2.43.so .
COPY flag.txt .
RUN chmod 555 unlimited_codex_for_free ld-2.43.so && chmod 444 libc.so.6 flag.txt \
    && useradd -m -u 1337 player

USER player
EXPOSE 1337
CMD ["socat", "TCP-LISTEN:1337,reuseaddr,fork", "EXEC:/app/unlimited_codex_for_free,stderr"]
