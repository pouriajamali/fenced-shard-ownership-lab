# Ownership v1 contract

Synthetic single shard; trusted non-Byzantine workers, literal 127.0.0.1 endpoints and a dedicated ownership_lab database/user. A fencing token is not authentication. No orders, market, funds or production integration.

Coordination uses etcd 3.7.3, acquired key create_revision (not local time/current unrelated revision), exact signed-64-bit JSON strings and bounded complete acknowledgements. An unconfirmed/expired lease does not authorize new acquisition. Ownership becomes active only at committed sink activation. Old in-flight requests are rejected after that cutover, not merely on lease expiry.

The PostgreSQL transaction locks shard state, validates run/cluster/fence/owner, and stores the high-water fence, business effect and receipt atomically. Deduplication is UNIQUE(shard,businessOperationId) with a canonical digest independent of fence. A new owner may replay the same effect result. Conflicting identity reuse is rejected. A possible commit without reply is UNKNOWN, resolved only by same-identity lookup/retry. Neither timeout nor cancellation means rollback.

Fresh schema initialization refuses pre-existing schemas. Ordinary owned-process restarts retain state. Coordinator lineage resets and database rollback/restore are unsupported; no reset/restore path is supplied. External rollback cannot be universally detected by a self-contained database; admission after an out-of-contract restore is prohibited rather than claimed safe. Do not infer protection against arbitrary storage rollback from a run ID alone.

Quantity delta is 1..1,000,000; cumulative total uses checked signed 64-bit arithmetic. Identity is 1..64 ASCII letters/digits/dot/underscore/hyphen. Gateway first frame max 32 KiB, JSON depth 16, coordinator request deadline 3 seconds, CLI action deadline 15 seconds. No automatic retry with a new business ID.

CLI JSON integer fields are decimal strings so downstream readers do not silently round 64-bit fences or lease IDs through IEEE-754 numbers. The Python fixture controller uses exact integers. Test hooks pause only an owned CLI child; BeforeLock represents an already-started application transaction before the authoritative state lock, not a measured network-packet delay.

Acceptance: independent resulting-history checks, exact-integer and malformed/incomplete renewal tests, competing acquisition, paused/in-flight old worker, sink activation/effect crashes before and after commit, cross-generation idempotency/conflict, ordinary sink restart, unavailable sink and real quorum loss. A single-machine three-member cluster does not establish physical fault-domain independence or production HA. Timing is fixture coordination, not a trading-latency benchmark.

Initial local profile budget: 4 logical CPUs, 8 GiB lab RAM, 10 GiB task scratch; 120-second readiness, 60-second owned case, 15-minute profile cap, 256 MiB logs. These are provisional limits, not measured machine requirements. Existing Linux/WSL access required; no OS feature or container runtime installation is implied.
