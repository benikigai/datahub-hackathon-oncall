"""Compute and emit data-quality assertions for olist_dirty into DataHub.

CONTEXT: The DataHub Great Expectations plugin (datahub_gx_plugin) builds
SQLite URNs that include the full file path of the .db file as the "database
name" component. The kit's DataHub ingestion uses a different format —
`<platform_instance>.main.<table>` — where 'main' is SQLite's default schema.

These two URN formats don't match, so assertions written by the GE plugin
land on phantom dataset URNs that no agent will ever query. We bypass the
plugin and emit assertions directly via the DataHub Python SDK to the
CORRECT URNs that the kit ingested.

This script computes the same 4 assertions per table that the GE checkpoint
would have computed (3 for olist_products which only has 3), runs the SQL
checks against the local .db file, and emits AssertionInfo + AssertionRunEvent
aspects to DataHub for the matching dataset URNs.

Run setup_gx_source.py against olist.db to produce the L5 baseline (all
assertions PASS); then run this script against olist_dirty.db to produce the
incident state (3 assertions FAIL — the planted issues).
"""
import hashlib
import os
import sqlite3
import time
from pathlib import Path
from typing import Callable

import datahub.emitter.mce_builder as builder
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.metadata.schema_classes import (
    AssertionInfoClass,
    AssertionResultClass,
    AssertionResultTypeClass,
    AssertionRunEventClass,
    AssertionRunStatusClass,
    AssertionStdOperatorClass,
    AssertionStdParameterClass,
    AssertionStdParametersClass,
    AssertionStdParameterTypeClass,
    AssertionTypeClass,
    DatasetAssertionInfoClass,
    DatasetAssertionScopeClass,
)

# ─── Config ─────────────────────────────────────────────────────────────────
# Override via env vars to point this script at a different SQLite + instance:
#   OLIST_DB=gx/data/olist_dirty_2.db OLIST_INSTANCE=olist_dirty_2 python gx/setup_gx.py
DEFAULT_DB = Path(__file__).parent / "data" / "olist_dirty.db"
DB_PATH = Path(os.environ.get("OLIST_DB", str(DEFAULT_DB)))
PLATFORM_INSTANCE = os.environ.get("OLIST_INSTANCE", "olist_dirty")
GMS_URL = os.environ.get("DATAHUB_GMS_URL", "http://100.114.31.63:8080")
TOKEN = os.environ.get("DATAHUB_GMS_TOKEN", "")

assert DB_PATH.exists(), f"Missing {DB_PATH} — scp from studio-a:~/code/datahub-static-assets/datasets/olist-ecommerce/"
assert TOKEN, "DATAHUB_GMS_TOKEN not set — source ~/.config/openclaw/shell-secrets.zsh"


def dataset_urn(table: str) -> str:
    """Match the kit's URN format: <instance>.main.<table>."""
    return builder.make_dataset_urn("sqlite", f"{PLATFORM_INSTANCE}.main.{table}", "PROD")


def assertion_urn(dataset_urn_str: str, name: str) -> str:
    """Stable assertion URN derived from dataset + check name."""
    h = hashlib.md5(f"{dataset_urn_str}::{name}".encode()).hexdigest()
    return f"urn:li:assertion:{h}"


# ─── Assertion definitions ──────────────────────────────────────────────────
# Each tuple: (table, check_name, sql, scope, operator, field, expected_zero, description)
# expected_zero=True means a passing check returns 0 violations
ASSERTIONS = [
    # ─── olist_order_items ───
    (
        "olist_order_items", "order_id_not_null",
        "SELECT COUNT(*) FROM olist_order_items WHERE order_id IS NULL",
        DatasetAssertionScopeClass.DATASET_COLUMN, AssertionStdOperatorClass.NOT_NULL,
        "order_id", True,
        "order_id should never be null",
    ),
    (
        "olist_order_items", "product_id_not_null",
        "SELECT COUNT(*) FROM olist_order_items WHERE product_id IS NULL",
        DatasetAssertionScopeClass.DATASET_COLUMN, AssertionStdOperatorClass.NOT_NULL,
        "product_id", True,
        "product_id should never be null",
    ),
    (
        "olist_order_items", "seller_id_not_null",
        "SELECT COUNT(*) FROM olist_order_items WHERE seller_id IS NULL",
        DatasetAssertionScopeClass.DATASET_COLUMN, AssertionStdOperatorClass.NOT_NULL,
        "seller_id", True,
        "seller_id should never be null",
    ),
    (
        # ★ THE KILLER: planted issue truncates ~5% of seller_ids by 1 char
        "olist_order_items", "seller_id_length_eq_32",
        "SELECT COUNT(*) FROM olist_order_items WHERE LENGTH(seller_id) != 32",
        DatasetAssertionScopeClass.DATASET_COLUMN, AssertionStdOperatorClass.EQUAL_TO,
        "seller_id", True,
        "seller_id length should equal 32 (UUID hash)",
    ),
    # ─── olist_customers ───
    (
        "olist_customers", "customer_id_not_null",
        "SELECT COUNT(*) FROM olist_customers WHERE customer_id IS NULL",
        DatasetAssertionScopeClass.DATASET_COLUMN, AssertionStdOperatorClass.NOT_NULL,
        "customer_id", True,
        "customer_id should never be null",
    ),
    (
        "olist_customers", "customer_unique_id_not_null",
        "SELECT COUNT(*) FROM olist_customers WHERE customer_unique_id IS NULL",
        DatasetAssertionScopeClass.DATASET_COLUMN, AssertionStdOperatorClass.NOT_NULL,
        "customer_unique_id", True,
        "customer_unique_id should never be null",
    ),
    (
        "olist_customers", "customer_id_unique",
        "SELECT COUNT(*) - COUNT(DISTINCT customer_id) FROM olist_customers",
        DatasetAssertionScopeClass.DATASET_COLUMN, AssertionStdOperatorClass.EQUAL_TO,
        "customer_id", True,
        "customer_id should be unique",
    ),
    (
        # ★ THE KILLER: clean olist has exactly 99,441 customers; dirty has 91,486
        "olist_customers", "row_count_eq_99441",
        "SELECT ABS(COUNT(*) - 99441) FROM olist_customers",
        DatasetAssertionScopeClass.DATASET_ROWS, AssertionStdOperatorClass.EQUAL_TO,
        None, True,
        "row count should equal 99441 (full Olist customer set)",
    ),
    # ─── olist_products ───
    (
        "olist_products", "product_id_not_null",
        "SELECT COUNT(*) FROM olist_products WHERE product_id IS NULL",
        DatasetAssertionScopeClass.DATASET_COLUMN, AssertionStdOperatorClass.NOT_NULL,
        "product_id", True,
        "product_id should never be null",
    ),
    (
        "olist_products", "product_id_unique",
        "SELECT COUNT(*) - COUNT(DISTINCT product_id) FROM olist_products",
        DatasetAssertionScopeClass.DATASET_COLUMN, AssertionStdOperatorClass.EQUAL_TO,
        "product_id", True,
        "product_id should be unique",
    ),
    (
        # ★ THE KILLER: ~3% of products have NULL category, breaking translation join
        "olist_products", "product_category_name_not_null",
        "SELECT COUNT(*) FROM olist_products WHERE product_category_name IS NULL",
        DatasetAssertionScopeClass.DATASET_COLUMN, AssertionStdOperatorClass.NOT_NULL,
        "product_category_name", True,
        "product_category_name should never be null",
    ),
]


def build_assertion_info(ds_urn, check_name, scope, operator, field, description):
    """DatasetAssertionInfoClass requires `dataset` (URN) — that's how the
    assertion gets linked to the dataset entity in DataHub."""
    field_urns = [builder.make_schema_field_urn(ds_urn, field)] if field else None
    ds_assertion = DatasetAssertionInfoClass(
        dataset=ds_urn,
        scope=scope,
        operator=operator,
        fields=field_urns,
        nativeType=check_name,
    )
    return AssertionInfoClass(
        type=AssertionTypeClass.DATASET,
        datasetAssertion=ds_assertion,
        description=description,
        customProperties={"check_name": check_name},
    )


def emit_assertion(emitter, table, check_name, scope, operator, field, description, success, observed_value):
    ds_urn = dataset_urn(table)
    a_urn = assertion_urn(ds_urn, check_name)

    # 1. Assertion info (the rule + link to dataset)
    info = build_assertion_info(ds_urn, check_name, scope, operator, field, description)
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=a_urn, aspect=info))

    # 2. Run event (the latest result)
    result = AssertionResultClass(
        type=AssertionResultTypeClass.SUCCESS if success else AssertionResultTypeClass.FAILURE,
        actualAggValue=float(observed_value) if observed_value is not None else None,
    )
    run_event = AssertionRunEventClass(
        timestampMillis=int(time.time() * 1000),
        runId=f"manual-{int(time.time())}",
        assertionUrn=a_urn,
        asserteeUrn=ds_urn,
        status=AssertionRunStatusClass.COMPLETE,
        result=result,
    )
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=a_urn, aspect=run_event))

    return success, observed_value


def main():
    print(f"Computing assertions for {DB_PATH}")
    print(f"Platform instance: {PLATFORM_INSTANCE}")
    print(f"DataHub: {GMS_URL}")
    print()

    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    emitter = DatahubRestEmitter(gms_server=GMS_URL, token=TOKEN)

    n_pass = 0
    n_fail = 0
    by_table: dict[str, dict[str, int]] = {}

    for table, check_name, sql, scope, operator, field, expected_zero, description in ASSERTIONS:
        cur.execute(sql)
        observed = cur.fetchone()[0]
        success = (observed == 0) if expected_zero else (observed != 0)

        emit_assertion(emitter, table, check_name, scope, operator, field, description, success, observed)

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
    print(f"Total: {n_pass} passing, {n_fail} failing")
    print()
    for table, counts in by_table.items():
        marker = "✅" if counts["fail"] == 0 else "❌"
        total = counts["pass"] + counts["fail"]
        print(f"  {marker} {dataset_urn(table)}")
        print(f"      {counts['pass']}/{total} passing")

    return 0 if (n_fail == 3) else 1  # expect exactly 3 failures on dirty


if __name__ == "__main__":
    raise SystemExit(main())
