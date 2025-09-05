import os
import requests
import httpx

# Query strings
GET_HUBS = """
query GetHubs {
  hubs { results { id name } }
}
"""

GET_PROJECTS = """
query GetProjects($hubId: ID!) {
  projects(hubId: $hubId) { results { id name } }
}
"""

GET_TOP_FOLDERS = """
query GetTopFolders($projectId: ID!) {
  project(projectId: $projectId) {
    folders { results { id name } }
  }
}
"""

FOLDER_FRAGMENT = """
fragment FolderContents on Folder {
  id
  name
  items { results { id name __typename } }
  exchanges { results { id name __typename } }
  folders { results { id name } }
}
"""

GET_FOLDER_CONTENT = f"""
query GetFolderContent($folderId: ID!) {{
  folder(folderId: $folderId) {{ ...FolderContents }}
}}
{FOLDER_FRAGMENT}
"""


GET_PROPERTY_DEFINITION = """query GetPropertyDefinitions($exchangeId: ID!) {
  exchange(exchangeId: $exchangeId) {
    id
    name
    propertyDefinitions {
      pagination { pageSize cursor }
      results {
        name
        valueType
        isReadOnly
        isHidden
        # description, specification, units may be available depending on the def.
      }
    }
  }
}
"""



GET_ELEMENTS_CATEGORIES = """query ListElementCategories($exchangeId: ID!, $pageSize: Int, $cursor: String) {
  exchange(exchangeId: $exchangeId) {
    elements(pagination: { limit: $pageSize, cursor: $cursor }) {
      pagination { pageSize cursor }
      results {
        id
        properties(filter: { names: ["category"] }) {
          results {
            name
            value
          }
        }
      }
    }
  }
}
""" 

GET_EXCHANGE_FILE_URN = """
query GetFileUrn($exchangeId: ID!) {
  exchange(exchangeId: $exchangeId) {
    alternativeIdentifiers {
      fileVersionUrn
    }
  }
}
"""


GET_ELEMENTS_WITH_FILTER = """
query GetElementsWithFilter(
  $exchangeId: ID!
  $elementFilter: ElementFilterInput
  $elementPagination: PaginationInput
) {
  exchange(exchangeId: $exchangeId) {
    id
    name
    elements(filter: $elementFilter, pagination: $elementPagination) {
      pagination { pageSize cursor }
      results {
        id
        name
        properties { results { name value } }
      }
    }
  }
}
"""


DX_GRAPHQL_URL = "https://developer.api.autodesk.com/dataexchange/2023-05/graphql"
APS_REGION = os.environ.get("APS_REGION", "")

def execute_graphql_query(query: str, token: str, variables: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "x-ads-region": APS_REGION,
        "Content-Type": "application/json",
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = requests.post(DX_GRAPHQL_URL, headers=headers, json=payload)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise Exception(f"GraphQL API returned errors:\n{data['errors']}")
    return data.get("data", {})


async def execute_graphql_query_async(
  query: str,
  token: str,
  variables: dict | None = None,
  *,
  client: httpx.AsyncClient | None = None,
) -> dict:
  """Async variant of the GraphQL executor using httpx.

  If a client is provided, it will be used; otherwise a temporary AsyncClient
  will be created for this request.
  """
  headers = {
    "Authorization": f"Bearer {token}",
    "x-ads-region": APS_REGION,
    "Content-Type": "application/json",
  }
  payload: dict = {"query": query}
  if variables:
    payload["variables"] = variables

  if client is None:
    async with httpx.AsyncClient() as _client:
      resp = await _client.post(DX_GRAPHQL_URL, headers=headers, json=payload)
  else:
    resp = await client.post(DX_GRAPHQL_URL, headers=headers, json=payload)

  resp.raise_for_status()
  data = resp.json()
  if "errors" in data:
    raise Exception(f"GraphQL API returned errors:\n{data['errors']}")
  return data.get("data", {})
