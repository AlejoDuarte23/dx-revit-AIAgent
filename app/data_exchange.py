from app.crud import (
    get_hubs_async,
    get_projects_async,
    get_top_folders_async,
    get_folder_tree_async,
)
from app.models import DXFolderTree, ProjectData, HubData
import asyncio
import httpx


def print_tree_from_data(
    folder_data: DXFolderTree, prefix: str = "", is_last: bool = True
):
    """
    Prints a nicely formatted ASCII tree with emojis.
    """
    connector = "└─" if is_last else "├─"
    print(f"{prefix}{connector} 📁 {folder_data.name}")
    child_prefix = f"{prefix}   " if is_last else f"{prefix}│  "

    # Prepare children (items, exchanges, then folders)
    children: list[tuple[str, object]] = []
    children += [("item", it) for it in (folder_data.items or [])]
    children += [("exchange", ex) for ex in (folder_data.exchanges or [])]
    children += [("folder", fd) for fd in (folder_data.folders or [])]

    for i, (kind, obj) in enumerate(children):
        last_child = i == len(children) - 1
        c = "└─" if last_child else "├─"
        if kind == "item":
            print(f"{child_prefix}{c} 📄 {obj.name}")
        elif kind == "exchange":
            print(f"{child_prefix}{c} 🔁 {obj.name}")
        else:
            print_tree_from_data(obj, prefix=child_prefix, is_last=last_child)


async def build_folder_tree_async(
    token: str, folder_id: str, client: httpx.AsyncClient
) -> DXFolderTree | None:
    root = await get_folder_tree_async(token, folder_id, client=client)
    if not root:
        return None
    tasks: list[asyncio.Task] = [
        asyncio.create_task(build_folder_tree_async(token, child.id, client))
        for child in (root.folders or [])
        if getattr(child, "id", None)
    ]
    if tasks:
        children = await asyncio.gather(*tasks, return_exceptions=True)
        root.folders = [c for c in children if isinstance(c, DXFolderTree)]
    else:
        root.folders = []
    return root


async def build_top_folder_trees(
    token: str, top_folders, client: httpx.AsyncClient
) -> list[DXFolderTree]:
    tasks = [
        asyncio.create_task(build_folder_tree_async(token, folder.id, client))
        for folder in top_folders
        if getattr(folder, "id", None)
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, DXFolderTree)]


async def get_all_content_from_all_hubs(token: str) -> dict[str, HubData]:
    full_hierarchy: dict[str, HubData] = {}
    async with httpx.AsyncClient() as client:
        # fetch hubs
        hubs = await get_hubs_async(token, client=client)

        for hub in hubs:
            full_hierarchy[hub.id] = {"name": hub.name, "projects": {}}
            # fetch projects per hub
            projects = await get_projects_async(token, hub.id, client=client)

            for project in projects:
                project_data: ProjectData = {"name": project.name, "folder_tree": []}
                full_hierarchy[hub.id]["projects"][project.id] = project_data

                try:
                    # Get Top folders
                    top_folders = await get_top_folders_async(
                        token, project.id, client=client
                    )
                    trees = await build_top_folder_trees(token, top_folders, client)
                    for tree in trees:
                        # Print the fully expanded tree, not the shallow folder ref
                        print_tree_from_data(tree)
                        project_data["folder_tree"].append(tree)
                except Exception:
                    # skip if fails.
                    continue

    return full_hierarchy


# Helpers to collect exchanges from a built folder tree
def _collect_exchanges(node: DXFolderTree, out: dict[str, str]) -> None:
    for ex in (node.exchanges or []):
        # Note: if duplicate names exist, last one wins
        out[ex.name] = ex.id
    for child in (node.folders or []):
        _collect_exchanges(child, out)


async def list_exchanges_in_hub(
    token: str,
    *,
    hub_id: str | None = None,
    hub_name: str | None = None,
) -> dict[str, str]:
    """List all exchanges in a given hub.

    Inputs: provide either hub_id or hub_name. If hub_name is given, it will be
    resolved to a hub id (case-insensitive match).

    Returns: dict mapping { exchange_name: exchange_id } across all projects
    and folders in the hub.
    """
    if not hub_id:
        # Resolve by name
        hubs = await get_hubs_async(token)
        name_lower = (hub_name or "").strip().lower()
        # Prefer exact case-sensitive first, then case-insensitive
        selected = next((h for h in hubs if h.name == hub_name), None) or next(
            (h for h in hubs if h.name.lower() == name_lower), None
        )
        if not selected:
            raise ValueError("Hub not found by name")
        hub_id = selected.id

    exchanges: dict[str, str] = {}
    async with httpx.AsyncClient() as client:
        projects = await get_projects_async(token, hub_id, client=client)
        for project in projects:
            try:
                top_folders = await get_top_folders_async(token, project.id, client=client)
                trees = await build_top_folder_trees(token, top_folders, client)
                for tree in trees:
                    _collect_exchanges(tree, exchanges)
            except Exception:
                # Skip projects that fail to expand
                continue
    return exchanges
