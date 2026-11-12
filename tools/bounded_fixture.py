"""Finite Linux fixture/tool execution; no global limits, installs or cleanup.

Callers must already own a delegated cgroup with aggregate kernel hard limits.
A stopped child is checked inside that group before its first executable starts.
"""
import gzip
import hashlib
import json
import os
import posixpath
import re
import selectors
import signal
import stat
import tarfile
import time
from pathlib import Path

MEMORY_MAX = 4294967296
DOWNLOAD_MAX = 67108864
WORKSPACE_MAX = 4294967296
LOG_MAX = 134217728


def require(value, message):
    if not value:
        raise ValueError(message)


def strict_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "DUPLICATE_JSON_KEY")
            out[key] = value
        return out
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: require(False, "JSON_CONSTANT"))


def sha256(path, cap=WORKSPACE_MAX):
    digest = hashlib.sha256()
    total = 0
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(65536), b""):
            total += len(data)
            require(total <= cap, "ACTUAL_FILE_BYTE_CAP")
            digest.update(data)
    return digest.hexdigest()


def canonical(path, exists=True):
    path = Path(path)
    require(path.is_absolute() and ".." not in path.parts, "ABSOLUTE_CANONICAL_PATH")
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            info = item.lstat()
            require(not stat.S_ISLNK(info.st_mode)
                    and not getattr(info, "st_file_attributes", 0) & 0x400,
                    "PATH_REDIRECT")
    require(not exists or path.exists(), "PATH_MISSING")
    require(path == path.resolve(strict=exists), "PATH_ALIAS")
    return path


def fresh_directory(path, owned_root):
    path = canonical(path, exists=False)
    root = canonical(owned_root)
    require(path != root and path.is_relative_to(root), "OWNED_OUTPUT_CONTAINMENT")
    path.mkdir(exist_ok=False)
    return path


def kernel_limits(pid="self"):
    require(os.name == "posix" and os.getuid() != 0, "NONROOT_LINUX_REQUIRED")
    membership = Path(f"/proc/{pid}/cgroup").read_text()
    names = [x[3:] for x in membership.splitlines() if x.startswith("0::")]
    require(len(names) == 1 and names[0] != "/", "DELEGATED_CGROUP_REQUIRED")
    group = Path("/sys/fs/cgroup") / names[0].lstrip("/")
    values = {n: (group/n).read_text().strip()
              for n in ("memory.max", "memory.swap.max", "pids.max", "cpu.max")}
    require(values["memory.max"].isdigit()
            and 0 < int(values["memory.max"]) <= MEMORY_MAX, "AGGREGATE_MEMORY_HOLD")
    require(values["memory.swap.max"] == "0", "SWAP_HOLD")
    require(values["pids.max"].isdigit()
            and 0 < int(values["pids.max"]) <= 64, "AGGREGATE_TASK_HOLD")
    quota, period = values["cpu.max"].split()
    require(quota.isdigit() and 0 < int(quota) <= 2*int(period), "AGGREGATE_CPU_HOLD")
    return {"membership": membership, "group": str(group), "kernel": values}


def clean_go_environment(go, workspace, *, workspace_file="off", target="linux"):
    """Construct the full environment; inherited Go/auth/proxy settings never pass."""
    go = canonical(go)
    workspace = canonical(workspace)
    require(target in ("windows", "linux"), "FINITE_TARGET")
    env = {"PATH": str(go/"bin") + ":/usr/bin:/bin", "LANG": "C.UTF-8",
           "HOME": str(workspace/"home"), "TMPDIR": str(workspace/"tmp"),
           "XDG_CONFIG_HOME": str(workspace/"home/.config"),
           "GOROOT": str(go), "GOPATH": str(workspace/"gopath"),
           "GOCACHE": str(workspace/"cache"), "GOTMPDIR": str(workspace/"tmp"),
           "GOTOOLCHAIN": "local", "GOENV": "off", "GOTELEMETRY": "off",
           "GOWORK": workspace_file, "CGO_ENABLED": "0", "GOOS": target,
           "GOARCH": "amd64", "GOAMD64": "v1", "GOMAXPROCS": "2",
           "GOPROXY": "off", "GOSUMDB": "sum.golang.org", "GOAUTH": "off",
           "GOVCS": "*:off"}
    for name in ("home", "tmp", "gopath", "cache"):
        canonical(workspace/name, exists=False).mkdir(exist_ok=False)
    # The x/telemetry library reads a mode file, rather than GOTELEMETRY.
    # Keep it off in this fresh private HOME before any analyzer main/init runs.
    telemetry = workspace/"home/.config/go/telemetry"
    telemetry.mkdir(mode=0o700, parents=True, exist_ok=False)
    with (telemetry/"mode").open("x", encoding="utf-8", newline="\n") as mode:
        mode.write("off\n")
    os.chmod(telemetry/"mode", 0o600)
    return env


def _kill_owned_group(pid):
    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    time.sleep(.2)
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def workspace_limit(roots):
    total = 0
    for owned_root in roots:
        for file in owned_root.rglob("*"):
            info = file.lstat()
            if stat.S_ISREG(info.st_mode):
                total += info.st_size
            require(total <= WORKSPACE_MAX, "NEW_WORKSPACE_CAP")
    return total


def run(argv, *, cwd, env, evidence, seconds, disk_root, pass_fds=(), other_disk_roots=()):
    """The calling phase owns the cgroup and releases it after durable teardown."""
    require(type(seconds) is int and 0 < seconds <= 1200, "FINITE_WALL")
    require(argv and all(isinstance(x, str) and "\0" not in x for x in argv),
            "FINITE_ARGV")
    cwd = canonical(cwd)
    evidence = canonical(evidence)
    disk_root = canonical(disk_root)
    disk_roots = [disk_root, *(canonical(p) for p in other_disk_roots)]
    require(not pass_fds or all(type(x) is int and x >= 0 for x in pass_fds),
            "HELD_FDS")
    caps = kernel_limits()
    out = (evidence/"stdout.log").open("xb")
    err = (evidence/"stderr.log").open("xb")
    started = time.monotonic()
    pipes = [os.pipe(), os.pipe()]
    remaining_fds = {fd for pair in pipes for fd in pair}
    selection = selectors.DefaultSelector()
    logged = 0
    pid = None
    status = "HOLD"
    exitcode = None
    receipt = {"argv": argv, "cwd": str(cwd), "secondsMax": seconds,
               "parentLimits": caps, "downloadedCodeTrust": "CALLER_GATE_REQUIRED"}
    try:
        pid = os.fork()
        if pid == 0:
            try:
                os.setsid()
                os.kill(os.getpid(), signal.SIGSTOP)
                os.chdir(cwd)
                os.dup2(pipes[0][1], 1)
                os.dup2(pipes[1][1], 2)
                for pair in pipes:
                    for descriptor in pair:
                        os.close(descriptor)
                for descriptor in pass_fds:
                    os.set_inheritable(descriptor, True)
                os.execve(argv[0], argv, env)
            except BaseException:
                os._exit(126)
        for pair, destination in zip(pipes, (out, err)):
            os.close(pair[1])
            remaining_fds.remove(pair[1])
            os.set_blocking(pair[0], False)
            selection.register(pair[0], selectors.EVENT_READ, destination)
        stopped, wait_status = os.waitpid(pid, os.WUNTRACED)
        require(stopped == pid and os.WIFSTOPPED(wait_status), "CHILD_STOP_REQUIRED")
        child_caps = kernel_limits(pid)
        require(child_caps == caps, "CHILD_INHERITED_LIMIT_MEMBERSHIP")
        receipt.update(pid=pid,
                       processStartIdentity=Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[19],
                       childBeforeExec=child_caps)
        os.kill(pid, signal.SIGCONT)
        last_disk_check = 0.0
        ended = None
        while True:
            ended = os.waitid(os.P_PID, pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            if ended is not None:
                exitcode = ended.si_status if ended.si_code == os.CLD_EXITED else -ended.si_status
                status = "PASS" if exitcode == 0 else "FAILED_CHILD"
            for key, _ in selection.select(.05):
                data = os.read(key.fd, 65536)
                if not data:
                    selection.unregister(key.fd)
                    os.close(key.fd)
                    remaining_fds.remove(key.fd)
                else:
                    require(logged + len(data) <= LOG_MAX, "CHILD_LOG_CAP")
                    key.data.write(data)
                    logged += len(data)
            if ended is not None and not selection.get_map():
                workspace_limit(disk_roots)  # Include fast exit immediately after a disk write.
                break
            require(time.monotonic()-started <= seconds, "CHILD_WALL_CAP")
            if time.monotonic()-last_disk_check >= 1:
                workspace_limit(disk_roots)
                last_disk_check = time.monotonic()
    except Exception as error:
        status = "HOLD_" + str(error)[:180]
        raise
    finally:
        if pid is not None:
            _kill_owned_group(pid)
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass
        selection.close()
        for descriptor in remaining_fds:
            try:
                os.close(descriptor)
            except OSError:
                pass
        out.close()
        err.close()
        group = Path(caps["group"])
        receipt.update(status=status, exitCode=exitcode,
                       seconds=round(time.monotonic()-started, 3), savedLogBytes=logged,
                       memoryPeak=(group/"memory.peak").read_text().strip(),
                       memoryEvents=(group/"memory.events").read_text(),
                       ownProcessGroupTermination="TERM_THEN_KILL_OWN_GROUP_ONLY",
                       phaseTeardown="CALLER_MUST_VERIFY_CGROUP_TERMINAL_BEFORE_LEASE_RELEASE")
        (evidence/"process.json").write_text(json.dumps(receipt, indent=2)+"\n")
    require(exitcode == 0, "BOUNDED_CHILD_FAILED")
    return receipt


def archive_inventory(path, prefix):
    """Complete stream before materialization; return all regular/link identities."""
    require(re.fullmatch(r"[A-Za-z0-9._-]+", prefix) is not None, "ARCHIVE_PREFIX")
    rows = []
    seen = set()
    expanded = 0
    logical = 0
    class Limited:
        def __init__(self, stream):
            self.stream = stream
        def read(self, n):
            nonlocal expanded
            require(0 <= n <= 65536, "BOUNDED_DECOMPRESS_READ")
            data = self.stream.read(n)
            expanded += len(data)
            require(expanded <= 1073741824, "DECOMPRESSED_CAP")
            return data
    with Path(path).open("rb") as source, gzip.GzipFile(fileobj=source) as gz:
        limited = Limited(gz)
        with tarfile.open(fileobj=limited, mode="r|") as archive:
            for member in archive:
                name = member.name.rstrip("/")
                require(name == prefix or name.startswith(prefix+"/"), "MEMBER_PREFIX")
                require(not any(ord(c) < 32 or ord(c) == 127 or c in '\\:<>"|?*'
                                for c in name), "MEMBER_CHARACTER")
                require(all(x not in ("", ".", "..") for x in name.split("/")), "MEMBER_COMPONENT")
                require(name.casefold() not in seen and len(rows) < 30000, "MEMBER_COLLISION")
                require(not member.mode & 0o7000 and 0 <= member.size <= DOWNLOAD_MAX,
                        "MEMBER_MODE_SIZE")
                seen.add(name.casefold())
                row = {"path": name, "mode": member.mode, "bytes": member.size}
                if member.isdir():
                    require(member.size == 0, "DIRECTORY_BODY")
                    row["type"] = "directory"
                elif member.isfile():
                    row["type"] = "file"
                    logical += member.size
                    require(logical <= 1073741824, "LOGICAL_CAP")
                    digest = hashlib.sha256()
                    actual = 0
                    stream = archive.extractfile(member)
                    for data in iter(lambda: stream.read(65536), b""):
                        actual += len(data)
                        require(actual <= member.size, "MEMBER_FRAME")
                        digest.update(data)
                    require(actual == member.size, "MEMBER_TRUNCATED")
                    row["sha256"] = digest.hexdigest()
                elif member.issym():
                    require(member.size == 0 and member.linkname
                            and not member.linkname.startswith("/")
                            and not any(ord(c) < 32 or c in "\\:" for c in member.linkname),
                            "LINK_TARGET")
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(name),
                                                              member.linkname))
                    require(target == prefix or target.startswith(prefix+"/"), "LINK_ESCAPE")
                    row.update(type="symlink", target=member.linkname, resolvedTarget=target)
                else:
                    raise ValueError("UNSUPPORTED_MEMBER_TYPE")
                rows.append(row)
        while limited.read(65536):
            pass
    byname = {x["path"]: x for x in rows}
    for row in rows:
        for parent in Path(row["path"]).parents:
            require(byname.get(parent.as_posix(), {}).get("type") != "symlink", "PARENT_LINK")
        if row["type"] == "symlink":
            target = row["resolvedTarget"]
            visited = {row["path"]}
            for _ in range(32):
                require(target not in visited and target in byname, "LINK_CYCLE_OR_MISSING")
                visited.add(target)
                referent = byname[target]
                if referent["type"] != "symlink":
                    break
                target = referent["resolvedTarget"]
            else:
                raise ValueError("LINK_DEPTH")
    return rows
