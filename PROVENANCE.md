# Verify preview provenance

The established portfolio ED25519 fingerprint is:

```text
SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU
```

Confirm it through a previously trusted checkout or independent maintainer channel. A key and fingerprint downloaded together are not independent identity proof. The private key is never distributed. Signed Git commits/annotated tags, exact-source archives, manifests, signed SHA256SUMS.txt and public-key assets are the provenance boundary. An unsigned checksum alone does not authenticate a release.

The preview.7 release provides all six assets. Downloaded bytes and the known-key SSH signature were verified; the examples below select that same explicit release.

After downloading the source archive, SHA256SUMS.txt, SHA256SUMS.txt.sig and SIGNING-PUBLIC-KEY.pub from the [same explicit release](https://github.com/pouriajamali/fenced-shard-ownership-lab/releases/tag/v0.1.0-preview.7), run tools/verify_downloads.py from a trusted checkout. Do not execute a newly downloaded verification script before establishing that trust.

## PowerShell

From a fresh directory, using a previously trusted checkout's tools/verify_downloads.py and existing OpenSSH/Python:

```powershell
$ErrorActionPreference = 'Stop'
$repo = 'pouriajamali/fenced-shard-ownership-lab'
$tag = 'v0.1.0-preview.7'
$archive = 'fenced-shard-ownership-lab-v0.1.0-preview.7-source.zip'
foreach ($name in @($archive, 'SHA256SUMS.txt', 'SHA256SUMS.txt.sig', 'SIGNING-PUBLIC-KEY.pub')) {
    Invoke-WebRequest -Uri "https://github.com/$repo/releases/download/$tag/$name" -OutFile $name
}
python /path/to/trusted/checkout/tools/verify_downloads.py --directory . --work verify-work --archive $archive --trusted-fingerprint 'SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU'
if ($LASTEXITCODE -ne 0) { throw 'Provenance verification failed' }
```

## POSIX shell

```sh
repo='pouriajamali/fenced-shard-ownership-lab'
tag='v0.1.0-preview.7'
archive='fenced-shard-ownership-lab-v0.1.0-preview.7-source.zip'
for name in "$archive" SHA256SUMS.txt SHA256SUMS.txt.sig SIGNING-PUBLIC-KEY.pub; do
  curl --fail --location --output "$name" "https://github.com/$repo/releases/download/$tag/$name" || exit 1
done
python3 /path/to/trusted/checkout/tools/verify_downloads.py --directory . --work verify-work --archive "$archive" --trusted-fingerprint 'SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU'
```

Replace only the trusted checkout path. The verifier accepts one canonical ed25519 SSH public-key blob and at most one terminal LF/CRLF; it rejects multiple lines, controls, noncanonical blobs or an algorithm mismatch. Its optional single-line comment is discarded. The fingerprint is calculated from that one blob and compared exactly/case-sensitively. The allowed-signers entry is reconstructed only from a fixed principal and canonical algorithm/blob; untrusted key-file text is never copied into it. The verifier then checks the SSH file-namespace signature, the explicitly selected archive and all signed archives present. A missing explicitly selected archive, duplicate or invalid checksum entry fails verification; other signed archives are verified when present. Windows/Linux archive names may replace the selected source archive. Existing outputs are not overwritten.

Trust-boundary validation uses explicit exceptions, not Python assertions, and remains active under python -O and PYTHONOPTIMIZE. Key, signature and checksum inputs are bounded and the verified checksum bytes are the same snapshot parsed for archive hashes. Archive hashes are streamed with a size cap. The regression suite checks real signed bytes and disposable attacker signatures in all three interpreter modes; only its receipt may be uploaded, not its disposable private-key directory.

GitHub build provenance attestations supplement this key-based verification when available. They do not establish a SLSA level, reproducible builds, exclusive ownership, safety, Windows Authenticode, exchange certification or production suitability. Original code uses MIT; upstream licenses and attribution remain independent. No existing release/tag/asset is overwritten.

## Preview.7 publication and verification boundary

The links/examples above select the published [v0.1.0-preview.7 release](https://github.com/pouriajamali/fenced-shard-ownership-lab/releases/tag/v0.1.0-preview.7) and its six verified assets. Runtime tag source is `bff39cd89822ceba07fce68c4dcdbf5819f09254`; documentation-only main revisions have a separate SHA. [CI43372419271 attempt1](https://github.com/pouriajamali/fenced-shard-ownership-lab/actions/runs/43372419271) succeeded on that runtime source. The archived README/source remains the tested build-time snapshot; current repository docs and release notes supply later availability status. The tested archives and historical tags/assets/signatures are unchanged.

The new signed `SHA256SUMS.txt` has exactly four entries: the three unchanged native/source CI archives and `SIGNING-PUBLIC-KEY.pub`. It is459 UTF-8/LF bytes with SHA256 `898aa935a4969b3ee51fa5490e55c77b9a8e55144cefa53cb1c04192ade86d4b`. Signature namespace is `file`, principal `pouriajamali`, using the independently trusted fingerprint above. Signature/self checksums are not entries. The downloadable public key is112 bytes/LF. The owner private key is never distributed.

Fresh CI has41 units and verifier8 tests/27 scenarios per OS, and native CLI help/version/endpoint guards per OS. The fresh16-case integration/21-SQL-snapshot evidence is Linux only; historical Windows-to-WSL integration is separate. MIT and upstream notices remain unchanged.

[The attestation](https://github.com/pouriajamali/fenced-shard-ownership-lab/attestations/67037698) binds all three archive digests to runtime source and run/attempt. Included-leaf ECDSA-SHA256 DSSE math and canonical workflow SAN were independently checked. Independent Fulcio-root and Rekor trust remain unverified; this is a limited inspection, not a general security or SLSA certification. The established SSH signature/fingerprint check is a separate release-byte verification boundary.

## NuGet metadata correction

Published preview.1 incorrectly used normalized NuGet contentHash as a managed-package SPDX raw-archive SHA512 and omitted the runtime raw checksum. Package/signature verification above is a separate check of release bytes and is not invalidated by that semantic finding. Preview.2 retains normalized identity separately and emits actual raw signed archive SHA512. `tools/check_sbom_archives.py` independently hashes cached NuGet archive bytes; its regression suite rejects the old mislabel and matching false metadata. See [preview.2 notes](docs/RELEASE-v0.1.0-preview.2.md). Old tags/assets/signatures remain unchanged. Each release has its own signed tag and downloadable verification evidence.

## Sealed tooling release provenance

The shared input tag is tooling-actionlint-v1.7.12-go1.26.11-r1 in
pouriajamali/data-admission-gate. Its two ZIP hashes/sizes are pinned in the
reviewed source lock. Verify the file-namespace signed SHA256SUMS against the
independently trusted ED25519 fingerprint printed above and principal
pouriajamali. Candidate PASS/self-hashes and a co-downloaded key alone are not
trust anchors. The archive carries all original tooling notices plus the
Go Vulnerability Database CC-BY-4.0 license/attribution. Producer path strings
are observations; fresh runtime reads only reviewed source and archive-relative
inputs. See docs/ACTIONLINT-BUILD.md for controlled import/default/direct routes.
