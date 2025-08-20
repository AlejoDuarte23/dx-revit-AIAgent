from typing import Optional
import httpx
from app.models import DXHub, DXProject, DXFolderTree, DXItem, DXExchange
from app.queries import (
    execute_graphql_query,
    execute_graphql_query_async,
    GET_HUBS,
    GET_PROJECTS,
    GET_TOP_FOLDERS,
    GET_FOLDER_CONTENT,
    GET_ELEMENTS_CATEGORIES,
    GET_EXCHANGE_FILE_URN,
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

def get_projects(token: str, hub_id: str) -> list[DXProject]:
    return parse_projects(execute_graphql_query(GET_PROJECTS, token, {"hubId": hub_id}))

def get_top_folders(token: str, project_id: str) -> list[DXFolderTree]:
    return parse_top_folders(execute_graphql_query(GET_TOP_FOLDERS, token, {"projectId": project_id}))

def get_folder_tree(token: str, folder_id: str) -> DXFolderTree | None:
    return parse_folder_tree(execute_graphql_query(GET_FOLDER_CONTENT, token, {"folderId": folder_id}))


# Elements categories (by exchange)
def _parse_elements_categories_page(data: dict) -> tuple[dict[str, str | None], str | None]:
    """Parse one page of elements -> category.

    Returns a mapping of element id to category string (or None) and the next cursor.
    """
    out: dict[str, str | None] = {}
    elements = (
        data.get("exchange", {})
        .get("elements", {})
    )
    pagination = elements.get("pagination", {}) or {}
    next_cursor = pagination.get("cursor")
    for el in (elements.get("results", []) or []):
        el_id = el.get("id")
        if not el_id:
            continue
        props = (el.get("properties", {}) or {}).get("results", []) or []
        # find the property named "category"
        category_val = None
        for p in props:
            if p.get("name") == "category":
                category_val = p.get("value")
                break
        out[el_id] = category_val
    return out, next_cursor


def get_elements_categories(
    token: str,
    exchange_id: str,
    *,
    page_size: int = 200,
) -> dict[str, str | None]:
    """Return a mapping of element id -> category for a given exchange.

    Paginates through all elements.
    """
    results: dict[str, str | None] = {}
    cursor: str | None = None
    while True:
        variables = {"exchangeId": exchange_id, "pageSize": page_size, "cursor": cursor}
        data = execute_graphql_query(GET_ELEMENTS_CATEGORIES, token, variables)
        page_map, cursor = _parse_elements_categories_page(data)
        results.update(page_map)
        if not cursor:
            break
    return results


def parse_exchange_file_urn(data: dict) -> str | None:
    alt = data.get("exchange", {}).get("alternativeIdentifiers", {}) or {}
    return alt.get("fileVersionUrn")


def get_exchange_file_urn(token: str, exchange_id: str) -> str | None:
    data = execute_graphql_query(
        GET_EXCHANGE_FILE_URN, token, {"exchangeId": exchange_id}
    )
    print(data)
    return parse_exchange_file_urn(data)


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


async def get_elements_categories_async(
    token: str,
    exchange_id: str,
    *,
    page_size: int = 200,
    client: httpx.AsyncClient | None = None,
) -> dict[str, str | None]:
    """Async version to fetch all element categories for an exchange."""
    results: dict[str, str | None] = {}
    cursor: str | None = None
    while True:
        variables = {"exchangeId": exchange_id, "pageSize": page_size, "cursor": cursor}
        data = await execute_graphql_query_async(
            GET_ELEMENTS_CATEGORIES, token, variables, client=client
        )
        page_map, cursor = _parse_elements_categories_page(data)
        results.update(page_map)
        if not cursor:
            break
    return results


async def get_exchange_file_urn_async(
    token: str,
    exchange_id: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> str | None:
    data = await execute_graphql_query_async(
        GET_EXCHANGE_FILE_URN, token, {"exchangeId": exchange_id}, client=client
    )
    return parse_exchange_file_urn(data)
