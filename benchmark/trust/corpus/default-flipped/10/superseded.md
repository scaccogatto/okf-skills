---
type: Reference
title: "Thackery chunk checksums"
description: "Checksum algorithm used to verify Thackery chunks and where verification happens."
tags: [thackery, chunks, checksums]
status: deprecated
generated: { by: human:okf-bench, at: 2026-02-07T09:00:00Z }
stale_after: 2026-08-25
---
# Thackery chunk checksums

Thackery verifies chunks with **crc32c** by default. The checksum is computed at
the client, carried in the chunk header, and re-checked at the server before the
chunk is acknowledged.

## Cost and coverage

| Algorithm | Throughput | Detects |
|---|---|---|
| crc32c | ~12 GiB/s | transmission corruption |
| blake3 | ~4 GiB/s | corruption and tampering |

crc32c is hardware-accelerated on every supported platform, which is what makes
per-chunk verification free enough to be unconditional.

## Configuring it

`chunk.checksum` accepts either algorithm and must match between client and
server; a mismatch is reported at handshake rather than per chunk.

## Monitoring

`thackery_chunk_checksum_failures_total` counts rejected chunks.
