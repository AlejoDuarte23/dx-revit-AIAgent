import httpx
from functools import lru_cache
from typing import Optional
from app.models import DXHub, DXProject, DXFolderTree, DXItem, DXExchange
from app.queries import (
    execute_graphql_query,
    execute_graphql_query_async,
    GET_HUBS,
    GET_PROJECTS,
    GET_TOP_FOLDERS,
    GET_FOLDER_CONTENT,
    GET_EXCHANGE_FILE_URN,
    GET_ELEMENTS_WITH_FILTER,
)

# Parsers
def parse_hubs(data: dict) -> list[DXHub]:
    arr = data.get("hubs", {}).get("results", []) or []
    return [DXHub.model_validate(x) for x in arr]

def parse_projects(data: dict) -> list[DXProject]:
    arr = data.get("projects", {}).get("results", []) or []
    return [DXProject.model_validate(x) for x in arr]

def parse_top_folders(data: dict) -> list[DXFolderTree]:
    # Reuse DXFolderTree for refs (id+name only)
    arr = data.get("project", {}).get("folders", {}).get("results", []) or []
    return [DXFolderTree.model_validate(x) for x in arr]

def parse_folder_tree(data: dict) -> Optional[DXFolderTree]:
    raw = data.get("folder") or {}
    if not raw:
        return None
    # folders have subfolder thus is recursive 
    def _build(node: dict) -> DXFolderTree:
        items = [DXItem.model_validate(i) for i in (node.get("items", {}).get("results", []) or [])]
        exchanges = [DXExchange.model_validate(e) for e in (node.get("exchanges", {}).get("results", []) or [])]
        subfolders_raw = node.get("folders", {}).get("results", []) or []
        # Create shallow child nodes (id+name); caller can expand recursively
        subfolders = [DXFolderTree.model_validate({"id": sf.get("id"), "name": sf.get("name")}) for sf in subfolders_raw]
        return DXFolderTree(
            id=node.get("id"),
            name=node.get("name"),
            items=items,
            exchanges=exchanges,
            folders=subfolders,
        )

    return _build(raw)

def get_hubs(token: str) -> list[DXHub]:
    return parse_hubs(execute_graphql_query(GET_HUBS, token))

def parse_exchange_file_urn(data: dict) -> str | None:
    alt = data.get("exchange", {}).get("alternativeIdentifiers", {}) or {}
    return alt.get("fileVersionUrn")


def get_exchange_file_urn(token: str, exchange_id: str) -> str | None:
    data = execute_graphql_query(
        GET_EXCHANGE_FILE_URN, token, {"exchangeId": exchange_id}
    )
    print(data)
    return parse_exchange_file_urn(data)


def _dx_quote_single(val: str) -> str:
    v = (val or "").strip()
    v = v.replace("'", "\\'")
    return f"'{v}'"


def _property_lhs(property_name: str) -> str:
    name = (property_name or "").strip()
    # If name includes whitespace or special chars, quote the whole token as
    # 'property.name.Family Name'
    import re
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        name = name.replace("'", "\\'")
        return f"'property.name.{name}'"
    return f"property.name.{name}"


def build_property_equals_filter(property_name: str, value: str) -> str:
    return f"{_property_lhs(property_name)}=={_dx_quote_single(value)}"


def build_metadata_name_equals_filter(value: str) -> str:
    return f"metadata.name=={_dx_quote_single(value)}"


def _parse_elements_with_properties_page(data: dict) -> tuple[list[dict], str | None]:
    els = data.get("exchange", {}).get("elements", {}) or {}
    cursor = (els.get("pagination") or {}).get("cursor")
    results = els.get("results") or []
    return results, cursor


def get_elements_with_filter(
    token: str,
    exchange_id: str,
    *,
    filter_query: str,
    page_size: int = 200,
) -> list[dict]:
    all_results: list[dict] = []
    cursor: str | None = None
    while True:
        variables = {
            "exchangeId": exchange_id,
            "elementFilter": {"query": filter_query},
            "elementPagination": {"limit": page_size, "cursor": cursor or ""},
        }
        data = execute_graphql_query(GET_ELEMENTS_WITH_FILTER, token, variables)
        page, cursor = _parse_elements_with_properties_page(data)
        all_results.extend(page)
        if not cursor:
            break
    return all_results


def get_elements_by_property_name(
    token: str,
    exchange_id: str,
    *,
    property_name: str,
    value: str,
    page_size: int = 200,
) -> list[dict]:
    return get_elements_with_filter(
        token,
        exchange_id,
        filter_query=build_property_equals_filter(property_name, value),
        page_size=page_size,
    )

@lru_cache(maxsize=12)
def get_elements_by_metadata_name(
    token: str,
    exchange_id: str,
    *,
    metadata_name: str,
    page_size: int = 200,
) -> list[dict]:
    return get_elements_with_filter(
        token,
        exchange_id,
        filter_query=build_metadata_name_equals_filter(metadata_name),
        page_size=page_size,
    )

# Async counterparts used by orchestrator
async def get_hubs_async(token: str, *, client: httpx.AsyncClient | None = None) -> list[DXHub]:
    data = await execute_graphql_query_async(GET_HUBS, token, client=client)
    return parse_hubs(data)


async def get_projects_async(
    token: str, hub_id: str, *, client: httpx.AsyncClient | None = None
) -> list[DXProject]:
    data = await execute_graphql_query_async(
        GET_PROJECTS, token, {"hubId": hub_id}, client=client
    )
    return parse_projects(data)


async def get_top_folders_async(
    token: str, project_id: str, *, client: httpx.AsyncClient | None = None
) -> list[DXFolderTree]:
    data = await execute_graphql_query_async(
        GET_TOP_FOLDERS, token, {"projectId": project_id}, client=client
    )
    return parse_top_folders(data)


async def get_folder_tree_async(
    token: str, folder_id: str, *, client: httpx.AsyncClient | None = None
) -> DXFolderTree | None:
    data = await execute_graphql_query_async(
        GET_FOLDER_CONTENT, token, {"folderId": folder_id}, client=client
    )
    return parse_folder_tree(data)