"""DataHub Python SDK helpers for write operations.

Used by the Fixer agent to write incident annotations back to DataHub.
DataHub docs explicitly recommend the Python SDK over GraphQL mutations
for programmatic writes.

Writes both EditableDatasetPropertiesClass (description shown at top of
DataHub UI dataset page — most visible) AND DatasetPropertiesClass with
customProperties (belt-and-suspenders, queryable via GraphQL).
"""
import os
from datetime import datetime, timezone

from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.metadata.schema_classes import (
    DatasetPropertiesClass,
    EditableDatasetPropertiesClass,
)
import datahub.emitter.mce_builder as builder

GMS_URL = os.environ.get("DATAHUB_GMS_URL", "http://100.114.31.63:8080")


def _emitter() -> DatahubRestEmitter:
    token = os.environ.get("DATAHUB_GMS_TOKEN", "")
    if not token:
        raise RuntimeError("DATAHUB_GMS_TOKEN not set in environment")
    return DatahubRestEmitter(gms_server=GMS_URL, token=token)


def make_dataset_urn(platform_instance: str, table: str) -> str:
    """Build a DataHub dataset URN matching the kit's ingestion convention.

    Example:
        make_dataset_urn("olist_dirty", "olist_order_items") →
        urn:li:dataset:(urn:li:dataPlatform:sqlite,olist_dirty.olist_order_items,PROD)
    """
    return builder.make_dataset_urn("sqlite", f"{platform_instance}.{table}", "PROD")


def update_description(
    urn: str,
    description: str,
    custom_properties: dict[str, str] | None = None,
) -> None:
    """Write a description (visible at the top of the DataHub UI dataset page)
    plus optional customProperties."""
    emitter = _emitter()

    # The editable description is what shows at the top of the dataset page in the UI
    editable = EditableDatasetPropertiesClass(description=description)
    emitter.emit(MetadataChangeProposalWrapper(entityUrn=urn, aspect=editable))

    if custom_properties:
        # Belt-and-suspenders: customProperties also queryable via GraphQL
        props = DatasetPropertiesClass(
            description=description,
            customProperties=custom_properties,
        )
        emitter.emit(MetadataChangeProposalWrapper(entityUrn=urn, aspect=props))


def quarantine_dataset(urn: str, incident_id: str, root_cause: str) -> None:
    """High-level: mark a dataset as quarantined by an incident.
    Used by the Fixer agent."""
    description = f"⚠️ {incident_id}: quarantined by Fixer agent — {root_cause}"
    update_description(
        urn,
        description,
        custom_properties={
            "incident_id": incident_id,
            "status": "quarantined",
            "root_cause": root_cause,
            "quarantined_at": datetime.now(timezone.utc).isoformat(),
        },
    )


def reset_dataset_descriptions(urns: list[str]) -> None:
    """Cleanup helper for tests/demos — clears the editable description on listed datasets."""
    emitter = _emitter()
    for urn in urns:
        emitter.emit(
            MetadataChangeProposalWrapper(
                entityUrn=urn,
                aspect=EditableDatasetPropertiesClass(description=""),
            )
        )


if __name__ == "__main__":
    test_urn = make_dataset_urn("olist_dirty", "olist_order_items")
    print(f"Smoke test: write + reset on {test_urn}")
    quarantine_dataset(test_urn, "TEST-SMOKE", "smoke test from datahub_sdk module")
    print("Wrote. Resetting...")
    reset_dataset_descriptions([test_urn])
    print("Done.")
