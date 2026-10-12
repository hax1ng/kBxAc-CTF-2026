FROM debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251 AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential wget ca-certificates libffi-dev libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev libncurses5-dev \
    libgdbm-dev liblzma-dev uuid-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN wget -q https://www.python.org/ftp/python/3.13.2/Python-3.13.2.tgz && \
    tar xf Python-3.13.2.tgz

WORKDIR /build/Python-3.13.2
RUN export CFLAGS="-O2 -fstack-protector-strong -D_FORTIFY_SOURCE=2" && \
    ./configure --prefix=/opt/python3.13 --disable-shared && \
    make -j$(nproc) && \
    make install && \
    ln -sf python3.13 /opt/python3.13/bin/python3 && \
    cd /opt/python3.13/bin && \
    gcc -no-pie -O2 -fstack-protector-strong -D_FORTIFY_SOURCE=2 -Xlinker -export-dynamic -o python3.13.nopie \
        /build/Python-3.13.2/Programs/python.o \
        /build/Python-3.13.2/libpython3.13.a \
        -lpthread -ldl -lutil -lm -lz -lffi && \
    mv python3.13.nopie python3.13

FROM debian:bookworm-slim@sha256:3783cc01769c7b2b1b83a5c5ad96c815348e28ed7da68e2e3687004faa906251

RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-traditional libffi8 libssl3 zlib1g && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/python3.13 /opt/python3.13
ENV PATH="/opt/python3.13/bin:$PATH"

RUN python3 -m pip install --no-cache-dir --timeout 100 --retries 10 flask pymupdf==1.28.2

RUN useradd -m -s /bin/bash ctfuser

WORKDIR /app
COPY app.py .

RUN echo "kBxAc{TEST_FLAG}" > /flag.txt && \
    chmod 444 /flag.txt

EXPOSE 5000

USER ctfuser

CMD ["python3", "app.py"]
