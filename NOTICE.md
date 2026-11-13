# Attribution and distribution boundaries

Original lab source is copyright 2026 Pouria Jamali, MIT. No private/shared system source, customer data or account configuration is included.

The archive's DEPENDENCIES.json and SBOM.spdx.json describe the actual resolved/shipped managed package graph and bundled .NET runtime; licenses/ retains full license texts, supplied third-party notices and per-package copyrights. Npgsql uses the PostgreSQL license. OpenTelemetry and other dependencies retain their own declared licenses. The original MIT license does not relabel those components.

Expression-only NuGet metadata does not substitute for a full license beside a binary. vendor/notices/NOTICE-SOURCES.json maps the exact 17 managed package identities/versions/content hashes to vetted full texts and original copyrights. It pins Npgsql v10.0.3/LICENSE and the Microsoft.Extensions packages' own dotnet/dotnet repository commit's src/runtime/LICENSE.TXT with SHA256 digests. The latter MIT text is accompanied by each package's separate Microsoft Corporation copyright from its nuspec, not inferred only from a runtime notice. OpenTelemetry's supplied full Apache and third-party notices remain included. A missing/changed license, copyright or unmapped resolved identity stops packaging. The bundled .NET runtime retains its supplied full license/third-party notices independently.

tools/upstream.lock.json contains references to separately downloaded Linux fixtures, not bundled etcd, PostgreSQL, libpq, libnuma or liburing binaries. etcd is Apache-2.0. PostgreSQL/libpq use PostgreSQL licensing; Ubuntu runtime libraries retain their package copyright/license files under the extracted root's usr/share/doc. Preserve those files when handling the fetched packages. Official HTTPS digest metadata was used to freeze the referenced bytes; this is not an assertion of independent vendor-signature verification.

Public architecture references: [etcd v3 gateway](https://etcd.io/docs/v3.7/dev-guide/api_grpc_gateway/), [platform tiers](https://etcd.io/docs/v3.7/op-guide/supported-platform/), [fencing explanation](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html), [PostgreSQL transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html), [Npgsql 10 client](https://www.npgsql.org/doc/release-notes/10.0.html). The fencing pattern and existing consensus are not claimed as new inventions.

The provenance/packaging approach follows the author's established public synthetic portfolio delivery process; no private signing key or private project implementation is distributed.

Go Vulnerability Database data in the tooling proof streams is licensed
CC-BY-4.0, separately from the module/compiler/auditor notice graph. Source:
https://vuln.go.dev/ and https://github.com/golang/vulndb/tree/master/data.
The public sealed tooling ZIPs retain the complete original Go vulnerability
database LICENSE and an attribution/formatting/analysis note under
producer-proofs/vulndb-*. No upstream endorsement is claimed.

The copied etcd audit records in vendor/etcd-admission also retain Go Vulnerability Database CC-BY-4.0 data. Their complete original license and source/selection/analysis attribution are bundled as vendor/notices/GO-VULNDB-LICENSE.txt and vendor/notices/VULNDB-ATTRIBUTION.txt. In the separate serving ZIP these same notices live under notices/. The original seven proof files and admitted image remain byte-identical; adding these disclosures performs no new audit or security certification.


CI build-tool boundary: corrective Windows verification may privately stage the exact official .NET SDK 10.0.404 ZIP. Its full original SDK license and third-party notice files are retained and byte-checked in that private SDK tree before the first SDK target. The SDK is not installed globally, bundled with this application, cached, uploaded or publicly redistributed. Application Core runtime notices remain separately included under vendor/notices. Archive SHA identity is not a code-signature or general security certification.

Proposed Linux CI build-tool boundary: the preview.5 draft may privately stage
the exact official .NET SDK10.0.404 Linux tar.gz only after a separate execution
gate. All ten full original SDK license/third-party notice files must be
byte-verified before SDK target creation and retained in the private SDK tree.
The source lock catalogs identities, not redistributed SDK notice substitutes.
The SDK is not installed globally, bundled with the application, cached, uploaded
or publicly redistributed. Application runtime15 notices and their byte maps
remain unchanged. Raw digest identity is not a vendor signature or security claim.
