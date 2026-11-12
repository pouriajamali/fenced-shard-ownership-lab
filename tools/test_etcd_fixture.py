"""Synthetic contract negatives for fixture admission; never execute fake binaries.

This suite does not establish real compiler/module/fixture trust or live faults.
Run the approved Linux suite normally, with -O and with PYTHONOPTIMIZE=1.
"""
import argparse
import copy
import hashlib
import io
import json
import os
import sys
import tarfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bounded_fixture as bounded
import check_etcd_fixture as checker

WORK = None
COUNTER = 0
REJECTIONS = []
PAYLOAD = b"synthetic fixture bytes; never executed\n"
PROOF = b'{"syntheticContractControl":true,"noRealSecurityClaim":true}\n'
PAYLOAD_SHA = "8c303e926a8b3d5525b87253b07f7b956550b0dc76f160ef43588b85d431dc82"
PROOF_SHA = "44b5d49450052c1229f062e2e040d5b2c5287937774adb5bf2c18de677afc5a4"
LOCK = {
    "schema": 1, "status": "ADMITTED_MAINTAINER_BUILD",
    "sourceCommit": "0a173d0410a96d01091b484daae81365bbcde57e",
    "goVersion": "go1.26.11", "target": "linux/amd64",
    "binarySha256": PAYLOAD_SHA, "binaryBytes": len(PAYLOAD),
    "proofs": {name: PROOF_SHA for name in sorted({"admission/source-audit.jsonl", "admission/binary-audit.jsonl", "admission/module-graph.json", "admission/licenses.json", "admission/buildinfo.json", "admission/reproducibility.json", "admission/advisory-snapshot.json"})},
}
LOCK_RAW = (json.dumps(LOCK, sort_keys=True)+"\n").encode()
LOCK_SHA = "f05ce1274c7c3af1d71530cfb50fb4559fd88eef77e01e4507420b0c519d4813"


class AdmissionVectors(unittest.TestCase):
    def setUp(self):
        global COUNTER
        COUNTER += 1
        self.root = WORK/(str(COUNTER).zfill(3)+"-"+self._testMethodName)
        self.root.mkdir(exist_ok=False)

    def reject(self, label, action, errors=(ValueError, OSError, tarfile.TarError)):
        with self.assertRaises(errors):
            action()
        REJECTIONS.append(label)

    def fixture(self):
        root = self.root/"fixture"
        (root/"etcd-source-go1.26.11").mkdir(parents=True)
        (root/"etcd-source-go1.26.11/etcd").write_bytes(PAYLOAD)
        (root/"admission").mkdir()
        for name in LOCK["proofs"]:
            (root/name).write_bytes(PROOF)
        manifest = {key: copy.deepcopy(LOCK[key]) for key in checker.FIELDS}
        (root/"ETCD-BUILD.json").write_text(json.dumps(manifest))
        return root, manifest

    def archive(self, entries):
        path = self.root/("archive-"+str(len(list(self.root.glob("archive-*"))))+".tar.gz")
        with tarfile.open(path, "w:gz") as archive:
            for name, kind, target in entries:
                entry = tarfile.TarInfo(name)
                entry.mode = 0o644
                if kind == "file":
                    entry.size = 1
                    archive.addfile(entry, io.BytesIO(b"x"))
                else:
                    entry.type = {"symlink": tarfile.SYMTYPE, "hardlink": tarfile.LNKTYPE,
                                  "fifo": tarfile.FIFOTYPE, "device": tarfile.CHRTYPE}[kind]
                    entry.linkname = target
                    archive.addfile(entry)
        return path

    def test_independent_literal_control(self):
        self.assertEqual(hashlib.sha256(PAYLOAD).hexdigest(), PAYLOAD_SHA)
        self.assertEqual(hashlib.sha256(PROOF).hexdigest(), PROOF_SHA)
        self.assertEqual(hashlib.sha256(LOCK_RAW).hexdigest(), LOCK_SHA)
        root, manifest = self.fixture()
        _, file, actual = checker.identity(root, LOCK)
        self.assertEqual(actual, manifest)
        self.assertEqual(file.read_bytes(), PAYLOAD)
        archive = self.archive([(f"root/{n}", "file", "") for n in "abcd"])
        self.assertEqual(len(bounded.archive_inventory(archive, "root")), 4)

    def test_strict_json_framing(self):
        for label, raw in [
            ("duplicate-first", '{"schema":1,"schema":1}'),
            ("duplicate-last", '{"a":1,"b":2,"b":2}'),
            ("trailing-document", '{}{}'), ("nan", '{"v":NaN}'),
            ("infinity", '{"v":Infinity}'),
        ]:
            self.reject(label, lambda raw=raw: bounded.strict_json(raw))
        self.assertEqual(bounded.strict_json('{"v":"literal"}'), {"v": "literal"})

    def test_manifest_fields_types_and_independent_reference(self):
        root, original = self.fixture()
        for key in sorted(checker.FIELDS):
            bad = copy.deepcopy(original)
            del bad[key]
            (root/"ETCD-BUILD.json").write_text(json.dumps(bad))
            self.reject("missing-"+key, lambda: checker.identity(root, LOCK))
        for key, value in [("schema", True), ("schema", 1.0),
                           ("binaryBytes", True), ("binaryBytes", float(len(PAYLOAD))),
                           ("goVersion", "go1.26.10"), ("target", "windows/amd64"),
                           ("sourceCommit", "0"*40), ("binarySha256", "z"*64)]:
            bad = copy.deepcopy(original)
            bad[key] = value
            (root/"ETCD-BUILD.json").write_text(json.dumps(bad))
            self.reject("forged-"+key+"-"+str(value), lambda: checker.identity(root, LOCK))
        bad = copy.deepcopy(original)
        bad["status"] = "PASS"
        (root/"ETCD-BUILD.json").write_text(json.dumps(bad))
        self.reject("candidate-pass-not-admission", lambda: checker.identity(root, LOCK))

    def test_candidate_matching_its_own_forged_proofs_is_rejected(self):
        root, manifest = self.fixture()
        proof = root/"admission/module-graph.json"
        proof.write_bytes(b'{"attackerChosenModule":"new-version","status":"PASS"}')
        manifest["proofs"]["admission/module-graph.json"] = hashlib.sha256(proof.read_bytes()).hexdigest()
        (root/"ETCD-BUILD.json").write_text(json.dumps(manifest))
        self.reject("matching-own-graph-not-reference", lambda: checker.identity(root, LOCK))

    def test_missing_or_changed_license_advisory_reproducibility_proofs(self):
        for name in ("licenses.json", "source-audit.jsonl", "binary-audit.jsonl",
                     "reproducibility.json", "advisory-snapshot.json"):
            root, _ = self.fixture() if not (self.root/"fixture").exists() else (self.root/"fixture", None)
            proof = root/"admission"/name
            before = proof.read_bytes()
            proof.write_bytes(b'{"status":"UNKNOWN","symbolsAbsent":true,"loopbackOnly":true}')
            self.reject("proof-unknown-"+name, lambda: checker.identity(root, LOCK))
            proof.write_bytes(before)
        proof = root/"admission/licenses.json"
        proof.rename(root/"admission/retained-license.json")
        self.reject("missing-full-license-proof", lambda: checker.identity(root, LOCK))

    def test_lock_is_independent_of_candidate_supplied_lock(self):
        root, manifest = self.fixture()
        path = self.root/"locked-reference.json"
        path.write_bytes(LOCK_RAW)
        with mock.patch.object(checker, "LOCK", path), mock.patch.object(checker, "LOCK_SHA256", LOCK_SHA):
            self.assertEqual(checker.reference()["binarySha256"], PAYLOAD_SHA)
            bad = copy.deepcopy(LOCK)
            bad["goVersion"] = "go1.26.10"
            path.write_text(json.dumps(bad, sort_keys=True)+"\n")
            manifest["goVersion"] = bad["goVersion"]
            (root/"ETCD-BUILD.json").write_text(json.dumps(manifest))
            self.reject("matching-forged-lock-and-manifest", checker.reference)
        with mock.patch.object(checker, "LOCK_SHA256", None):
            self.reject("draft-reference-hold", checker.reference)

    def test_forbidden_archive_paths_at_every_position(self):
        badnames = ["../escape", "/root/absolute", "C:/drive", "root/../escape",
                    "root/a\\b", "root/a\nb", "root/a\x01b", "root//empty"]
        base = [(f"root/{name}", "file", "") for name in "abcd"]
        for position in range(4):
            for name in badnames:
                items = list(base)
                items[position] = (name, "file", "")
                archive = self.archive(items)
                self.reject(f"path-{position}-{repr(name)}",
                            lambda archive=archive: bounded.archive_inventory(archive, "root"))
            for name in ("root/b" if position == 0 else "root/a",
                         "root/B" if position == 0 else "root/A"):
                items = list(base)
                items[position] = (name, "file", "")
                archive = self.archive(items)
                self.reject(f"alias-{position}-{name}",
                            lambda archive=archive: bounded.archive_inventory(archive, "root"))

    def test_escaping_links_and_special_nodes_at_every_position(self):
        base = [(f"root/{name}", "file", "") for name in "abcd"]
        for position in range(4):
            for kind in ("symlink", "hardlink", "fifo", "device"):
                items = list(base)
                items[position] = (f"root/link{position}", kind, "../../outside")
                archive = self.archive(items)
                self.reject(f"node-{position}-{kind}",
                            lambda archive=archive: bounded.archive_inventory(archive, "root"))
        for label, items in [
            ("parent-link-write", [("root/a", "symlink", "b"), ("root/b", "file", ""),
                                   ("root/a/payload", "file", ""), ("root/d", "file", "")]),
            ("link-cycle", [("root/a", "symlink", "b"), ("root/b", "symlink", "a"),
                            ("root/c", "file", ""), ("root/d", "file", "")]),
        ]:
            archive = self.archive(items)
            self.reject(label, lambda: bounded.archive_inventory(archive, "root"))

    def test_archive_truncation_and_actual_stream_cap(self):
        archive = self.archive([(f"root/{name}", "file", "") for name in "abcd"])
        data = archive.read_bytes()
        broken = self.root/"truncated.tar.gz"
        broken.write_bytes(data[:-8])
        self.reject("truncated-actual-gzip", lambda: bounded.archive_inventory(broken, "root"),
                    errors=(ValueError, OSError, EOFError, tarfile.TarError))
        self.reject("actual-file-byte-cap", lambda: bounded.sha256(archive, 1))

    def test_owned_fresh_paths_and_no_unsafe_go_environment(self):
        self.reject("lexical-parent", lambda: bounded.canonical(self.root/"x/../y", exists=False))
        self.reject("root-output-alias", lambda: bounded.fresh_directory(self.root, self.root))
        existing = self.root/"existing"
        existing.mkdir()
        self.reject("fresh-output-only", lambda: bounded.fresh_directory(existing, self.root))
        if os.name == "posix":
            go = self.root/"trusted-go"
            go.mkdir()
            workspace = self.root/"environment"
            workspace.mkdir()
            unsafe = {"GOTOOLCHAIN": "auto", "GOSUMDB": "off", "GONOSUMDB": "*",
                      "GOPRIVATE": "*", "GOFLAGS": "-mod=mod", "GOEXPERIMENT": "bad",
                      "GODEBUG": "bad", "GOAUTH": "credential-secret"}
            with mock.patch.dict(os.environ, unsafe):
                env = bounded.clean_go_environment(go, workspace)
            self.assertEqual(env["GOTOOLCHAIN"], "local")
            self.assertEqual(env["GOSUMDB"], "sum.golang.org")
            self.assertEqual(env["GOAUTH"], "off")
            self.assertEqual(env["XDG_CONFIG_HOME"], str(workspace/"home/.config"))
            self.assertEqual((workspace/"home/.config/go/telemetry/mode").read_bytes(), b"off\n")
            for key in ("GONOSUMDB", "GOPRIVATE", "GOFLAGS", "GOEXPERIMENT", "GODEBUG"):
                self.assertNotIn(key, env)

    def test_public_and_direct_entrypoints_stop_before_children(self):
        with mock.patch.object(checker, "LOCK_SHA256", None):
            import fetch_services
            import integration
            root, _ = self.fixture()
            with mock.patch.object(fetch_services, "get") as network:
                self.reject("default-fetch-no-unadmitted-fallback",
                            lambda: fetch_services.fetch(self.root/"fetch"))
                network.assert_not_called()
            with mock.patch.object(sys, "argv", ["integration.py", "--fixtures", str(root),
                                                "--out", str(self.root/"profile"),
                                                "--cli", str(self.root/"missing-cli")]), \
                 mock.patch.object(integration.subprocess, "Popen") as spawn:
                self.reject("direct-integration-before-host", integration.main)
                spawn.assert_not_called()
            self.assertFalse((self.root/"profile").exists())



class NativeHeldIdentityVectors(AdmissionVectors):
    # Loaded separately on Linux; common cases above are not duplicated.
    def test_sealed_identity_survives_path_replacement_without_execution(self):
        root, _ = self.fixture()
        with mock.patch.object(checker, "reference", return_value=copy.deepcopy(LOCK)):
            with checker.admitted_etcd(root) as admitted:
                descriptor = admitted["pass_fds"][0]
                candidate = root/"etcd-source-go1.26.11/etcd"
                old = root/"retained-original"
                candidate.rename(old)
                candidate.write_bytes(b"attacker replacement")
                os.lseek(descriptor, 0, os.SEEK_SET)
                self.assertEqual(os.read(descriptor, 4096), PAYLOAD)
                with self.assertRaises(OSError):
                    os.write(descriptor, b"x")
            self.reject("restart-rechecks-actual-path",
                        lambda: self._enter(root))
        self.assertEqual(old.read_bytes(), PAYLOAD)

    def _enter(self, root):
        with checker.admitted_etcd(root):
            pass

    def test_changed_binary_and_hardlink_and_symlink_rejected_before_spawn(self):
        root, _ = self.fixture()
        candidate = root/"etcd-source-go1.26.11/etcd"
        with mock.patch.object(checker, "reference", return_value=copy.deepcopy(LOCK)):
            candidate.write_bytes(b"x"*len(PAYLOAD))
            self.reject("actual-bytes-not-manifest", lambda: self._enter(root))
            candidate.write_bytes(PAYLOAD)
            alias = self.root/"hardlink"
            os.link(candidate, alias)
            self.reject("actual-hardlink-alias", lambda: self._enter(root))
        sentinel = self.root/"sentinel"
        sentinel.mkdir()
        link = self.root/"directory-link"
        link.symlink_to(sentinel, target_is_directory=True)
        self.reject("ancestor-symlink", lambda: bounded.canonical(link/"x", exists=False))
        self.assertEqual(list(sentinel.iterdir()), [])


def main():
    global WORK
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--expected-optimization", type=int, required=True)
    args = parser.parse_args()
    if sys.flags.optimize != args.expected_optimization:
        raise ValueError("Requested optimization was not active")
    WORK = bounded.canonical(args.work.absolute(), exists=False)
    WORK.mkdir(exist_ok=False)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AdmissionVectors)
    if os.name == "posix":
        for name in ("test_sealed_identity_survives_path_replacement_without_execution",
                     "test_changed_binary_and_hardlink_and_symlink_rejected_before_spawn"):
            suite.addTest(NativeHeldIdentityVectors(name))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    receipt = {"status": "PASS" if result.wasSuccessful() and not result.skipped else "FAIL",
               "tests": result.testsRun, "failures": len(result.failures),
               "errors": len(result.errors), "skips": len(result.skipped),
               "rejectedVectors": REJECTIONS, "pythonOptimizeFlag": sys.flags.optimize,
               "platform": sys.platform,
               "claim": "Synthetic archive/admission/held-byte controls only; real SDK/tool/fixture positive controls and complete source-build N01-N16 coverage remain separate."}
    (WORK/"receipt.json").write_text(json.dumps(receipt, indent=2)+"\n")
    raise SystemExit(0 if receipt["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
