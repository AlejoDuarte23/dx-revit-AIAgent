from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


AEC_GRAPHQL_URL = "https://developer.api.autodesk.com/aec/graphql"
DEFAULT_HIGHLIGHT_COLOR = "#f97316"
ELEMENT_CONTEXT_PROPERTY = "Element Context"
FAMILY_NAME_PROPERTY = "Family Name"
ELEMENT_NAME_PROPERTY = "Element Name"


ELEMENTS_BY_TYPE_QUERY = """
query ElementsByType(
  $elementGroupId: ID!,
  $rsqlFilter: String!,
  $pagination: PaginationInput
) {
  elementsByElementGroup(
    elementGroupId: $elementGroupId,
    filter: { query: $rsqlFilter },
    pagination: $pagination
  ) {
    pagination {
      cursor
      pageSize
    }
    results {
      id
      name
      alternativeIdentifiers {
        externalElementId
      }
    }
  }
}
"""


@dataclass(frozen=True)
class ModelContext:
    token: str
    region: str
    version_urn: str
    element_group_id: str


def get_token() -> str:
    import viktor as vkt

    integration = vkt.external.OAuth2Integration("aps-integration-viktor")
    return integration.get_access_token()


def get_model_context(autodesk_file: Any) -> ModelContext:
    token = get_token()
    region = autodesk_file.get_region(token)
    version = autodesk_file.get_latest_version(token)
    element_group_id = get_element_group_id(autodesk_file, token=token)
    return ModelContext(
        token=token,
        region=region,
        version_urn=version.urn,
        element_group_id=element_group_id,
    )


def get_element_group_id(autodesk_file: Any, *, token: str | None = None) -> str:
    access_token = token or get_token()
    return str(autodesk_file.get_aec_data_model_element_group_id(access_token))


def execute_aec_graphql_query(
    query: str,
    token: str,
    region: str,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Region": region,
    }
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    response = requests.post(
        AEC_GRAPHQL_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if "errors" in data:
        raise RuntimeError(f"AEC Data Model query failed: {data['errors']}")
    return data.get("data", {})


def escape_rsql_value(value: str) -> str:
    escaped = (value or "").strip().replace("\\", "\\\\").replace("'", "\\'")
    return escaped


def quote_filter_value(value: str) -> str:
    escaped = escape_rsql_value(value)
    return f"'{escaped}'"


def property_lhs(property_name: str) -> str:
    escaped = (property_name or "").strip().replace("'", "\\'")
    if any(char.isspace() for char in escaped):
        return f"'property.name.{escaped}'"
    return f"property.name.{escaped}"


def elements_page(data: dict[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    elements = data.get("elementsByElementGroup", {}) or {}
    cursor = (elements.get("pagination") or {}).get("cursor")
    return elements.get("results", []) or [], cursor


def fetch_elements_by_type(
    context: ModelContext,
    *,
    type_name: str,
    family_name: str | None = None,
    page_size: int = 200,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    cursor: str | None = None
    rsql_parts = [f"{property_lhs(ELEMENT_CONTEXT_PROPERTY)}==Instance"]

    if family_name:
        rsql_parts.append(
            f"{property_lhs(FAMILY_NAME_PROPERTY)}=={quote_filter_value(family_name)}"
        )

    rsql_parts.append(
        f"{property_lhs(ELEMENT_NAME_PROPERTY)}=={quote_filter_value(type_name)}"
    )
    rsql_filter = " and ".join(rsql_parts)

    while True:
        variables = {
            "elementGroupId": context.element_group_id,
            "rsqlFilter": rsql_filter,
            "pagination": {
                "limit": page_size,
                "cursor": cursor,
            },
        }
        data = execute_aec_graphql_query(
            ELEMENTS_BY_TYPE_QUERY,
            token=context.token,
            region=context.region,
            variables=variables,
        )
        page_results, cursor = elements_page(data)
        results.extend(page_results)
        if not cursor:
            break

    return results


def external_element_id(element: dict[str, Any]) -> str | None:
    alt = element.get("alternativeIdentifiers") or {}
    external_id = alt.get("externalElementId")
    if external_id:
        return str(external_id)
    return None


def find_elements_by_element_name(
    context: ModelContext,
    type_name: str,
    family_name: str | None = None,
) -> list[dict[str, Any]]:
    try:
        filtered_results = fetch_elements_by_type(
            context,
            type_name=type_name,
            family_name=family_name,
        )
    except Exception:
        return []
    return [element for element in filtered_results if external_element_id(element)]


def fetch_elements_by_family(
    context: ModelContext,
    *,
    family_name: str,
    page_size: int = 200,
) -> list[dict[str, Any]]:
    """Fetch all instances of a family without type filtering."""
    results: list[dict[str, Any]] = []
    cursor: str | None = None
    rsql_parts = [
        f"{property_lhs(ELEMENT_CONTEXT_PROPERTY)}==Instance",
        f"{property_lhs(FAMILY_NAME_PROPERTY)}=={quote_filter_value(family_name)}",
    ]
    rsql_filter = " and ".join(rsql_parts)

    while True:
        variables = {
            "elementGroupId": context.element_group_id,
            "rsqlFilter": rsql_filter,
            "pagination": {
                "limit": page_size,
                "cursor": cursor,
            },
        }
        data = execute_aec_graphql_query(
            ELEMENTS_BY_TYPE_QUERY,
            token=context.token,
            region=context.region,
            variables=variables,
        )
        page_results, cursor = elements_page(data)
        results.extend(page_results)
        if not cursor:
            break

    return results


def find_elements_by_family(
    context: ModelContext,
    family_name: str,
) -> list[dict[str, Any]]:
    """Find all instances of a family."""
    try:
        filtered_results = fetch_elements_by_family(
            context,
            family_name=family_name,
        )
    except Exception:
        return []
    return [element for element in filtered_results if external_element_id(element)]


def build_highlight_payload(
    elements: list[dict[str, Any]],
    color: str = DEFAULT_HIGHLIGHT_COLOR,
) -> list[dict[str, str]]:
    seen: set[str] = set()
    payload: list[dict[str, str]] = []
    for element in elements:
        external_id = external_element_id(element)
        if not external_id or external_id in seen:
            continue
        seen.add(external_id)
        payload.append({"externalElementId": external_id, "color": color})
    return payload
