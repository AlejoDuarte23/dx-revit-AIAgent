from typing import Any, Literal, Optional, Union 
from pydantic import BaseModel, Field
from app.models import  QueryElement

class QueryFilter(BaseModel):
    operation: Literal[">"] | Literal["<"] | Literal["="]
    value: float
    output: Literal["Sum"] | Literal["Count"]


# You can pass either:
# - QueryFilter (with output = "Sum" or "Count")
# - Literal "Count"
# - Literal "Sum"
OperationType = Union[QueryFilter, Literal["Count"], Literal["Sum"]]


class QueryToolInput(BaseModel):
    element_name: str = Field(..., description="QueryElement like 'Wall', 'SC123', 'UB304x23x23' ")
    query_property: str | None = Field(..., description="Property name, for example Length, Area, Volume. Can be None if 'Count' is needed")
    operation: OperationType


class QueryToolOutputItem(BaseModel):
    element_name: str
    query_property: str
    op: Literal[">", "<", "=", "Count", "Sum"]
    threshold: Optional[float] = None
    output: Literal["Sum", "Count"]
    result: Union[int, float]
    matched_elements: int


class QueryToolOutput(BaseModel):
    ok: bool
    results: list[QueryToolOutputItem]


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not (isinstance(x, float) and (x != x))


def _to_float(x: Any) -> Optional[float]:
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except Exception:
            return None
    return None


def _match_element_name(e: QueryElement, name: str) -> bool:
    if not name:
        return True
    if e.name == name:
        return True
    # Also accept the property "QueryElement Name"
    if e.prop("QueryElement Name") == name:
        return True
    return False


def _apply_filter(val: Any, f: QueryFilter) -> bool:
    nv = _to_float(val)
    if nv is None:
        return False
    if f.operation == ">":
        return nv > f.value
    if f.operation == "<":
        return nv < f.value
    # "="
    return nv == f.value


def _run_single_query(elements: list[QueryElement], q: QueryToolInput) -> QueryToolOutputItem:
    # Preselect by element name
    candidates = [e for e in elements if _match_element_name(e, q.element_name)]
    print(candidates)
    # Unpack operation
    if isinstance(q.operation, str):
        # Bare "Count" or "Sum"
        if q.operation == "Count":
            # Count elements, ignore property value
            count = len(candidates)
            return QueryToolOutputItem(
                element_name=q.element_name,
                query_property=q.query_property,
                op="Count",
                threshold=None,
                output="Count",
                result=count,
                matched_elements=count,
            )
        else:  # "Sum"
            total = 0.0
            matched = 0
            for e in candidates:
                print(e)
                v = e.prop(q.query_property)
                print(f"{v=}")
                fv = _to_float(v)
                if fv is not None:
                    total += fv
                    matched += 1
            return QueryToolOutputItem(
                element_name=q.element_name,
                query_property=q.query_property,
                op="Sum",
                threshold=None,
                output="Sum",
                result=total,
                matched_elements=matched,
            )

    # QueryFilter path
    f: QueryFilter = q.operation
    matched_vals: list[float] = []
    for e in candidates:
        v = e.prop(q.query_property)
        if _apply_filter(v, f):
            fv = _to_float(v)
            if fv is not None:
                matched_vals.append(fv)

    if f.output == "Count":
        return QueryToolOutputItem(
            element_name=q.element_name,
            query_property=q.query_property,
            op=f.operation,
            threshold=f.value,
            output="Count",
            result=len(matched_vals),
            matched_elements=len(matched_vals),
        )
    else:  # Sum
        return QueryToolOutputItem(
            element_name=q.element_name,
            query_property=q.query_property,
            op=f.operation,
            threshold=f.value,
            output="Sum",
            result=float(sum(matched_vals)) if matched_vals else 0.0,
            matched_elements=len(matched_vals),
        )

