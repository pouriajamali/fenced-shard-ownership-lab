"""Eight bounded receipt-oracle vectors; source-authored, not execution evidence.

Run only in an approved test stage. Uses literal expected receipts/SQL rows,
independent hashlib over literal request bytes, and in-memory forgeries only.
"""
import argparse
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

from receipt_oracle import (
    ReceiptOracleError, decode_json, validate_history, validate_receipt,
)

# These fields are independent literals, not generated from observed receipts.
EXPECTED = {
    "original": {"operationId": "original", "delta": "17", "totalAfter": "17",
                 "originalFence": "9007199254740993"},
    "concurrent": {"operationId": "concurrent", "delta": "23", "totalAfter": "40",
                   "originalFence": "9007199254740995"},
    "before-commit": {"operationId": "before-commit", "delta": "31", "totalAfter": "71",
                      "originalFence": "9007199254740997"},
    "after-commit": {"operationId": "after-commit", "delta": "41", "totalAfter": "112",
                     "originalFence": "9007199254740997"},
    "unavailable": {"operationId": "unavailable", "delta": "53", "totalAfter": "165",
                    "originalFence": "9007199254740997"},
}
OWNER = {"owner": "worker-e", "clusterId": "18446744073709551615",
         "fence": "9007199254740999"}
REJECTIONS = []


def observation():
    # Deliberately SQL-name sorted, unlike planned commit order above.
    rows = [
        ("after-commit", 41, b"effect-v1\nsynthetic-shard\nafter-commit\n41\n",
         '{"operationId":"after-commit","delta":"41","totalAfter":"112","originalFence":"9007199254740997"}'),
        ("before-commit", 31, b"effect-v1\nsynthetic-shard\nbefore-commit\n31\n",
         '{"operationId":"before-commit","delta":"31","totalAfter":"71","originalFence":"9007199254740997"}'),
        ("concurrent", 23, b"effect-v1\nsynthetic-shard\nconcurrent\n23\n",
         '{"operationId":"concurrent","delta":"23","totalAfter":"40","originalFence":"9007199254740995"}'),
        ("original", 17, b"effect-v1\nsynthetic-shard\noriginal\n17\n",
         '{"operationId":"original","delta":"17","totalAfter":"17","originalFence":"9007199254740993"}'),
        ("unavailable", 53, b"effect-v1\nsynthetic-shard\nunavailable\n53\n",
         '{"operationId":"unavailable","delta":"53","totalAfter":"165","originalFence":"9007199254740997"}'),
    ]
    return {
        "state": {"shard": "synthetic-shard", "run_id": "literal-run",
                  "cluster_id": "18446744073709551615",
                  "fence": 9007199254740999, "owner": "worker-e", "total": 165},
        "effects": [
            {"shard": "synthetic-shard", "operation_id": name, "delta": delta,
             "request_hash": hashlib.sha256(request_bytes).hexdigest(), "receipt": text}
            for name, delta, request_bytes, text in rows
        ],
    }


class ReceiptVectors(unittest.TestCase):
    def reject(self, label, action, code):
        with self.assertRaisesRegex(ReceiptOracleError, code):
            action()
        REJECTIONS.append(label)

    def history(self, value, preserved=None):
        return validate_history(value, EXPECTED, OWNER, "literal-run", preserved)

    def test_valid_complete_history_and_exact_fence_above_double_precision(self):
        value = observation()
        original_texts = self.history(value)
        self.assertEqual(len(original_texts), 5)
        self.assertEqual(self.history(copy.deepcopy(value), original_texts), original_texts)
        for effect in value["effects"]:
            validate_receipt(decode_json(effect["receipt"]), EXPECTED[effect["operation_id"]])
        # This round-to-double countervalue is a different integer.
        self.assertNotEqual(EXPECTED["original"]["originalFence"], "9007199254740992")

    def test_wrong_sql_total_after_with_same_hash_effect_count_and_sum(self):
        value = observation()
        value["effects"][0]["receipt"] = value["effects"][0]["receipt"].replace(
            '"totalAfter":"112"', '"totalAfter":"165"')
        self.reject("sql-total-after", lambda: self.history(value), "MISMATCH_TOTALAFTER")

    def test_wrong_sql_original_fence_with_same_hash_effect_count_and_sum(self):
        value = observation()
        value["effects"][0]["receipt"] = value["effects"][0]["receipt"].replace(
            '"originalFence":"9007199254740997"', '"originalFence":"9007199254740999"')
        self.reject("sql-original-fence", lambda: self.history(value), "MISMATCH_ORIGINALFENCE")

    def test_matching_forged_sql_and_cli_totals_do_not_become_reference(self):
        value = observation()
        forged = '{"operationId":"after-commit","delta":"41","totalAfter":"165","originalFence":"9007199254740997"}'
        value["effects"][0]["receipt"] = forged
        reply = decode_json(forged)
        self.reject("paired-total-sql", lambda: self.history(value), "MISMATCH_TOTALAFTER")
        self.reject("paired-total-cli",
                    lambda: validate_receipt(reply, EXPECTED["after-commit"]), "MISMATCH_TOTALAFTER")

    def test_matching_forged_sql_and_cli_fences_do_not_become_reference(self):
        value = observation()
        forged = '{"operationId":"after-commit","delta":"41","totalAfter":"112","originalFence":"9007199254740999"}'
        value["effects"][0]["receipt"] = forged
        reply = decode_json(forged)
        self.reject("paired-fence-sql", lambda: self.history(value), "MISMATCH_ORIGINALFENCE")
        self.reject("paired-fence-cli",
                    lambda: validate_receipt(reply, EXPECTED["after-commit"]), "MISMATCH_ORIGINALFENCE")

    def test_missing_duplicate_extra_fields_and_changed_original_text(self):
        missing = {"operationId": "after-commit", "delta": "41",
                   "originalFence": "9007199254740997"}
        extra = {"operationId": "after-commit", "delta": "41", "totalAfter": "112",
                 "originalFence": "9007199254740997", "unexpected": "x"}
        duplicate = '{"operationId":"after-commit","delta":"41","delta":"41","totalAfter":"112","originalFence":"9007199254740997"}'
        self.reject("missing-field", lambda: validate_receipt(missing, EXPECTED["after-commit"]),
                    "RECEIPT_FIELDS")
        self.reject("extra-field", lambda: validate_receipt(extra, EXPECTED["after-commit"]),
                    "RECEIPT_FIELDS")
        self.reject("duplicate-field", lambda: validate_receipt(duplicate, EXPECTED["after-commit"]),
                    "DUPLICATE_JSON_PROPERTY")
        value = observation()
        preserved = self.history(value)
        value["effects"][0]["receipt"] += " "
        self.reject("changed-original-text", lambda: self.history(value, preserved),
                    "ORIGINAL_RECEIPT_TEXT_CHANGED")

    def test_noncanonical_numeric_boolean_and_rounded_receipt_integers(self):
        # Literal, finite representations; no random generator or production parser.
        invalid_deltas = (41, 41.0, True, "041", "+41", " 41", "4.1e1", "0",
                          "9223372036854775808")
        for index, bad in enumerate(invalid_deltas):
            receipt = {"operationId": "after-commit", "delta": bad, "totalAfter": "112",
                       "originalFence": "9007199254740997"}
            self.reject("integer-domain-" + str(index),
                        lambda receipt=receipt: validate_receipt(receipt, EXPECTED["after-commit"]),
                        "NONCANONICAL_DECIMAL_STRING|INTEGER_OUT_OF_RANGE")
        rounded = {"operationId": "original", "delta": "17", "totalAfter": "17",
                   "originalFence": "9007199254740992"}
        self.reject("rounded-fence", lambda: validate_receipt(rounded, EXPECTED["original"]),
                    "MISMATCH_ORIGINALFENCE")
        sql = observation()
        sql["state"]["fence"] = 9007199254741000.0
        self.reject("float-sql-fence", lambda: self.history(sql), "SQL_INTEGER_DOMAIN")

    def test_missing_duplicate_effects_and_wrong_lineage(self):
        missing = observation()
        missing["effects"].pop()
        self.reject("missing-effect", lambda: self.history(missing), "EFFECT_COUNT")
        duplicate = observation()
        duplicate["effects"][1] = copy.deepcopy(duplicate["effects"][0])
        self.reject("duplicate-effect", lambda: self.history(duplicate), "EFFECT_ID_SET")
        wrong_lineage = observation()
        wrong_lineage["state"]["run_id"] = "other-run"
        self.reject("wrong-lineage", lambda: self.history(wrong_lineage), "STATE_LINEAGE")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReceiptVectors)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    ok = result.wasSuccessful() and result.testsRun == 8
    receipt = {
        "schema": 1, "status": "PASS" if ok else "FAIL",
        "testsRun": result.testsRun, "failures": len(result.failures),
        "errors": len(result.errors), "pythonOptimization": sys.flags.optimize,
        "counterexamplesRejected": len(REJECTIONS), "rejections": REJECTIONS,
        "scope": "Fixed literal planned receipts and in-memory SQL/CLI forgeries only",
        "limits": ["Not a live storage corruption experiment or production certification"],
    }
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
