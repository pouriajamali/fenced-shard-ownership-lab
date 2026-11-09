# Bounded failure matrix

| Boundary | Fixture/check | Expected invariant |
| --- | --- | --- |
| Owned-key acquisition | Exact >2^53 integer, mismatched owner/lease/revision, competing worker | No rounded/unconfirmed token activates a sink. |
| Renewal | Complete positive TTL and matching lease/cluster; truncated/oversized/error/duplicate fields | HTTP 200 alone does not authorize renewal. |
| Old actor | Owned child paused BeforeLock, then new committed activation | Resumed old transaction is rejected without an effect. |
| Activation interruption | Kill owned child BeforeCommit / AfterCommit | Old state survives before commit; new fence survives commit without acknowledgement. |
| Effect interruption | Kill owned child BeforeCommit / AfterCommit | Same identity resolves absent / one stored result; no invented rollback from missing response. |
| Retry under another owner | Reuse original business ID/digest | Stored original result, not another increment. |
| Concurrent retries | Four same-identity clients | One effect and three replay responses. |
| Changed payload | Same business ID, different delta | Conflict, no effect. |
| Run/cluster mismatch | Distinct declared lineage | Reject without resetting fence or history. |
| Sink restart/unavailable | Owned PostgreSQL process stop/start | Preserve durable history; unavailable outcome is resolved using the same identity. |
| Quorum loss | Stop two of three owned etcd members | No new acquisition; report unavailable coordination. |
| Arithmetic/domain | Independent BigInteger boundary comparison; invalid delta | No wrap or partial effect. |
| Observability | Redacted OpenTelemetry trace on a replay | Same business result, no credentials/payload/SQL in exported fields. |

The independent Python oracle queries PostgreSQL state and effects, reconstructs the operation set and sum, and compares the active fence/owner/lineage. Receipt counts describe this finite fixture only. Source unit checks, native client execution, local process faults and exact public-download verification remain distinct evidence classes.

Out of scope: Byzantine workers, arbitrary external storage rollback/restore, cross-region/network timing, independent physical fault domains, authenticated multi-tenant service operation, market/account connectivity, financial correctness outside this synthetic increment contract, and production HA/exactly-once delivery claims.
