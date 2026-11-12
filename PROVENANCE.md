# Verify preview provenance

The established portfolio ED25519 fingerprint is:

```text
SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU
```

Confirm it through a previously trusted checkout or independent maintainer channel. A key and fingerprint downloaded together are not independent identity proof. The private key is never distributed. Signed Git commits/annotated tags, exact-source archives, manifests, signed SHA256SUMS.txt and public-key assets are the provenance boundary. An unsigned checksum alone does not authenticate a release.

After downloading the source archive, SHA256SUMS.txt, SHA256SUMS.txt.sig and SIGNING-PUBLIC-KEY.pub from the [same explicit release](https://github.com/pouriajamali/fenced-shard-ownership-lab/releases/tag/v0.1.0-preview.1), run tools/verify_downloads.py from a trusted checkout. Do not execute a newly downloaded verification script before establishing that trust.

## PowerShell

From a fresh directory, using a previously trusted checkout's tools/verify_downloads.py and existing OpenSSH/Python:

```powershell
$ErrorActionPreference = 'Stop'
$repo = 'pouriajamali/fenced-shard-ownership-lab'
$tag = 'v0.1.0-preview.2'
$archive = 'fenced-shard-ownership-lab-v0.1.0-preview.2-source.zip'
foreach ($name in @($archive, 'SHA256SUMS.txt', 'SHA256SUMS.txt.sig', 'SIGNING-PUBLIC-KEY.pub')) {
    Invoke-WebRequest -Uri "https://github.com/$repo/releases/download/$tag/$name" -OutFile $name
}
python /path/to/trusted/checkout/tools/verify_downloads.py --directory . --work verify-work --archive $archive --trusted-fingerprint 'SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU'
if ($LASTEXITCODE -ne 0) { throw 'Provenance verification failed' }
```

## POSIX shell

```sh
repo='pouriajamali/fenced-shard-ownership-lab'
tag='v0.1.0-preview.2'
archive='fenced-shard-ownership-lab-v0.1.0-preview.2-source.zip'
for name in "$archive" SHA256SUMS.txt SHA256SUMS.txt.sig SIGNING-PUBLIC-KEY.pub; do
  curl --fail --location --output "$name" "https://github.com/$repo/releases/download/$tag/$name" || exit 1
done
python3 /path/to/trusted/checkout/tools/verify_downloads.py --directory . --work verify-work --archive "$archive" --trusted-fingerprint 'SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU'
```

Replace only the trusted checkout path. The verifier accepts one canonical ed25519 SSH public-key blob and at most one terminal LF/CRLF; it rejects multiple lines, controls, noncanonical blobs or an algorithm mismatch. Its optional single-line comment is discarded. The fingerprint is calculated from that one blob and compared exactly/case-sensitively. The allowed-signers entry is reconstructed only from a fixed principal and canonical algorithm/blob; untrusted key-file text is never copied into it. The verifier then checks the SSH file-namespace signature, the explicitly selected archive and all signed archives present. Missing/duplicate/invalid entries fail verification. Windows/Linux archive names may replace the selected source archive. Existing outputs are not overwritten.

Trust-boundary validation uses explicit exceptions, not Python assertions, and remains active under python -O and PYTHONOPTIMIZE. Key, signature and checksum inputs are bounded and the verified checksum bytes are the same snapshot parsed for archive hashes. Archive hashes are streamed with a size cap. The regression suite checks real signed bytes and disposable attacker signatures in all three interpreter modes; only its receipt may be uploaded, not its disposable private-key directory.

GitHub build provenance attestations supplement this key-based verification when available. They do not establish a SLSA level, reproducible builds, exclusive ownership, safety, Windows Authenticode, exchange certification or production suitability. Original code uses MIT; upstream licenses and attribution remain independent. No existing release/tag/asset is overwritten.

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
