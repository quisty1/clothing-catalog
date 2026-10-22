FROM golang:1.24.8-alpine AS build
RUN apk add --no-cache ca-certificates curl git
WORKDIR /src
ARG MINIO_COMMIT=7aac2a2c5b7c882e68c1ce017d8256be2feea27f
RUN curl -fsSL "https://codeload.github.com/minio/minio/tar.gz/${MINIO_COMMIT}" | tar xz --strip-components=1
RUN CGO_ENABLED=0 go build -trimpath -o /out/minio .

FROM alpine:3.22
RUN apk add --no-cache ca-certificates curl && addgroup -S minio && adduser -S minio -G minio && mkdir /data && chown minio:minio /data
COPY --from=build /out/minio /usr/local/bin/minio
USER minio
EXPOSE 9000
ENTRYPOINT ["minio"]
CMD ["server", "/data", "--console-address", ":9001"]
