import viktor as vkt
import base64
import json

from agents import function_tool
from app.crud import get_elements_by_property_name
from app.crud import get_hubs, get_exchange_file_urn, get_elements_by_metadata_name
from app.data_exchange import list_exchanges_in_hub
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
    counts: list[int] = Field(..., description="List of category/item labels")
    volumes: list[float] = Field(..., description="List of category/item labels")


@function_tool()
def display_dashboard(data: DashboardData):
    """
    Render a 2x2 Plotly dashboard (2 pies + 2 bars) using DashBoard.html template.

    Injects data into placeholders (NAMES_PLACEHOLDER, COUNTS_PLACEHOLDER, VOLUMES_PLACEHOLDER)
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
    volumes_json = to_js_string(data.volumes)

    html = html.replace("NAMES_PLACEHOLDER", names_json)
    html = html.replace("COUNTS_PLACEHOLDER", counts_json)
    html = html.replace("VOLUMES_PLACEHOLDER", volumes_json)

    # Store HTML under same key used by the viewer mechanism
    vkt.Storage().set(
        "aps_view",
        data=vkt.File.from_data(html.encode("utf-8")),
        scope="entity",
    )
    return "Dashboard generated. Open the Model Viewer panel to view it."


@function_tool()
def query_elements_by_metadata_name(
    exchange_id: str,
    element_name: str,
    properties: str | None = None,
    include_area: bool = True,
    include_volume: bool = True,
    include_family_name: bool = True,
    extra: str | None = None,
    wildcard: str | None = None,
):
    """
        Query elements by their metadata 'name' and return:
    - Count of matching elements
        - A compact summary of selected properties
    - A short sample of the first few matches with requested properties

    Args:
      exchange_id: Data Exchange ID
      element_name: Exact metadata name to match (e.g., '600mm Diameter')
            properties: Optional comma-separated property names to include in the summary
                                    and sample (e.g., 'Area,Volume,Family Name').
            include_area: Include Area in defaults (ignored if overridden by properties)
            include_volume: Include Volume in defaults (ignored if overridden)
            include_family_name: Include Family Name in defaults (ignored if overridden)
            extra: Optional comma-separated additional properties to include
            wildcard: If '*', include all properties found; if a substring, include all
                                properties whose name contains this substring (case-insensitive)

    Note: Property matching is case-insensitive; typical names include
          'Area', 'Volume', 'Family Name', 'Category', 'Type Name', 'Name'.
    """

    # Defaults and parsing (ordered, de-duplicated)
    def add_props(acc: list[str], seq: list[str] | None):
        if not seq:
            return
        for _p in seq:
            p = _p.strip()
            if p and p not in acc:
                acc.append(p)

    default_props: list[str] = []
    if include_area:
        default_props.append("Area")
    if include_volume:
        default_props.append("Volume")
    if include_family_name:
        default_props.append("Family Name")

    prop_list: list[str] = []
    add_props(prop_list, default_props)
    if properties:
        add_props(prop_list, [p for p in properties.split(",") if p])
    if extra:
        add_props(prop_list, [p for p in extra.split(",") if p])

    data = get_elements_by_metadata_name(
        token=get_token(), exchange_id=exchange_id, metadata_name=element_name
    )

    # Coerce to list of items
    items = []
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        if "results" in data and isinstance(data["results"], list):
            items = data["results"]
        else:
            items = [data]
    else:
        items = []

    count = len(items)

    all_prop_names_original: set[str] = set()
    for it in items:
        props = it.get("properties", {})
        results = props.get("results", []) if isinstance(props, dict) else []
        for p in results:
            name = str(p.get("name", "")).strip()
            if name:
                all_prop_names_original.add(name)

    # Expand prop_list based on wildcard
    if wildcard:
        wc = wildcard.strip()
        if wc == "*":
            add_props(prop_list, sorted(list(all_prop_names_original)))
        else:
            needle = wc.lower()
            matches = [n for n in all_prop_names_original if needle in n.lower()]
            add_props(prop_list, sorted(matches))

    def to_prop_map(item: dict) -> dict:
        """Extract properties into a case-insensitive map."""
        props_ci = {}
        props = item.get("properties", {})
        results = props.get("results", []) if isinstance(props, dict) else []
        for p in results:
            name = str(p.get("name", "")).strip()
            val = p.get("value")
            if name:
                props_ci[name.lower()] = val
        # Add some common top-level aliases if present
        if "name" in item:
            props_ci["name"] = item["name"]
        if "category" in item:
            props_ci["category"] = item["category"]
        if "family" in item:
            props_ci["family"] = item["family"]
        return props_ci

    # Aggregate summary for numerics
    summary_lines = []
    numeric_totals = {}
    numeric_counts = {}
    categorical_sets = {}

    for it in items:
        m = to_prop_map(it)
        for p in prop_list:
            key = p.lower()
            val = m.get(key)
            if isinstance(val, (int, float)):
                numeric_totals[key] = numeric_totals.get(key, 0.0) + float(val)
                numeric_counts[key] = numeric_counts.get(key, 0) + 1
            elif val is not None:
                categorical_sets.setdefault(key, set()).add(val)

    # Build summary text
    if count == 0:
        return f"No elements matched the name: {element_name}"

    for key, total in numeric_totals.items():
        n = max(numeric_counts.get(key, 0), 1)
        avg = total / n
        summary_lines.append(
            f"{key.title()}: total={total:.4f}, avg={avg:.4f}, count={n}"
        )
    for key, values in categorical_sets.items():
        # show up to 5 unique values
        vals = list(values)
        preview = ", ".join(str(v) for v in vals[:5])
        more = "" if len(vals) <= 5 else f" (+{len(vals) - 5} more)"
        summary_lines.append(f"{key.title()}: {preview}{more}")

    # Sample the first few items
    sample_lines = []
    for it in items[: min(5, count)]:
        m = to_prop_map(it)
        id_part = it.get("id", "")
        name_part = it.get("name", m.get("name", ""))
        parts = [f"id={id_part}", f"name={name_part}"]
        for p in prop_list:
            key = p.lower()
            parts.append(f"{p}={m.get(key)}")
        sample_lines.append(" - " + ", ".join(parts))

    # Final text
    header = f"Matched {count} elements for '{element_name}'."
    summary = ("\nSummary: " + "; ".join(summary_lines)) if summary_lines else ""
    samples = ("\nSamples:\n" + "\n".join(sample_lines)) if sample_lines else ""
    return header + summary + samples


def get_element_by_property_name(exchange_id: str, property_name: str, value: str):
    return get_elements_by_property_name(
        token=get_token(),
        exchange_id=exchange_id,
        property_name=property_name,
        value=value,
    )
