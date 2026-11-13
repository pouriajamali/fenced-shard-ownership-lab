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


## Historical preview.4 policy and evidence boundary

The preview.3 tag at91469504bbdfd116da9af49058559072fbfc5461 is now a retained
failed native-CI attempt, not an application release. Earlier sections are
historical checkpoints. Run43313447070 attempt1 passed policy20s, held Windows
on the missing preinstalled SDK404 file, and held Linux before SDK/cap work
because its transient service lacked GITHUB_ACTIONS. No app/main/About delivery
followed. See [retained preview.3](RELEASE-v0.1.0-preview.3.md).

The proposed preview.4 keeps global.json404/disable, runtime15, managed locks,
RIDs, C#/SQL/digest/receipt behavior and all current resource ceilings. It changes
only the CI envelope and Windows SDK acquisition policy: fixed explicit safe
service environment, and exact official Windows SDK404 ZIP in the existing
bounded private verify Job. Its303618098-byte SHA512 and5578-member/10-notice
catalog reuse already sealed inputs; this draft runs no SDK or security review.
Linux remains preinstalled404 only. The first SDK target remains locked restore.
No setup action outside caps, global install, SDK probe, SDK artifact or cache is
permitted. Full SDK notices stay in its private tree. The new source and public
proofs remain pending; localA2 and support bytes are unchanged. The coordinator's
exact source/finite/public gate and independent tool review precede execution;
See [preview.4](RELEASE-v0.1.0-preview.4.md).

SDK download180s and total staging300s are elapsed-time acceptance guards
checked through final writes and before the first SDK target. Socket I/O has
a20s timeout; these checks are not fully preemptive I/O deadlines. The enclosing
verify Job retains its existing900s hard process wall. Workspace acceptance
remains4GiB and is not a filesystem quota.

## Proposed preview.5 policy and current boundary

Preview.4 is now a retained failed tag at `ada3a259f1d92606c954476a2da295d4731a6b91`.
Windows private SDK staging passed, then first restore failed; Linux reached its
existing404 file guard and held. No new application release resulted. A controlled
local Windows pair supports adding validated PROGRAMFILES(X86) and PROGRAMFILES
only on Windows. Hosted Windows repair remains unproven. The accepted safe facts
collector retains bounded structural facts and UNKNOWN root cause, never raw logs.

The preview.5 Linux helper is a draft for the existing nonroot generic64 verify
worker, not an alternate runner or global install. Before network it binds actual
source, lease, PID/start, unit, InvocationID and kernel4GiB/twoCPU/64/swap0.
The fixed builds.dotnet.microsoft.com HTTPS URL, raw243138887 bytes and both pinned
SHA512/SHA256 precede gzip parsing. Per-hop host checks, no proxy, socket20s,
input512MiB, unpacked2GiB and total ART4GiB acceptance apply. Download180s and
entire stage300s are elapsed acceptance guards including final flush/fsync,
notices, workspace and receipts, not preemptive I/O or filesystem quotas.
The existing verify900s hard wall and workflow20m remain.

Before creating the SDK target, strict framing/checksum/type/size/order/padding/
end checks validate all5631 typed members (4907 files,724 directories), exact
expanded644980579 bytes,1913 separate GNU-L payload identities, final resolved
names, every file hash and ten original notices. PAX is empty. UID/GID2001/2001
and approved644/744/755 modes are data-only E0; output is owned by the nonroot
worker with explicit approved chmod only. There is no extraction API, archived
ownership/timestamp restoration, link/special/sparse/ACL/xattr application.
Streamed copy and a complete final byte-map check precede the existing locked
restore, which remains the first SDK command. Full notices stay private.

Windows route/map, shared fixture support, runtime15 notices, managed/Go locks,
generic64 and explicit native-linux-16 runtime128 selector remain unchanged.
Only two safe Linux JSON receipt paths are added to accepted artifact globs;
SDK/cache/archive directories stay private. package.py reads the version from
Directory.Build.props; check_release.py already binds exact tag/version, source
commit/tree/bytes, native host/RID and localCandidate=false. These predicates
remain unchanged; only the aggregate caller's proposed tag changes to preview.5.
Linux stage/restore/runtime and hosted repair remain UNKNOWN. No candidate test,
SDK archive open or public event was performed to prepare this draft.

The accepted Linux source catalog retains its exact CRLF byte identity.
A narrow .gitattributes -text -eol rule for that catalog prevents Git LF
normalization from silently changing the helper's accepted source-lock pin.
