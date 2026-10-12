FROM debian:sid AS builder
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git ca-certificates zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN git clone https://github.com/jmcnamara/libxlsxwriter.git && \
    cd libxlsxwriter && \
    git checkout 3227eb0c1556ba41d94605a7abee0e097782d10a && \
    make -j$(nproc)

FROM debian:sid
ENV DEBIAN_FRONTEND=noninteractive PORT=5000

RUN apt-get update && apt-get install -y --no-install-recommends \
    zlib1g gzip ca-certificates netcat-traditional && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /build/libxlsxwriter/lib/libxlsxwriter.so* ./lib/
COPY sheetforge .
COPY flag.txt /flag.txt
RUN chmod 555 sheetforge && chmod 444 lib/libxlsxwriter.so* /flag.txt \
    && useradd -m -u 1337 player

USER player
EXPOSE 5000
CMD ["/app/sheetforge"]
