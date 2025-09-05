import viktor as vkt
import base64
import json

from app.tools.querys import QueryToolOutputItem, QueryToolOutput  ,_run_single_query, QueryToolInput
from agents import function_tool
from app.crud import get_hubs, get_exchange_file_urn, get_elements_by_metadata_name
from app.data_exchange import list_exchanges_in_hub
from app.models import parse_query_elements
from pathlib import Path
from pydantic import BaseModel, Field

def get_token() -> str:
    integration = vkt.external.OAuth2Integration("aps-integration-viktor")
    return integration.get_access_token()


@function_tool()
def get_hub_tool():
    """List the hubs to the user, display the name and also de id"""
    return get_hubs(token=get_token())


@function_tool()
async def get_exchanges_tool(hub_id: str | None = None, hub_name: str | None = None):
    """List the exchanges in a hub (by id or name). Returns {name: id}."""
    return await list_exchanges_in_hub(
        token=get_token(), hub_id=hub_id, hub_name=hub_name
    )


@function_tool()
def get_exchange_file_file_urn_tool(exchange_id: str) -> str:
    """input the exchange id and return the urn for the exchange do not change anithing about the urn even the "version=1" """
    return get_exchange_file_urn(token=get_token(), exchange_id=exchange_id)


@function_tool()
def display_exchange_model(urn: str, filter_element: str | None = None):
    """user the urn someting like: urn:adsk.wipprod... to display the exchange model"""
    print(f"Received -> {urn=}, {filter_element=}")
    token = get_token()
    urn_bs64 = base64.urlsafe_b64encode(urn.encode()).decode().rstrip("=")
    print(f"[DEBUG] {urn_bs64=}")
    # Read the HTML template from the views folder
    html_path = Path(__file__).resolve().parent.parent / "views" / "ApsViewer.html"
    html = html_path.read_text(encoding="utf-8")
    html = html.replace("APS_TOKEN_PLACEHOLDER", token)
    html = html.replace("URN_PLACEHOLDER", urn_bs64)
    safe_filter = (
        (filter_element or "")
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("'", "\\'")
    )
    print(f"[DEBUG] injecting FILTER_ELEMENT= '{safe_filter}'")
    html = html.replace("FILTER_ELEMENT_PLACEHOLDER", safe_filter)

    vkt.Storage().set(
        "aps_view",
        data=vkt.File.from_data(html.encode("utf-8")),
        scope="entity",
    )
    return (
        "Tool Excecution Complete. In the RHS the model will be displayed in a second"
    )


class DashboardData(BaseModel):
    """Inputs for the dashboard visualization."""
    names: list[str] = Field(..., description="List of category/item labels")
    counts: list[int] = Field(..., description="List of category/item counts")
    attributes: list[float] = Field(..., description="List of attribute/item values")
    attribute_name: str = Field(..., description="Name of the attribute Length, Volume, Area, etc.")

@function_tool()
def display_dashboard(data: DashboardData):
    """
    Render a 2x2 Plotly dashboard (2 pies + 2 bars) using DashBoard.html template.

    Injects data into placeholders (NAMES_PLACEHOLDER, COUNTS_PLACEHOLDER, ATTRIBUTES_PLACEHOLDER, ATTRIBUTE_NAME_PLACEHOLDER)
    and stores the HTML in VIKTOR storage under key 'aps_view'.

    Returns a short status message; open the 'Model Viewer' WebView to see it.
    """
    print(data)

    # Read template
    html_path = Path(__file__).resolve().parent.parent / "views" / "DashBoard.html"
    html = html_path.read_text(encoding="utf-8")

    # Prepare JSON and escape for single-quoted JS string in the template
    def to_js_string(value) -> str:
        s = json.dumps(value, ensure_ascii=False)
        # Escape backslashes and single quotes because template uses single quotes around JSON
        s = s.replace("\\", "\\\\").replace("'", "\\'")
        return s

    names_json = to_js_string(data.names)
    counts_json = to_js_string(data.counts)
    attributes_json = to_js_string(data.attributes)
    attribute_name_json = to_js_string(data.attribute_name)

    html = html.replace("NAMES_PLACEHOLDER", names_json)
    html = html.replace("COUNTS_PLACEHOLDER", counts_json)
    html = html.replace("ATTRIBUTES_PLACEHOLDER", attributes_json)
    html = html.replace("ATTRIBUTE_NAME_PLACEHOLDER", attribute_name_json)

    # Store HTML under same key used by the viewer mechanism
    vkt.Storage().set(
        "aps_view",
        data=vkt.File.from_data(html.encode("utf-8")),
        scope="entity",
    )
    return "Dashboard generated. Open the Model Viewer panel to view it."


@function_tool()
def query_elements(exchange_id: str, querys: list[QueryToolInput]) -> str:

    """
    Tool, query elements in a Data Exchange by name and property.

    Behavior, for each item in querys, fetch elements where element.name equals element_name or the property "Element Name" equals it, read query_property, then
    Count returns the number of matching elements, Sum returns the sum of numeric values, QueryFilter applies ">", "<", or "=", against value, then returns Count or Sum.

    Inputs,
    exchange_id, string,
    querys, list of QueryToolInput with fields, element_name, query_property, operation where operation is "Count", "Sum", or QueryFilter {operation, value, output}.

    Output, QueryToolOutput with ok and results in the same order as input, each item includes element_name, query_property, op, threshold, output, result, matched_elements.

    Example,
    {"exchange_id": "EX_1", "querys": [
      {"element_name": "CL_W1", "query_property": "Length", "operation": "Count"},
      {"element_name": "CL_W1", "query_property": "Length", "operation": {"operation": ">", "value": 0.5, "output": "Sum"}}
    ]}
    """
    print(f"[DEBUG] {exchange_id=}, {querys=}")
    out: list[QueryToolOutputItem] = []
    for q in querys:
        elements_raw = get_elements_by_metadata_name(
            token=get_token(),
            exchange_id=exchange_id,
            metadata_name=q.element_name
        )
        print(f"[DEBUG] elements_raw type: {type(elements_raw)}, len: {len(elements_raw)}")
        if elements_raw:
            print(f"[DEBUG] elements_raw[0]: {elements_raw[0]}")
        # Patch: Ensure alternativeIdentifiers exists for each element
        for el in elements_raw:
            if 'alternativeIdentifiers' not in el:
                el['alternativeIdentifiers'] = {}
        try:
            elements = parse_query_elements(elements_raw)  # Convert to QueryElement list
        except Exception as e:
            print(f"[ERROR] parse_query_elements failed: {e}")
            for idx, el in enumerate(elements_raw):
                print(f"[ERROR] Element {idx}: {el}")
            raise
        out.append(_run_single_query(elements, q))
        print(f"[DEBUG] out: {out}")
    return str(QueryToolOutput(ok=True, results=out))