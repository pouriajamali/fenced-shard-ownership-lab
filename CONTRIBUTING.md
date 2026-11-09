# Contributing

Start with README's demo and docs/CONTRACT.md. Keep changes bounded and reproducible; provide the failing history, expected invariant and a test that distinguishes the repaired behavior. Keep credentials and entire runtime work directories out of issues/PRs. Share only sanitized receipt excerpts.

Core/domain changes need exact-integer/framing tests and the independent fault-history check. Gateway changes need malformed, incomplete, expired and wrong-identity acknowledgements. Sink changes need before/after-commit interruption and cross-generation idempotency tests. Preserve the single-shard scope and interfaces; propose scope changes before implementing an extra protocol, dependency or framework.

For a review, explain alternatives, failure boundaries, resource/OS impact and the evidence actually run. A successful static check is not integration, performance, HA or security certification. Do not claim team-management experience on the strength of a synthetic review exercise.

CI and release changes must use exact dependencies/action commits, preserve notices and actual SBOM boundaries, and execute the extracted native packages. Release tags and previously published artifacts are immutable. Source/tag/checksum signing uses the established public key; do not submit private keys or request weaker OS/security settings.
