from datetime import datetime
from typing import Literal


from klaviyo_mcp_server.utils.param_types import (
    FieldsParam,
    FilterConfig,
    FilterParam,
    PageCursorParam,
    create_filter_models,
    PageSizeParam,
)
from klaviyo_mcp_server.utils.tool_decorator import mcp_tool
from klaviyo_mcp_server.utils.utils import (
    clean_result,
    get_filter_string,
    get_klaviyo_client,
)

GetFlowsFields = Literal[
    "name",
    "status",
    "archived",
    "created",
    "updated",
    "trigger_type",
]

GetFlowsFilter = create_filter_models(
    [
        FilterConfig(field="id", operators=["any"], value_type=str),
        FilterConfig(
            field="name",
            operators=["equals", "contains", "ends-with", "starts-with"],
            value_type=str,
        ),
        FilterConfig(
            field="status",
            operators=["equals"],
            value_type=Literal["live", "draft", "manual", "paused"],
        ),
        FilterConfig(field="archived", operators=["equals"], value_type=bool),
        FilterConfig(
            field="created",
            operators=[
                "equals",
                "greater-or-equal",
                "greater-than",
                "less-or-equal",
                "less-than",
            ],
            value_type=datetime,
        ),
        FilterConfig(
            field="updated",
            operators=[
                "equals",
                "greater-or-equal",
                "greater-than",
                "less-or-equal",
                "less-than",
            ],
            value_type=datetime,
        ),
        FilterConfig(
            field="trigger_type",
            operators=["equals"],
            value_type=Literal[
                "Metric",
                "Added to List",
                "Unconfigured",
                "Date Based",
                "Price Drop",
                "Low Inventory",
            ],
        ),
    ]
)


@mcp_tool(has_writes=False)
def get_flows(
    fields: FieldsParam[GetFlowsFields],
    filters: FilterParam[GetFlowsFilter] = None,
    page_cursor: PageCursorParam = None,
    page_size: PageSizeParam = None,
) -> dict:
    """Returns some or all flows based on filters.

    You can view and edit a flow in the Klaviyo UI at https://www.klaviyo.com/flow/{FLOW_ID}/edit."""

    response = get_klaviyo_client().Flows.get_flows(
        fields_flow=fields,
        filter=get_filter_string(filters),
        page_cursor=page_cursor,
        page_size=page_size,
    )
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=False)
def get_flow(flow_id: str) -> dict:
    """Returns a flow by ID.

    You can view and edit a flow in the Klaviyo UI at https://www.klaviyo.com/flow/{FLOW_ID}/edit."""

    response = get_klaviyo_client().Flows.get_flow(flow_id)
    clean_result(response["data"])
    return response
