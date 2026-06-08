# mavlink2rest for the default dexi-sim-ftw stack
#
# Identical to sim-outdoor/mavlink2rest's Dockerfile — same upstream, same
# pinned SHA, same multi-arch build. Default CMD's IP differs (172.20.0.9
# = mavlink-router in this stack's network).

FROM rust:alpine AS build

RUN apk add --no-cache musl-dev alpine-sdk pkgconfig

WORKDIR /usr/src/mavlink2rest

# Pinned to upstream release tag 1.0.2 (SHA 237c8899c29f84d28af02d928263558a31017f3e).
# Keep in sync with sim-outdoor/mavlink2rest/Dockerfile + the binary baked
# into dexi-os so the sim image and Pi image are byte-identical at this layer.
RUN apk add --no-cache git \
    && git clone https://github.com/mavlink/mavlink2rest.git . \
    && git checkout 237c8899c29f84d28af02d928263558a31017f3e \
    && cargo build --release \
    && cp target/release/mavlink2rest /usr/local/bin/mavlink2rest \
    && strip /usr/local/bin/mavlink2rest


FROM alpine:3.19

RUN apk add --no-cache libgcc

COPY --from=build /usr/local/bin/mavlink2rest /usr/local/bin/mavlink2rest

EXPOSE 8088/tcp

# Defaults — overridable from docker-compose `command:`.
ENTRYPOINT ["/usr/local/bin/mavlink2rest"]
CMD ["--connect=udpout:172.20.0.9:14770", "--server=0.0.0.0:8088"]
