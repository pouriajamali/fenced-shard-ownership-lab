# Local fixture runbook

1. Verify the archive/source provenance and prerequisites in README. Use an existing non-root Ubuntu24.04 environment; Windows needs existing WSL access. The lab does not enable OS features, start system services or install runtime packages.
2. Fetch the five locked PostgreSQL/library archives and reproduce the independently admitted same-source etcd image using the exact source-held input references, or reuse an already admitted bundle. Extract to a NEW services folder and inspect PREPARED.json. See ETCD-FIXTURE-BUILD.md for the bounded native preparation route. Failures leave evidence; choose new output paths rather than overwriting a failed attempt.
3. Run tools/integration.py. Only its own local child processes and dedicated ownership_lab database are controlled. Endpoints are literal loopback; database role/name are checked before opening a connection. A new profile initializes a fresh schema and refuses an existing one.
4. Inspect receipt.json and named case results. An exit code or PASS from a different client OS is not evidence that this client was executed. Verify host/stopped.json says the owned processes stopped. Scratch data is retained at its recorded Linux path; no automatic recursive deletion is performed.
5. If failure.json/host-error.json appears, preserve it and sanitized logs. The private connection file contains a generated ephemeral password and must not be published. The package and CI proof uploads exclude runtime work directories.

## UNKNOWN and recovery

An effect can commit before the client receives a result. Retry/query the SAME business operation identity with the SAME delta. A different delta is a conflict; a different identity is a new operation, not recovery. Current-generation replay returns the original receipt. Old-generation requests are rejected after committed cutover even if their business ID once existed.

Ordinary process restart uses the same owned data and retains fencing/dedup state. Arbitrary database rollback/restore or rebuilding coordinator lineage is not a supported recovery workflow. Stop admission and review the contract; there is no force-reset or restore command. A run ID alone cannot prove byte-level state continuity after external rollback.

## Limits and practical costs

Preparation, SDK/compiler/build/audit/default/linter paths require an actual aggregate cap of at most4GiB, two CPU cores,64 tasks and zero swap. Only the explicit native Linux16 runtime selector uses an exact4GiB/two-CPU/128-task/swap-zero owned delegated unit for its controller, four concurrent CLI requests and service descendants. Run integration.py with `--runtime-profile native-linux-16` inside that already bounded unit. Both integration and host independently read actual kernel limits before children; missing selectors remain64, numeric/other selectors and129/unbounded limits reject. An environment value cannot select128. For a Windows client profile, an existing trusted controller must first place its entire native process family in a1GiB/one-CPU/16-process Job; integration.py reads the actual Job before launching children. Supply a fresh `--service-unit ownership06-<unique-suffix>` of at least eight suffix characters. The internal WSL entry creates only that owned transient unit with3GiB/one CPU/48 tasks/zero swap and a1080-second runtime limit. It uses an existing non-root user manager, with no install or configuration fallback. The exact-token terminal file belongs beside the profile output folder, matching the internal host entry contract. The exact invocation/token and actual empty kernel group are required at shutdown. The managed local controller holds the canonical atomic lease until both OS families are terminal. These are enforced caps, not measured minimum requirements. Readiness is120 seconds, individual CLI calls25 seconds and the host lifetime15 minutes; host logs stop at128MiB. Retained evidence records the actual caps and outcomes. The helpers do not change power, timer, host-security or unrelated settings. Report resource/access failure rather than disabling protections or inventing integration PASS.

If a Linux process fails, inspect only the task-owned PID/data paths shown in that profile. Never use killall, broad process-name termination, system PostgreSQL service commands, or arbitrary data-directory deletion. The supervisor's mailbox recognizes only named operations on the children it created and normally stops them in its finally block and at the bounded profile lifetime.

## Historical925d1d0 native Linux resource blocker

The exact925d1d0 Windows packaged profile passed16 cases. Its native Linux peer
stopped at the four-concurrent-client step. A separate bounded diagnosis recorded
64 tasks, pids.events max0->4, network-thread initialization errors and zero
memory OOM/kill events. Preserve this failure; do not raise the ceiling, serialize
requests, disable diagnostics or drop cases under the existing contract. The coordinator subsequently approved only the explicit native-Linux16
128-task runtime amendment. Eight affected finite controls passed on both OSs
in all three optimization modes, plus actual64/128 positives. Generic64 and
Windows budgets remain unchanged. Exact candidate package/profile outcomes
are recorded separately; the historical failure remains unchanged.

## Resource and stop evidence

Inspect host/stopped.json resourceCounters: actual before/after counters, kernel
pids.peak/memory.peak and separately labeled sampled peaks. Any new pids.max
failure, memory OOM or OOM kill rejects acceptance. Integration publishes PASS
only after host exit, stopped identity/counters and Windows exact terminal proof.
The outer owned controller separately verifies the actual native cgroup empty
before releasing its canonical lease. Preserve any new failure; no256-task
escalation, diagnostics/performance retuning or dropped/serialized fault case.
