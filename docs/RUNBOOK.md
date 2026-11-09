# Local fixture runbook

1. Verify the archive/source provenance and prerequisites in README. Use an existing non-root Ubuntu24.04 environment; Windows needs existing WSL access. The lab does not enable OS features, start system services or install runtime packages.
2. Fetch six locked upstream fixture archives, extract to a NEW services folder and inspect PREPARED.json. Failures leave evidence; choose new output paths rather than overwriting a failed attempt.
3. Run tools/integration.py. Only its own local child processes and dedicated ownership_lab database are controlled. Endpoints are literal loopback; database role/name are checked before opening a connection. A new profile initializes a fresh schema and refuses an existing one.
4. Inspect receipt.json and named case results. An exit code or PASS from a different client OS is not evidence that this client was executed. Verify host/stopped.json says the owned processes stopped. Scratch data is retained at its recorded Linux path; no automatic recursive deletion is performed.
5. If failure.json/host-error.json appears, preserve it and sanitized logs. The private connection file contains a generated ephemeral password and must not be published. The package and CI proof uploads exclude runtime work directories.

## UNKNOWN and recovery

An effect can commit before the client receives a result. Retry/query the SAME business operation identity with the SAME delta. A different delta is a conflict; a different identity is a new operation, not recovery. Current-generation replay returns the original receipt. Old-generation requests are rejected after committed cutover even if their business ID once existed.

Ordinary process restart uses the same owned data and retains fencing/dedup state. Arbitrary database rollback/restore or rebuilding coordinator lineage is not a supported recovery workflow. Stop admission and review the contract; there is no force-reset or restore command. A run ID alone cannot prove byte-level state continuity after external rollback.

## Limits and practical costs

The initial profile budgets 4 logical CPUs, 8 GiB lab RAM, 10 GiB scratch (tool/image caches extra), 120-second readiness, 60-second case and 15-minute profile lifetime. Logs are capped at 256 MiB. These are provisional planning/stop limits, not measured minimum requirements or an OS-level aggregate CPU/RAM quota. The helpers do not change power, timer, host-security or unrelated settings. Report resource/access failure rather than disabling protections or inventing integration PASS.

If a Linux process fails, inspect only the task-owned PID/data paths shown in that profile. Never use killall, broad process-name termination, system PostgreSQL service commands, or arbitrary data-directory deletion. The supervisor's mailbox recognizes only named operations on the children it created and normally stops them in its finally block and at the bounded profile lifetime.
