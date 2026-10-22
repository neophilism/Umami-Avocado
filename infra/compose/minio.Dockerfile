FROM golang:1.24.8-alpine3.22 AS build
RUN GOBIN=/out CGO_ENABLED=0 go install github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z

FROM alpine:3.22.1
RUN addgroup -S minio && adduser -S -G minio minio
COPY --from=build /out/minio /usr/local/bin/minio
USER minio
ENTRYPOINT ["minio"]
