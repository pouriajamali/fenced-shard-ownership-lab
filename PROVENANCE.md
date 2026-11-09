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
$tag = 'v0.1.0-preview.1'
$archive = 'fenced-shard-ownership-lab-v0.1.0-preview.1-source.zip'
foreach ($name in @($archive, 'SHA256SUMS.txt', 'SHA256SUMS.txt.sig', 'SIGNING-PUBLIC-KEY.pub')) {
    Invoke-WebRequest -Uri "https://github.com/$repo/releases/download/$tag/$name" -OutFile $name
}
python /path/to/trusted/checkout/tools/verify_downloads.py --directory . --work verify-work --archive $archive --trusted-fingerprint 'SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU'
if ($LASTEXITCODE -ne 0) { throw 'Provenance verification failed' }
```

## POSIX shell

```sh
repo='pouriajamali/fenced-shard-ownership-lab'
tag='v0.1.0-preview.1'
archive='fenced-shard-ownership-lab-v0.1.0-preview.1-source.zip'
for name in "$archive" SHA256SUMS.txt SHA256SUMS.txt.sig SIGNING-PUBLIC-KEY.pub; do
  curl --fail --location --output "$name" "https://github.com/$repo/releases/download/$tag/$name" || exit 1
done
python3 /path/to/trusted/checkout/tools/verify_downloads.py --directory . --work verify-work --archive "$archive" --trusted-fingerprint 'SHA256:AgU5bZlJSjUu0KsWMmVEEr+BfXpcMVNroTA33bHcQdU'
```

Replace only the trusted checkout path. The verifier first checks the exact fingerprint and SSH file-namespace signature, then the explicitly selected archive and all signed archives present. Missing/duplicate/invalid entries fail verification. Windows/Linux archive names may replace the selected source archive. Existing outputs are not overwritten.

GitHub build provenance attestations supplement this key-based verification when available. They do not establish a SLSA level, reproducible builds, exclusive ownership, safety, Windows Authenticode, exchange certification or production suitability. Original code uses MIT; upstream licenses and attribution remain independent. No existing release/tag/asset is overwritten.
