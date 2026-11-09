# v0.1.0-preview.2 - metadata correction

Corrects NuGet/SPDX checksum semantics without changing the C# ownership/fencing/idempotency algorithms, wire contracts, dependency lock versions or service fixtures.

NuGet `contentHash` identifies normalized package content excluding signatures. It is retained as restore identity in DEPENDENCIES.json, and is no longer labelled as a SHA512 of a downloadable signed `.nupkg`. SPDX checksums now hash actual raw signed upstream archive bytes, pinned separately in the notice mappings. The runtime gets the same raw-checksum treatment plus its original package metadata copyright. Full existing license and third-party notices remain preserved.

An independent verifier reads and hashes actual cache archives for every shipped dependency rather than comparing two matching metadata claims. Counterexamples reject the old normalized-checksum mislabel, a tampered raw archive and paired false dependency/SBOM hashes. Existing native correctness and failure cases remain required for the exact new candidate.

The published preview.1 archives, tag, signatures and hashes are retained unchanged. Its SPDX semantic defect is acknowledged explicitly, not reinterpreted as archive tampering or silently repaired by replacing assets. Preview.2 uses a separate signed tag and pipeline; release-byte verification is recorded independently. There is no market/order/account, production, performance, exclusive ownership, OS code-signing or reproducible-build claim.

Primary semantics: [NuGet nupkg metadata design](https://github.com/NuGet/Home/wiki/Nupkg-Metadata-File) and [NuGet signed-package content hash discussion](https://github.com/NuGet/Home/issues/10787). A raw archive checksum describes the bytes used at build time; upstream re-signing would change those bytes and requires an explicit new pin/review.
