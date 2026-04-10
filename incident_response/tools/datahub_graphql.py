"""DataHub GraphQL POST helper.

Used by Detective and Reality-Checker to query DataHub via the authenticated
GraphQL endpoint at $DATAHUB_GMS_URL/api/graphql.
"""
import os
from typing import Any
import httpx

GMS_URL = os.environ.get("DATAHUB_GMS_URL", "http://100.114.31.63:8080")
TIMEOUT = 10.0


class DatahubError(Exception):
    """Raised when DataHub returns an HTTP error or GraphQL errors."""


def _token() -> str:
    """Read the token at call time so test fixtures can patch the env var."""
    tok = os.environ.get("DATAHUB_GMS_TOKEN", "")
    if not tok:
        raise DatahubError(
            "DATAHUB_GMS_TOKEN not set — source ~/.config/openclaw/shell-secrets.zsh "
            "or set it explicitly in .env"
        )
    return tok


def query(graphql: str, variables: dict | None = None) -> dict[str, Any]:
    """POST a GraphQL query to DataHub. Returns the `data` field on success.
    Raises DatahubError on HTTP error or GraphQL errors.
    """
    payload: dict[str, Any] = {"query": graphql}
    if variables:
        payload["variables"] = variables
    r = httpx.post(
        f"{GMS_URL}/api/graphql",
        json=payload,
        headers={
            "Authorization": f"Bearer {_token()}",
            "Content-Type": "application/json",
        },
        timeout=TIMEOUT,
    )
    if r.status_code != 200:
        raise DatahubError(f"HTTP {r.status_code}: {r.text[:200]}")
    body = r.json()
    if "errors" in body:
        raise DatahubError(f"GraphQL errors: {body['errors']}")
    return body.get("data", {})


async def query_async(graphql: str, variables: dict | None = None) -> dict[str, Any]:
    """Async variant — used by orchestrator + agents."""
    payload: dict[str, Any] = {"query": graphql}
    if variables:
        payload["variables"] = variables
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        r = await client.post(
            f"{GMS_URL}/api/graphql",
            json=payload,
            headers={
                "Authorization": f"Bearer {_token()}",
                "Content-Type": "application/json",
            },
        )
    if r.status_code != 200:
        raise DatahubError(f"HTTP {r.status_code}: {r.text[:200]}")
    body = r.json()
    if "errors" in body:
        raise DatahubError(f"GraphQL errors: {body['errors']}")
    return body.get("data", {})


if __name__ == "__main__":
    result = query(
        '{ search(input: {type: DATASET, query: "olist_orders", start: 0, count: 3}) { total } }'
    )
    print(f"OK: {result['search']['total']} olist_orders matches in DataHub")
