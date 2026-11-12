# Same-source etcd fixture build - unreleased local candidate

The exact source and binary security checks are complete. Two fresh builds have
identical35,702,972-byte output, SHA256
`720420f5f09bf4acb5b32365eddd7594764fb74e3e2b22aa7d1ae67b844f2af6`.
The independent serving reference and pre-execution admission controls are now
finalized. The first guarded native version check passed for etcd3.7.3,
Git0a173d0, Go1.26.11, linux/amd64. Preparing the admitted bundle plus the five
PostgreSQL/library archives also passed without starting services. Earlier
user-bus readiness failures remain retained. Native package/client acceptance
and the complete signed M1 candidate are separate required checks.

The target is Linux/amd64. Native Windows and Linux C# clients use the same owned
Linux services; Windows uses existing Ubuntu WSL. The old affected upstream
binary is immutable historical evidence and is absent from default downloads.
Five PostgreSQL/library archive pins remain unchanged.

## Exact inputs and actual builds

Source commit:`0a173d0410a96d01091b484daae81365bbcde57e`.
The7,467,783-byte archive has SHA256
`f7628ecdb67353acdc708a42c4fb9e1267b4a1efed68ec1da83514406a598b60`.
All1,482 source files and11 symlinks matched the full independent Git tree.
The original13 workspace modules, go.work, all go.mod/go.sum files and behavior
remain unchanged. Only the compiler changes to the admitted Linux Go1.26.11.
Its66,999,944-byte archive has SHA256
`9849f4e04ee35303714e34fbc3ac8ab44ea3e448a95aa182f91e3b9b79c710ec`.

The frozen MVS has741 external metadata modules. Only58 source modules were
needed for the complete565-package entry graph, including prefix-parent absence
inputs. All58 original zip/mod h1 pairs were canonically SumDB-authenticated.
The actual binary has54 external dependencies and four original in-tree workspace
dependencies. The five original local source modules map to exact etcd3.7.3
source; their buildinfo versions remain honestly reported as `(devel)`.

The actual source/server command was:

```text
go build -mod=readonly -p=1 -trimpath -buildvcs=false -installsuffix=cgo
  -ldflags=-X=go.etcd.io/etcd/api/v3/version.GitSHA=0a173d0
  -o=<fresh-output>/etcd .
```

Both builds used distinct fresh caches/output with CGO0, linux/amd64/v1, local
pinned toolchain, no inherited Go overrides and readonly original workspace.
This is a maintainer build of the original source.

## Security and serving reference

The admitted shared govulncheck v1.9.0 image SHA256 is
`4857102574e6c761e98376d8045adde9a26f27edb81d95173b6a6d130c414759`.
Both actual source and binary JSON/SBOM protocols completed against the same
frozen primary DB archive SHA256
`714ff02d9533ec6ca269e565b61b27cbd959aa0af89d51f318261322e875861c`.
GO-2026-5932, GO-2026-6860 and GO-2026-6866 were module-only findings: their
OpenPGP/HTML packages are absent from the complete source graph and actual binary
symbol/type evidence. All three exact primary records and the source/binary
closures were bound. The bbolt record GO-2026-4923 is withdrawn.

SDK-vendor review is separate: exact source fixes cover IDNA/DNS; the SDK norm
case uses the unchanged NFC-only importer, source/init/function-pointer scope and
actual full40,875-symbol ELF binding. The seven lower iterator helpers remain
reported; no SDK Iter entry/type is linked. This composite goes beyond absence
of a symbol. The binary is static Linux amd64 without interpreter/dynamic input.

The independently held lock pins the actual binary and seven proof files under
vendor/etcd-admission. Original full source notices are preserved separately in
vendor/notices/ETCD-FIXTURE-SOURCES.json:71 components and144 texts. Metadata-only
source parents and tools are distinguished from linked fixture dependencies and
from the shipped C# managed/runtime SBOM.

## Portable reproduction and controls

The implemented default route reads only public URLs and source-held identities
in tools/etcd-build.inputs.json. It inventories raw archives, verifies original
metadata and full notices before source materialization, requires the SDK's
canonical signed SumDB checks, builds twice, and compares actual bytes with the
independent admitted image. Reused security proofs explicitly retain their frozen
snapshot scope. No private E-drive receipt is a public-build dependency.

After independent admission, the entry points are:

```text
python tools/fetch_services.py --out <fresh-archives>
python tools/prepare_linux.py --archives <fresh-archives> --out <fresh-services>
```

A consumer that already holds the admitted bundle can supply
`--etcd-bundle <bundle>` to prepare_linux. This rechecks actual bytes before reuse
and before first/member-restart spawns. Optional `--build-work` selects a separate
fresh native build workspace with real Unix mode semantics. Linux executes a
sealed exact-byte memfd; pathname replacement cannot change the selected image.

Every consuming operation needs actual aggregate kernel limits: at most4GiB,
two CPU cores,64 tasks, zero swap and finite wall/log/disk/input bounds. The owned
child stops before first exec for actual cgroup/limit readback. Windows profiles split that aggregate budget: the native client family must
already be in a Job limited to1GiB/one CPU/16 processes; the exact owned Linux
service unit receives3GiB/one CPU/48 tasks, zero swap. The integration entry
requires a fresh --service-unit and actual Job readback before any child.
The host records its invocation identity; shutdown checks the exact unit/token
and actual empty cgroup before the outer controller can release its lease. Shared operator phases use the canonical
atomic lease and terminal owned teardown; no foreign lease can be reset.

Thirteen Linux common/held-identity controls passed in normal/-O/PYTHONOPTIMIZE=1
modes. Actual resource controls passed in each mode, including wall/log limits,
a fast-exit disk write and preservation of a separate sentinel process. Portable
input tests cover changed original workspace objects, versions, h1, extra/missing
modules, raw size/hash and default/direct admission order. A Unix-mode test was
moved from DrvFS to the approved native evidence root; five unaffected completed
normal controls were retained.

End-to-end default reproduction, actual package helper/proof binding and both
16-case native C# profiles are required local acceptance steps. Their current
results belong to the exact candidate review packet. Public hosted CI is a
separate gate and is not established by shared tooling CI. Source/control evidence
alone does not establish runtime behavior, production operation or a public
release. Public push/CI/tag/release require the separate exact owner gate.
