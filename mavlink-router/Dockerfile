# mavlink-router for dexi-sim-ftw default stack
#
# Builds the mavlink-router binary from source against debian:bookworm-slim
# (no Debian package exists in bookworm). Final image strips build deps to
# keep size down. Shares the same upstream + build recipe as sim-outdoor's
# mavlink-router image — the only difference is the bundled config, which
# targets this stack's 172.20.0.0/16 network and keeps the existing
# code-server MAVSDK flow intact.

FROM debian:bookworm-slim AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
        git ca-certificates \
        build-essential \
        meson ninja-build \
        pkg-config \
        python3 python3-future \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git clone --depth 1 https://github.com/mavlink-router/mavlink-router.git \
    && cd mavlink-router \
    && git submodule update --init --recursive --depth 1

WORKDIR /src/mavlink-router
RUN meson setup build . \
        --buildtype=release \
        -Dsystemdsystemunitdir= \
    && ninja -C build \
    && DESTDIR=/out ninja -C build install


FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /out/usr/bin/mavlink-routerd /usr/local/bin/mavlink-routerd
COPY config/main.conf /etc/mavlink-router/main.conf

EXPOSE 5760/tcp 24540/udp 24550/udp

ENTRYPOINT ["/usr/local/bin/mavlink-routerd", "-c", "/etc/mavlink-router/main.conf"]
