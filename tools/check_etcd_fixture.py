"""Admit the exact maintainer-built fixture before every first/direct/restart spawn.

The source-reviewed lock is independent of PREPARED.json and candidate receipts.
An unknown lock, stale upstream fixture, missing proof or mismatched bytes fails.
"""
import argparse
import contextlib
import hashlib
import json
import os
import re
import stat
from pathlib import Path, PurePosixPath

from bounded_fixture import canonical, require, sha256, strict_json

REQUIRED_PROOFS = {"admission/source-audit.jsonl", "admission/binary-audit.jsonl",
                   "admission/module-graph.json", "admission/licenses.json",
                   "admission/buildinfo.json", "admission/reproducibility.json",
                   "admission/advisory-snapshot.json"}
LOCK_SHA256 = "47fbc300bda7c5350c771bd7f9ee46ffc1d086e8d4d36a7e11d18ad545fdc30c"  # Independent same-source/image and frozen-proof admission.
LOCK = Path(__file__).with_name("etcd-build.lock.json")
FIELDS = {"schema", "sourceCommit", "goVersion", "target", "binarySha256",
          "binaryBytes", "proofs"}


def reference():
    require(isinstance(LOCK_SHA256, str) and len(LOCK_SHA256) == 64,
            "HOLD_ETCD_REFERENCE_NOT_ADMITTED")
    raw = canonical(LOCK).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == LOCK_SHA256, "ETCD_LOCK_IDENTITY")
    lock = strict_json(raw)
    require(type(lock["schema"]) is int and lock["schema"] == 1 and lock["status"] == "ADMITTED_MAINTAINER_BUILD",
            "ETCD_REFERENCE_STATUS")
    require(lock["sourceCommit"] == "0a173d0410a96d01091b484daae81365bbcde57e"
            and lock["goVersion"] == "go1.26.11" and lock["target"] == "linux/amd64",
            "ETCD_REFERENCE_SOURCE_COMPILER")
    require(type(lock["binaryBytes"]) is int and 0 < lock["binaryBytes"] <= 67108864,
            "ETCD_REFERENCE_SIZE")
    require(type(lock["binarySha256"]) is str and re.fullmatch("[0-9a-f]{64}", lock["binarySha256"])
            and type(lock["proofs"]) is dict and set(lock["proofs"]) == REQUIRED_PROOFS,
            "ETCD_REFERENCE_COMPLETE")
    return lock


def identity(fixtures, lock):
    """Internal comparison seam uses independent literal references in negatives."""
    root = canonical(fixtures)
    file = canonical(root/"etcd-source-go1.26.11"/"etcd")
    require(file.is_relative_to(root), "ETCD_BINARY_CONTAINMENT")
    manifest = canonical(root/"ETCD-BUILD.json")
    raw = manifest.read_bytes()
    require(len(raw) <= 2097152, "ETCD_MANIFEST_CAP")
    supplied = strict_json(raw)
    require(set(supplied) == FIELDS, "ETCD_MANIFEST_FIELDS")
    expected = {key: lock[key] for key in FIELDS}
    require(all(type(supplied[key]) is type(expected[key]) for key in FIELDS),
            "ETCD_MANIFEST_FIELD_TYPES")
    require(supplied == expected, "ETCD_INDEPENDENT_REFERENCE_MISMATCH")
    for name, digest in lock["proofs"].items():
        require(type(name) is str and type(digest) is str and re.fullmatch("[0-9a-f]{64}", digest),
                "ETCD_PROOF_REFERENCE")
        part = PurePosixPath(name)
        require(not part.is_absolute() and part.parts and ".." not in part.parts
                and part.as_posix() == name and not any(ord(c) < 32 or c in "\\:" for c in name), "ETCD_PROOF_PATH")
        proof = canonical(root.joinpath(*part.parts))
        require(proof.is_relative_to(root) and sha256(proof, 134217728) == digest,
                "ETCD_FROZEN_PROOF_MISMATCH")
    return root, file, supplied


@contextlib.contextmanager
def admitted_etcd(fixtures):
    """Copy hash-checked bytes to a kernel-sealed executable, defeating path swaps.

    The local binary is never executed by pathname after verification. A sealed
    memfd is a transient held identity, not a second artifact or trust reference.
    """
    require(os.name == "posix" and hasattr(os, "memfd_create"),
            "HOLD_LINUX_SEALED_EXECUTION_REQUIRED")
    import fcntl
    lock = reference()
    root, path, info = identity(fixtures, lock)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    sealed = None
    try:
        before = os.fstat(descriptor)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                and before.st_size == lock["binaryBytes"], "ETCD_REGULAR_UNALIASED_SIZE")
        sealed = os.memfd_create("ownership-etcd-admitted", os.MFD_ALLOW_SEALING)
        digest = hashlib.sha256()
        total = 0
        while True:
            data = os.read(descriptor, 65536)
            if not data:
                break
            total += len(data)
            require(total <= lock["binaryBytes"], "ETCD_BINARY_STREAM_CAP")
            digest.update(data)
            offset = 0
            while offset < len(data):
                written = os.write(sealed, data[offset:])
                require(written > 0, "ETCD_SEALED_COPY")
                offset += written
        after = os.fstat(descriptor)
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns,
                 before.st_ctime_ns) ==
                (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns,
                 after.st_ctime_ns), "ETCD_BINARY_CHANGED_DURING_ADMISSION")
        require(total == lock["binaryBytes"] and digest.hexdigest() == lock["binarySha256"],
                "ETCD_ACTUAL_BINARY_IDENTITY")
        os.fchmod(sealed, 0o500)
        seals = (fcntl.F_SEAL_WRITE | fcntl.F_SEAL_SHRINK |
                 fcntl.F_SEAL_GROW | fcntl.F_SEAL_SEAL)
        fcntl.fcntl(sealed, fcntl.F_ADD_SEALS, seals)
        require(fcntl.fcntl(sealed, fcntl.F_GET_SEALS) & seals == seals,
                "HOLD_ETCD_KERNEL_SEAL")
        yield {"executable": f"/proc/self/fd/{sealed}", "pass_fds": (sealed,),
               "identity": info, "fixtureRoot": str(root)}
    finally:
        os.close(descriptor)
        if sealed is not None:
            os.close(sealed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", required=True, type=Path)
    args = parser.parse_args()
    with admitted_etcd(args.fixtures) as admitted:
        print(json.dumps({"status": "EXACT_ETCD_ADMITTED_NOT_EXECUTED",
                          "identity": admitted["identity"]}))


if __name__ == "__main__":
    main()
