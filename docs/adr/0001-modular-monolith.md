# ADR 0001 — Modular monolith

**Decision:** One React web workspace and one Python scientific domain/API, with a separately runnable worker; use PostgreSQL and S3-compatible object storage. Avoid Kafka, Kubernetes and separately deployed microservices until measured needs require them. Logical domain boundaries must remain explicit.
