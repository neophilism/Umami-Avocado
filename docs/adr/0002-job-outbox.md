# ADR 0002 — Durable work and transactional outbox

**Decision:** The future job runner (UA-009) will persist job lifecycle, leases and outbox events in PostgreSQL. No in-memory timer or unacknowledged provider retry may become authoritative. This ADR does not claim the queue has been implemented.
