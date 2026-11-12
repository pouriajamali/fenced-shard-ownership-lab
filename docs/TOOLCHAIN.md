# Reviewed toolchain and evidence boundary

- Original five-project technology review: 2026-11-09, proposal SHA256 686c06536e2b2fc49f95948fe192986cd714452800ee091fc29d5ca484dcf1b9. Direct owner implementation and original MIT/publication approval were separately verified in the coordinating chat; only this first independent project is implemented here.
- Frozen preview.2 used SDK 10.0.403 / runtime 10.0.14 / C# 14. global.json and explicit stable dependencies plus packages.lock.json freeze compiler/runtime/package choices. All Windows/Linux runtime identifiers are represented consistently in restore.
- Npgsql 10.0.3, OpenTelemetry 1.20.1, xUnit.net v3 package 4.0.3. The last is a stable patch newer than the proposal's 4.0.2 snapshot. Official NuGet version metadata was rechecked at the authorized freeze; no preview was selected.
- tools/upstream.lock.json freezes six Linux fixture artifacts and SHA256 digests. Four came from official etcd/PGDG HTTPS digest metadata; two runtime-library hashes came from the installed Ubuntu24.04 apt metadata and official Ubuntu archives. They are separately fetched references, not bundled server binaries, and no upstream vendor-signature verification is claimed.
- Actions were resolved through official release/tag metadata to immutable commits: checkout v7.0.1, setup-dotnet v6.1.0, setup-python v7.1.0, upload-artifact v7.0.2, download-artifact v8.0.2 and attest v4.2.2. The workflow contains those commit pins. Attestation mode is provenance with explicit checksum subjects and no registry/storage record; least-privilege job permissions apply only to aggregation/release.
- SBOMs represent the resolved/shipped managed packages and bundled runtime. They do not inventory the whole host OS, SDK, package cache or separately fetched Linux server installation. Upstream and .NET runtime notices remain included independently of the original MIT source.

This document records source/tool choices, not executable compatibility proof. Exact commit/tree, actual test/XML/package/fault receipts, CI jobs and downloaded asset verification establish the later delivery boundary. Local Linux cross-publishing is labelled as such; public Linux binaries require a native Linux CI build. No performance result, physical fault-domain redundancy, SLSA-level certification or independent people-leadership history is inferred.


## Current-source servicing checkpoint — 2026-11-11

The selected preview.3 source uses observed SDK10.0.404/Core and ASP.NET10.0.15
on native Windows x64 and existing non-root Ubuntu24.04/WSL Linux x64. This does
not mean ASP.NET is an application dependency: actual FrameworkReference is
Core only. All three managed locks remain byte-identical; 34 unique normalized
managed identities and actual raw archives were compared to acquired bytes.

Windows default NuGet verification passed for all39 acquired nupkgs. Linux
locked restore retained default trust validation, and explicit Linux verification
of the Core runtime nupkg passed. Only the two Core runtime15 notice records were
derived from actual cache metadata/nuspec/raw archive/full license and supplied
notice bytes. No normalized contentHash is labelled a raw signed-archive hash.
These checks establish their stated coverage, not general security.

Initial sealed-feed restore failed because SDK ProcessFrameworkReferences
prefetched unreferenced ASP.NET/Desktop runtime packs. Evaluation retained solely
Microsoft.NETCore.App. The task-private documented
DisableTransitiveFrameworkReferenceDownloads=true limits that prefetch; required
Core/runtime/host resolution and all signature/audit/lock guards remain active.
The scoped property is recorded in local argv/environment receipts and is not
a source/global configuration change. Actual future CI download behavior must
be checked separately; do not infer that CI used this private local option.
[Official SDK property](https://learn.microsoft.com/en-us/dotnet/core/project-sdk/msbuild-props#disabletransitiveframeworkreferencedownloads).

Both OSs passed41 C# units, Release builds, current direct/transitive NuGet
advisory queries and the eight receipt vectors normally and optimized. Existing
notice/SBOM/provenance and CI-policy regression receipts are separate. Linux's
disposable-attacker signing regression first failed on DrvFS private-file modes;
a fresh owned native0700 scratch with the unchanged test passed. No maintainer
private key was read, copied or changed.

The exact pinned etcd3.7.3 binary statically reports go1.26.10, revision
0a173d0410a96d01091b484daae81365bbcde57e. The official Go database published
GO-2026-6859 on2026-11-11, affecting this standard-library range (fixed1.26.11).
MaxBytesReader and its Read method names occur in the binary. This is not proof
of exploitability in the fixture, but applicability is unresolved and the
required native advisory gate is BLOCKED. No etcd fault profile has been run.
Other package-specific Go matches remain in the actual advisory receipt; no
absence/reachability certification is claimed.

The source-only historical .403/.14 fallback is not selected. The five PostgreSQL/Ubuntu-library
archive pins, C#/SQL/digest algorithms, signing identity and previous release
assets stay unchanged. The affected prebuilt etcd pin is retained as a historical
reference and removed from the default download list; the same-commit source-build
lock is still unadmitted. No public preview.3 exists from this checkpoint.

## Resumed local work boundary

The same-commit etcd rebuild with Go1.26.11 and a separately pinned advisory tool now has a complete local scope approval, including direct-entry admission and optimized-mode guards. Approval is not security acceptance. Exact Go/source archives and the pinned auditor source have now been acquired and fully inventoried. The actual Go1.26.11 SDK completed current source/backport/target/init advisory review and one native identity command after all 15,048 regular file hashes/modes were checked. Auditor/fixture source and binary admission is still pending. The prior Linux instance was removed during owner-directed storage work; its successful .NET/Linux SDK/unit observations remain historical. The replacement now has fresh actual aggregate cgroup and scoped Go SDK qualification. The Windows SDK starts from the migrated task root, and a separate owned Windows Job Object confirmed a 4GiB aggregate committed-memory limit, CPU limit and process limit. This is a resource-control observation, not a fixture or release result.

The E DrvFS mode mismatch is recorded as a preserved failed attempt. A narrowly approved private native workspace in the existing E-backed WSL VHD preserves source modes; no mount/configuration/security setting changed. SDK admission does not admit the separate analyzer, module graphs, source-built fixture or public workflow. Initial Windows synthetic archive/admission controls passed11 tests and95 rejected vectors per normal/-O/PYTHONOPTIMIZE=1 mode. Linux held-image checks, complete source-build negatives and real admitted positive controls remain pending.
