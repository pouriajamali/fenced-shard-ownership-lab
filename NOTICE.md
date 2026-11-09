# Attribution and distribution boundaries

Original lab source is copyright 2026 Pouria Jamali, MIT. No private/shared system source, customer data or account configuration is included.

The archive's DEPENDENCIES.json and SBOM.spdx.json describe the actual resolved/shipped managed package graph and bundled .NET runtime; licenses/ retains supplied license/third-party notices. Npgsql uses the PostgreSQL license. OpenTelemetry and other dependencies retain their own declared licenses. The original MIT license does not relabel those components.

tools/upstream.lock.json contains references to separately downloaded Linux fixtures, not bundled etcd, PostgreSQL, libpq, libnuma or liburing binaries. etcd is Apache-2.0. PostgreSQL/libpq use PostgreSQL licensing; Ubuntu runtime libraries retain their package copyright/license files under the extracted root's usr/share/doc. Preserve those files when handling the fetched packages. Official HTTPS digest metadata was used to freeze the referenced bytes; this is not an assertion of independent vendor-signature verification.

Public architecture references: [etcd v3 gateway](https://etcd.io/docs/v3.7/dev-guide/api_grpc_gateway/), [platform tiers](https://etcd.io/docs/v3.7/op-guide/supported-platform/), [fencing explanation](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html), [PostgreSQL transactions](https://www.postgresql.org/docs/18/tutorial-transactions.html), [Npgsql 10 client](https://www.npgsql.org/doc/release-notes/10.0.html). The fencing pattern and existing consensus are not claimed as new inventions.

The provenance/packaging approach follows the author's established public synthetic portfolio delivery process; no private signing key or private project implementation is distributed.
