"""L5 baseline: same 11 assertions as setup_gx.py but against olist.db (clean
source). Expected outcome: ALL 11 assertions PASS. The diff between this and
setup_gx.py output (3 failures) is the production-only failure set that the
Reality-Checker agent surfaces.

This file imports from setup_gx.py to keep the assertion definitions DRY.
Only the DB_PATH and PLATFORM_INSTANCE differ.
"""
import os
import sqlite3
import time
from pathlib import Path

from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter

# Import shared definitions from setup_gx.py
import sys
sys.path.insert(0, str(Path(__file__).parent))
from setup_gx import (  # noqa: E402
    ASSERTIONS,
    build_assertion_info,
    assertion_urn,
)
import datahub.emitter.mce_builder as builder
from datahub.metadata.schema_classes import (
    AssertionResultClass,
    AssertionResultTypeClass,
    AssertionRunEventClass,
    AssertionRunStatusClass,
)

# ─── Override config to point at clean source ─────────────────────────────
DB_PATH = Path(__file__).parent / "data" / "olist.db"
PLATFORM_INSTANCE = "olist_source"
GMS_URL = os.environ.get("DATAHUB_GMS_URL", "http://100.114.31.63:8080")
TOKEN = os.environ.get("DATAHUB_GMS_TOKEN", "")

assert DB_PATH.exists(), f"Missing {DB_PATH} — scp from studio-a:~/code/datahub-static-assets/datasets/olist-ecommerce/"
assert TOKEN, "DATAHUB_GMS_TOKEN not set"


def dataset_urn(table: str) -> str:
    return builder.make_dataset_urn("sqlite", f"{PLATFORM_INSTANCE}.main.{table}", "PROD")


def emit_assertion_for_source(emitter, table, check_name, scope, operator, field, description, success, observed):
    ds_urn = dataset_urn(table)
    a_urn = assertion_urn(ds_urn, check_name)

    info = build_assertion_info(ds_urn, check_name, scope, operator, field, description)
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=a_urn, aspect=info))

    result = AssertionResultClass(
        type=AssertionResultTypeClass.SUCCESS if success else AssertionResultTypeClass.FAILURE,
        actualAggValue=float(observed) if observed is not None else None,
    )
    run_event = AssertionRunEventClass(
        timestampMillis=int(time.time() * 1000),
        runId=f"manual-source-{int(time.time())}",
        assertionUrn=a_urn,
        asserteeUrn=ds_urn,
        status=AssertionRunStatusClass.COMPLETE,
        result=result,
    )
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=a_urn, aspect=run_event))
    return success


def main():
    print(f"Computing baseline assertions for {DB_PATH}")
    print(f"Platform instance: {PLATFORM_INSTANCE}")
    print(f"DataHub: {GMS_URL}")
    print()

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    emitter = DatahubRestEmitter(gms_server=GMS_URL, token=TOKEN)

    n_pass = n_fail = 0
    by_table: dict[str, dict[str, int]] = {}

    for table, check_name, sql, scope, operator, field, expected_zero, description in ASSERTIONS:
        cur.execute(sql)
        observed = cur.fetchone()[0]
        success = (observed == 0) if expected_zero else (observed != 0)

        emit_assertion_for_source(emitter, table, check_name, scope, operator, field, description, success, observed)

        marker = "✅" if success else "❌"
        print(f"  {marker} {table:<22} {check_name:<35} observed={observed}")

        if success:
            n_pass += 1
        else:
            n_fail += 1
        by_table.setdefault(table, {"pass": 0, "fail": 0})
        by_table[table]["pass" if success else "fail"] += 1

    conn.close()

    print()
    print(f"Total: {n_pass} passing, {n_fail} failing  (expected: 11 / 0 — clean baseline)")
    print()
    for table, counts in by_table.items():
        marker = "✅" if counts["fail"] == 0 else "❌"
        total = counts["pass"] + counts["fail"]
        print(f"  {marker} {dataset_urn(table)}")
        print(f"      {counts['pass']}/{total} passing")

    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
