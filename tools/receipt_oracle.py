"""Independent complete-receipt oracle for the fixed synthetic fixture.

Expected values come from the controller's planned commit order and confirmed
acquisitions, never from a receipt or the application's snapshot command.
No I/O, application imports, storage mutation or retry logic lives here.
"""
import hashlib
import json
import re

SHARD = "synthetic-shard"
MAX_INT64 = 9_223_372_036_854_775_807
RECEIPT_FIELDS = frozenset(("operationId", "delta", "totalAfter", "originalFence"))


class ReceiptOracleError(ValueError):
    pass


def require(condition, code):
    # Explicit checks remain active with python -O / PYTHONOPTIMIZE=1.
    if not condition:
        raise ReceiptOracleError(code)


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, "DUPLICATE_JSON_PROPERTY")
        value[key] = item
    return value


def _invalid_constant(_):
    raise ReceiptOracleError("NONFINITE_JSON_NUMBER")


def decode_json(text):
    require(type(text) is str and len(text.encode("utf-8")) <= 32_768,
            "JSON_FRAME_DOMAIN")
    try:
        return json.loads(text, object_pairs_hook=_unique_object,
                          parse_constant=_invalid_constant)
    except (json.JSONDecodeError, RecursionError) as error:
        raise ReceiptOracleError("INVALID_JSON_FRAME") from error


def decimal_string(value, maximum=MAX_INT64):
    require(type(value) is str and re.fullmatch(r"[1-9][0-9]{0,19}", value) is not None,
            "NONCANONICAL_DECIMAL_STRING")
    parsed = int(value)
    require(parsed <= maximum, "INTEGER_OUT_OF_RANGE")
    return parsed


def _sql_integer(value, minimum=0):
    require(type(value) is int and minimum <= value <= MAX_INT64,
            "SQL_INTEGER_DOMAIN")
    return value


def _receipt(value):
    if type(value) is str:
        value = decode_json(value)
    require(type(value) is dict and set(value) == RECEIPT_FIELDS,
            "RECEIPT_FIELDS")
    require(type(value["operationId"]) is str
            and re.fullmatch(r"[A-Za-z0-9._-]{1,64}", value["operationId"]) is not None,
            "RECEIPT_OPERATION_ID")
    delta = decimal_string(value["delta"])
    require(delta <= 1_000_000, "RECEIPT_DELTA_DOMAIN")
    decimal_string(value["totalAfter"])
    decimal_string(value["originalFence"])
    return value


def validate_receipt(actual, expected):
    actual = _receipt(actual)
    reference = _receipt(expected)
    for field in ("operationId", "delta", "totalAfter", "originalFence"):
        require(actual[field] == reference[field],
                "RECEIPT_MISMATCH_" + field.upper())
    return dict(actual)


def validate_history(observed, expected, owner, run_id, preserved_receipts=None):
    """Validate fixed SQL rows; return original raw receipt texts, without mutation.

    expected is in *planned commit order*, not SQL row/operation-id sort order.
    Each independently planned prefix total is checked before inspecting SQL.
    preserved_receipts contains texts from earlier already-validated SQL reads.
    """
    require(type(expected) is dict and len(expected) <= 5, "REFERENCE_EFFECT_COUNT")
    reference_total = 0
    for name, planned in expected.items():
        planned = _receipt(planned)
        require(planned["operationId"] == name, "REFERENCE_OPERATION_ID")
        reference_total += decimal_string(planned["delta"])
        require(reference_total <= MAX_INT64
                and decimal_string(planned["totalAfter"]) == reference_total,
                "REFERENCE_COMMIT_ORDER")

    require(type(observed) is dict, "SQL_OBSERVATION")
    state, effects = observed.get("state"), observed.get("effects")
    require(type(state) is dict and type(effects) is list, "SQL_OBSERVATION")
    require(len(effects) == len(expected), "EFFECT_COUNT")
    require(state.get("shard") == SHARD and state.get("run_id") == run_id
            and state.get("cluster_id") == owner["clusterId"],
            "STATE_LINEAGE")
    decimal_string(owner["clusterId"], 18_446_744_073_709_551_615)
    active_fence = decimal_string(owner["fence"])
    require(_sql_integer(state.get("fence"), 1) == active_fence
            and state.get("owner") == owner["owner"], "STATE_OWNER_FENCE")
    require(_sql_integer(state.get("total")) == reference_total, "STATE_TOTAL")

    seen, texts = set(), {}
    delta_sum = 0
    preserved = {} if preserved_receipts is None else preserved_receipts
    for effect in effects:
        require(type(effect) is dict, "SQL_EFFECT")
        name = effect.get("operation_id")
        require(type(name) is str and name in expected and name not in seen,
                "EFFECT_ID_SET")
        seen.add(name)
        planned = expected[name]
        delta = decimal_string(planned["delta"])
        require(effect.get("shard") == SHARD, "EFFECT_SHARD")
        require(_sql_integer(effect.get("delta"), 1) == delta, "EFFECT_DELTA")
        # Separate Python/BCL-independent reference over the declared wire bytes.
        canonical = ("effect-v1\nsynthetic-shard\n" + name + "\n"
                     + planned["delta"] + "\n").encode("ascii")
        require(effect.get("request_hash") == hashlib.sha256(canonical).hexdigest(),
                "EFFECT_REQUEST_HASH")
        require(type(effect.get("receipt")) is str, "SQL_RECEIPT_TEXT")
        validate_receipt(effect["receipt"], planned)
        require(decimal_string(planned["originalFence"]) <= active_fence,
                "RECEIPT_FUTURE_FENCE")
        if name in preserved:
            require(effect["receipt"] == preserved[name], "ORIGINAL_RECEIPT_TEXT_CHANGED")
        texts[name] = effect["receipt"]
        delta_sum += delta

    require(seen == set(expected) and delta_sum == reference_total, "EFFECT_ID_SET")
    require(set(preserved).issubset(texts), "ORIGINAL_RECEIPT_DISAPPEARED")
    return texts
