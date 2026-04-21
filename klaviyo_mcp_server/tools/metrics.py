from typing import Literal

from klaviyo_mcp_server.utils.param_types import FieldsParam, PageCursorParam
from klaviyo_mcp_server.utils.utils import clean_result, get_klaviyo_client
from klaviyo_mcp_server.utils.tool_decorator import mcp_tool

GetMetricsFields = Literal["name", "created", "updated", "integration"]


@mcp_tool(has_writes=False)
def get_metrics(
    fields: FieldsParam[GetMetricsFields],
    page_cursor: PageCursorParam = None,
) -> dict:
    """Get all metrics in an account.

    You can view and edit a metric in the Klaviyo UI at https://www.klaviyo.com/metric/{METRIC_ID}/{METRIC_NAME}"""
    response = get_klaviyo_client().Metrics.get_metrics(
        fields_metric=fields, page_cursor=page_cursor
    )
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=False)
def get_metric(
    metric_id: str,
) -> dict:
    """Get a metric with the given metric ID.

    You can view and edit a metric in the Klaviyo UI at https://www.klaviyo.com/metric/{METRIC_ID}/{METRIC_NAME}"""
    response = get_klaviyo_client().Metrics.get_metric(metric_id)
    clean_result(response["data"])
    return response
