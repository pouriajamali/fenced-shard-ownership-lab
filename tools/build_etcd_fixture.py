"""Same-commit etcd build primitives. No target executable runs here.

Public admission stays closed until the independent source-held build lock and
all required source/binary/current-advisory proofs are populated and reviewed.
"""
import argparse
import json
import os
import stat
import tarfile
from pathlib import Path

from bounded_fixture import (archive_inventory, canonical, clean_go_environment,
                             fresh_directory, kernel_limits, require, run, sha256)
from check_etcd_fixture import reference

SOURCE_COMMIT = "0a173d0410a96d01091b484daae81365bbcde57e"
SOURCE_SHA256 = "f7628ecdb67353acdc708a42c4fb9e1267b4a1efed68ec1da83514406a598b60"
SDK_SHA256 = "9849f4e04ee35303714e34fbc3ac8ab44ea3e448a95aa182f91e3b9b79c710ec"


def verify_tree(root, rows, prefix):
    root = canonical(root)
    expected = {}
    root_row = next(r for r in rows if r["path"] == prefix)
    require(stat.S_IMODE(root.stat().st_mode) == root_row["mode"], "SOURCE_ROOT_MODE")
    for row in rows:
        require(row["path"] == prefix or row["path"].startswith(prefix+"/"),
                "SOURCE_MEMBER_PREFIX")
        relative = row["path"][len(prefix):].lstrip("/")
        if not relative:
            continue
        expected[relative] = row
        file = root/relative
        info = file.lstat()
        if row["type"] == "symlink":
            require(stat.S_ISLNK(info.st_mode) and os.readlink(file) == row["target"],
                    "SOURCE_SYMLINK_IDENTITY")
        elif row["type"] == "directory":
            canonical(file)
            require(stat.S_ISDIR(info.st_mode), "SOURCE_DIRECTORY_IDENTITY")
        else:
            canonical(file)
            require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                    and info.st_size == row["bytes"]
                    and sha256(file, 67108864) == row["sha256"],
                    "SOURCE_FILE_IDENTITY")
        if row["type"] != "symlink":
            require(stat.S_IMODE(info.st_mode) == row["mode"], "SOURCE_ACTUAL_MODE")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*")}
    require(actual == set(expected), "SOURCE_COMPLETE_MEMBER_SET")
    return {"members": len(expected), "sourceCommit": SOURCE_COMMIT}


def materialize(archive, destination, owned_root, prefix, expected_sha):
    """Full bounded inventory and digest precede every materialized member."""
    kernel_limits()
    archive = canonical(archive)
    require(sha256(archive, 67108864) == expected_sha, "FROZEN_RAW_ARCHIVE")
    rows = archive_inventory(archive, prefix)
    by_name = {row["path"]: row for row in rows}
    destination = fresh_directory(destination, owned_root)
    links = []
    with tarfile.open(archive, "r:gz") as source:
        for member in source:
            name = member.name.rstrip("/")
            relative = name[len(prefix):].lstrip("/")
            if not relative:
                continue
            target = destination/relative
            row = by_name[name]
            if row["type"] == "directory":
                target.mkdir(exist_ok=False)
                os.chmod(target, row["mode"])
            elif row["type"] == "symlink":
                links.append((target, row))
            else:
                stream = source.extractfile(member)
                descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                                     os.O_NOFOLLOW, row["mode"])
                with os.fdopen(descriptor, "wb") as output:
                    count = 0
                    for block in iter(lambda: stream.read(65536), b""):
                        count += len(block)
                        require(count <= row["bytes"], "MATERIALIZED_STREAM_CAP")
                        output.write(block)
                os.chmod(target, row["mode"])
    for target, row in links:
        target.symlink_to(row["target"])
    os.chmod(destination, by_name[prefix]["mode"])
    verify_tree(destination, rows, prefix)
    return rows


def build_once(*, source, source_rows, compiler, compiler_members, module_cache,
               work, owned_root, number, other_disk_roots=()):
    """Internal first-build primitive; output is never admitted by this function."""
    require(number in (1, 2), "EXACT_TWO_BUILD_NUMBER")
    kernel_limits()
    source = canonical(source)
    compiler = canonical(compiler)
    module_cache = canonical(module_cache)
    require((source/"go.work").is_file(), "EXACT_UPSTREAM_WORKSPACE_REQUIRED")
    verify_tree(source, source_rows, "etcd-"+SOURCE_COMMIT)
    for row in compiler_members:
        file = canonical(compiler.parent/row["path"])
        info = file.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
                and sha256(file) == row["sha256"]
                and info.st_size == row["bytes"]
                and stat.S_IMODE(info.st_mode) == int(row["mode"], 8),
                "ACTUAL_ADMITTED_COMPILER_INPUT")
    work = fresh_directory(work, owned_root)
    environment = work/"environment"
    environment.mkdir()
    env = clean_go_environment(compiler, environment,
                               workspace_file=str(source/"go.work"))
    env["GOMODCACHE"] = str(module_cache)
    output = work/"etcd"
    evidence = work/"process"
    evidence.mkdir()
    argv = [str(compiler/"bin/go"), "build", "-mod=readonly", "-p=1", "-trimpath",
            "-buildvcs=false", "-installsuffix=cgo",
            "-ldflags=-X=go.etcd.io/etcd/api/v3/version.GitSHA=0a173d0",
            "-o="+str(output), "."]
    process = run(argv, cwd=canonical(source/"server"), env=env, evidence=evidence,
                  seconds=1200, disk_root=owned_root,
                  other_disk_roots=other_disk_roots)
    verify_tree(source, source_rows, "etcd-"+SOURCE_COMMIT)
    record = {"status": "BUILT_NOT_ADMITTED_NOT_EXECUTED", "number": number,
              "sourceCommit": SOURCE_COMMIT, "binarySha256": sha256(output),
              "binaryBytes": output.stat().st_size, "argv": argv,
              "process": process, "fixtureAdmitted": False}
    (work/"receipt.json").write_text(json.dumps(record, indent=2)+"\n")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archives", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--work", type=Path)
    args = parser.parse_args()
    lock = reference()  # Independent source-held admission precedes work or SDK execution.
    from etcd_inputs import reproduce
    out = args.out.absolute()
    work = args.work.absolute() if args.work else out.parent/(out.name+"-rebuild")
    result = reproduce(canonical(args.archives.absolute()), out, work, lock)
    print(json.dumps({"status": "REPRODUCED_EXACT_ADMITTED_ETCD_NOT_EXECUTED", "binarySha256": result["binarySha256"]}))


if __name__ == "__main__":
    main()
