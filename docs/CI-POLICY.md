# CI resource policy

This describes the runtime-tag workflow at `bff39cd89822ceba07fce68c4dcdbf5819f09254` and subsequent documentation revisions. It records actual checks and limits; it does not itself authorize a CI event, account change or release.

## Trigger and classification

- Push validation targets main and the separately scoped prerequisite-probe branch; the task feature branch is excluded. Tags retain full native checks and exclude the shared support-tooling tag. PR and explicit dispatch routes remain separate.
- A documentation allowlist performs actual UTF-8/framing, Markdown fence/relative-link and frozen JSON/policy checks plus the admitted sealed linter. Unknown/failed comparisons, runtime/configuration/fixtures/licenses/provenance/pipeline changes require native checks. Root PROVENANCE.md is not a docs-only shortcut. Tags/manual runs cannot take the docs-only path.
- A documentation-only commit relative to BFF can still require full native validation against an earlier main source; PROVENANCE classification also requires that route. RuntimeTagSource remains `bff39cd89822ceba07fce68c4dcdbf5819f09254`; documentation-only main revisions have a distinct SHA. Main CI is separate from runtime-tag CI and does not replace the frozen release bytes.
- Main/tag/manual runs have unique concurrency groups; only superseded PR runs may cancel. Matrix native jobs retain max-parallel1/fail-fastfalse. This is a workflow scope, not an account-wide quota.

## Actual jobs and limits

Policy runs on windows-2025 with a5-minute ceiling and actual Windows Job4GiB/twoCPU/64 limits. The source-pinned sealed Windows actionlint route and existing policy tests/classifier are used; this is not the old generic download-an-official-linter-on-Ubuntu path. Optional external ShellCheck/Pyflakes results are not claimed. The special read-only probe has its own5-minute ceiling and runs only on its explicit branch; it is skipped for the runtime tag.

Native windows-latest/win-x64 and ubuntu-24.04/linux-x64 jobs each have15-minute ceilings. Source-pinned private SDK404 raw/member/full-notice validation precedes first locked restore. Runtime15, fixed source/maps/guards and actual per-phase ownership/caps apply. Windows generic Job limits are4GiB/twoCPU/64; Linux verify/prepare use4GiB/twoCPU/64/zero swap; explicit native-linux-16 runtime alone uses128 tasks. Aggregate has a10-minute ceiling and runs on version tags or the explicit verification input, with exact native/source checksum and attestation subjects.

A host deadline includes checkout, all phases, post-actions and uploads. Inner verify900/prepare240/runtime1080/aggregate480-second walls cannot guarantee teardown time. Missing current-source typed owned terminal0, positive canonical release, required resource counters/XML/receipts means HOLD. No global kill, relaxed guard/cap, automatic retry or artificial green check follows.

## Evidence and artifacts

[Runtime tag CI43372419271 attempt1](https://github.com/pouriajamali/fenced-shard-ownership-lab/actions/runs/43372419271) succeeded: policy, both native jobs and aggregate. Each OS supplied41 C# units, verifier8/27 in three modes and native packaged CLI help/version/endpoint checks. Fresh16 integration cases and21 SQL snapshots are Linux only; historical Windows integration remains separate. A green docs/policy check is not runtime or publication proof.

Normal source/PR checks retain the original native validation without uploading large delivery bundles; finite proof receipts remain. Tag/manual review routes retain native bundles. Ordinary proof retention is3 days, tag/manual artifacts7 days, and safe failure facts3 days. These are temporary Actions artifacts; published archives/SUMS/signatures/public key are a distinct immutable delivery boundary. No old artifact/cache deletion, paid capacity, self-hosted runner, permission/protection/security or account-budget change is authorized.

The published [preview.7 release](https://github.com/pouriajamali/fenced-shard-ownership-lab/releases/tag/v0.1.0-preview.7) has six assets verified by actual download, digest and known-key SSH signature. The archives retain the tested build-time README/source snapshot; current repo docs/release notes give later publication status. Runtime SDK404/Core15 and exact-source manifests/notices remain the archive boundary. Included-leaf DSSE math/SAN/subjects/source/run were checked; independent Fulcio-root and Rekor trust was not verified. No SLSA level/general security/HA/latency claim follows. Current artifact sizes and raw job seconds do not certify billing/storage usage.
