from typing import Self, TypedDict, Any
from pydantic import BaseModel, Field, ConfigDict

class DXHub(BaseModel):
    id: str
    name: str

class DXProject(BaseModel):
    id: str
    name: str

class DXItem(BaseModel):
    id: str
    name: str
    typename: str | None = Field(default=None, alias="__typename")

class DXExchange(BaseModel):
    id: str
    name: str
    typename: str | None = Field(default=None, alias="__typename")

class DXFolderTree(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str | None = None
    name: str
    items: list[DXItem] = Field(default_factory=list, description="This Only Include viewables so no PDF no docx. xlsx and so on")
    exchanges: list[DXExchange] = Field(default_factory=list)
    folders: list[Self] = Field(default_factory=list) # A subfoler is a DXFolderTree also

# Typed containers for return shape
class ProjectData(TypedDict):
    name: str
    folder_tree: list[DXFolderTree]

class HubData(TypedDict):
    name: str
    projects: dict[str, ProjectData]


def serialize_folder(node: DXFolderTree) -> dict[str, Any]:
    """Serialize a DXFolderTree node and its children to a JSON-serializable dict.

    Returns keys: id, name, items, exchanges, folders.
    """
    return {
        "id": node.id,
        "name": node.name,
        "items": [
            {"id": i.id, "name": i.name, "typename": i.typename}
            for i in (node.items or [])
        ],
        "exchanges": [
            {"id": e.id, "name": e.name, "typename": e.typename}
            for e in (node.exchanges or [])
        ],
        "folders": [serialize_folder(f) for f in (node.folders or [])],
    }