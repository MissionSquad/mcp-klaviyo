from typing import Annotated, Literal
from collections import defaultdict
from pydantic import Field

from klaviyo_mcp_server.models.reporting import ReportPresetTimeframe, ReportTimeframe
from klaviyo_mcp_server.utils.param_types import (
    FilterConfig,
    FilterParam,
    UnionWrapper,
    create_filter_models,
)
from klaviyo_mcp_server.utils.utils import (
    clean_result,
    get_filter_string,
    get_klaviyo_client,
)
from klaviyo_mcp_server.utils.reporting_utils import (
    get_campaign_details,
    get_flow_details,
    matches_detail_filters,
    aggregate_results_by_audience,
)
from klaviyo_mcp_server.utils.tool_decorator import mcp_tool


CampaignStatistic = Literal[
    "bounce_rate",
    "bounced",
    "bounced_or_failed",
    "bounced_or_failed_rate",
    "click_rate",
    "click_to_open_rate",
    "clicks",
    "clicks_unique",
    "conversion_rate",
    "conversion_uniques",
    "conversions",
    "delivered",
    "delivery_rate",
    "failed",
    "failed_rate",
    "open_rate",
    "opens",
    "opens_unique",
    "recipients",
    "spam_complaint_rate",
    "spam_complaints",
    "unsubscribe_rate",
    "unsubscribe_uniques",
    "unsubscribes",
]

CampaignValueStatistic = Literal[
    "average_order_value",
    "conversion_value",
    "revenue_per_recipient",
]

GetCampaignReportFilter = create_filter_models(
    [
        FilterConfig(
            field="send_channel",
            operators=["equals", "contains-any"],
            value_type=Literal["email", "sms", "push-notification"],
        ),
        FilterConfig(
            field="campaign_id", operators=["equals", "contains-any"], value_type=str
        ),
        FilterConfig(
            field="campaign_message_id",
            operators=["equals", "contains-any"],
            value_type=str,
        ),
    ]
)

CampaignReportDetailFilter = create_filter_models(
    [
        FilterConfig(
            field="audiences.included.name",
            operators=["equals", "contains-any"],
            value_type=str,
        ),
        FilterConfig(
            field="tags",
            operators=["equals", "contains-any"],
            value_type=str,
        ),
        FilterConfig(
            field="name",
            operators=["contains-any"],
            value_type=str,
        ),
    ]
)

FlowReportDetailFilter = create_filter_models(
    [
        FilterConfig(
            field="name",
            operators=["contains-any"],
            value_type=str,
        ),
    ]
)


@mcp_tool(has_writes=False)
def get_campaign_report(
    statistics: Annotated[
        list[CampaignStatistic], Field(description="List of statistics to query for.")
    ],
    conversion_metric_id: Annotated[
        str,
        Field(
            description="ID of the metric to be used for conversion statistics. You can get available metrics IDs using the get_metrics tool and just requesting the 'name' field. If a specific metric is not requested, use the ID of the metric named 'Placed Order'. If it doesn't exist, use any metric."
        ),
    ],
    value_statistics: Annotated[
        list[CampaignValueStatistic],
        Field(
            description="List of value statistics to query for. If you see an error about the conversion metric not supporting querying for values data, try again and leave this as an empty list."
        ),
    ] = None,
    timeframe: Annotated[
        UnionWrapper[ReportTimeframe],
        Field(
            ReportPresetTimeframe(key="last_30_days"),
            description="The timeframe to query for data within. The max length a timeframe can be is 1 year. If unspecified, use 1 year.",
        ),
    ] = UnionWrapper(value=ReportPresetTimeframe(key="last_30_days")),
    filters: FilterParam[GetCampaignReportFilter] = None,
    detail_filters: Annotated[
        FilterParam[CampaignReportDetailFilter],
        Field(
            description="Filters to apply to the campaign report. Contains-any does case-insensitive substring matching (for example, 'Test' will match 'test campaign'). Equals does case-insensitive exact matching. Unless explicitly stated, these filters should probably use contains-any."
        ),
    ] = None,
    group_by_audience: Annotated[
        bool,
        Field(
            description="If true, also return a deterministic aggregation grouped by normalized audience label and send_channel."
        ),
    ] = False,
) -> dict:
    """Returns metrics data for campaigns with the given filters and within the given timeframe. Can return performance data such as opens, clicks, and conversions, etc.

    This tool will also give you information about each campaign in the report, such as:
    - audience names and IDs for the campaign. Included audiences are audiences sent the campaign, excluded audiences are audiences not sent the campaign. Excluded audiences can remove profiles from the included audiences.
    - campaign name (if available)
    - send time (if available)
    - send channel (if available)
    - campaign ID
    """

    all_statistics = [*statistics, *(value_statistics or [])]

    body = {
        "data": {
            "type": "campaign-values-report",
            "attributes": {
                "statistics": all_statistics,
                "conversion_metric_id": conversion_metric_id,
                "timeframe": timeframe.value.model_dump(),
                "filter": get_filter_string(filters),
            },
        }
    }

    response = get_klaviyo_client().Reporting.query_campaign_values(body)

    clean_result(response["data"])

    # Get campaign IDs by channel
    campaign_ids_by_channel = defaultdict(list)
    data_results = response["data"]["attributes"]["results"]
    for result in data_results:
        campaign_ids_by_channel[result["groupings"]["send_channel"]].append(
            result["groupings"]["campaign_id"]
        )

    try:
        # Get campaign details including campaign names, and insert into results
        campaigns = get_campaign_details(campaign_ids_by_channel)
        filtered_results = []

        for campaign_data in data_results:
            campaign = campaigns[campaign_data["groupings"]["campaign_id"]]
            campaign_data["campaign_details"] = campaign

            # Apply detail filters if provided
            if detail_filters:
                if campaign and matches_detail_filters(campaign, detail_filters):
                    filtered_results.append(campaign_data)
            else:
                filtered_results.append(campaign_data)

        response["data"]["attributes"]["results"] = filtered_results
    except Exception:
        # If we can't get the campaign details, return the response without the filtered results
        pass

    # Optional deterministic audience aggregation
    if group_by_audience:
        response["data"]["attributes"]["audience_aggregation"] = (
            aggregate_results_by_audience(
                response["data"]["attributes"]["results"],
                bool(value_statistics and "conversion_value" in value_statistics),
            )
        )
    return response


FlowStatistic = CampaignStatistic
FlowValueStatistic = CampaignValueStatistic

GetFlowReportFilter = create_filter_models(
    [
        FilterConfig(
            field="send_channel",
            operators=["equals", "contains-any"],
            value_type=Literal["email", "sms", "push-notification"],
        ),
        FilterConfig(
            field="flow_id", operators=["equals", "contains-any"], value_type=str
        ),
        FilterConfig(
            field="flow_message_id",
            operators=["equals", "contains-any"],
            value_type=str,
        ),
    ]
)


@mcp_tool(has_writes=False)
def get_flow_report(
    statistics: Annotated[
        list[FlowStatistic], Field(description="List of statistics to query for.")
    ],
    conversion_metric_id: Annotated[
        str,
        Field(
            description="ID of the metric to be used for conversion statistics. You can get available metrics IDs using the get_metrics tool and just requesting the 'name' field. If a specific metric is not requested, use the ID of the metric named 'Placed Order'. If it doesn't exist, use any metric."
        ),
    ],
    value_statistics: Annotated[
        list[FlowValueStatistic],
        Field(
            description="List of value statistics to query for. If you see an error about the conversion metric not supporting querying for values data, try again and leave this as an empty list."
        ),
    ] = None,
    timeframe: Annotated[
        UnionWrapper[ReportTimeframe],
        Field(
            ReportPresetTimeframe(key="last_30_days"),
            description="The timeframe to query for data within. The max length a timeframe can be is 1 year. If unspecified, use 1 year.",
        ),
    ] = UnionWrapper(value=ReportPresetTimeframe(key="last_30_days")),
    filters: FilterParam[GetFlowReportFilter] = None,
    detail_filters: Annotated[
        FilterParam[FlowReportDetailFilter],
        Field(
            description="Filters to apply to the flow report. Contains-any does case-insensitive substring matching (for example, 'Test' will match 'test campaign'). Equals does case-insensitive exact matching. Unless explicitly stated, these filters should probbaly use contains-any."
        ),
    ] = None,
) -> dict:
    """Returns metrics data for flows with the given filters and within the given timeframe. Can return performance data such as opens, clicks, and conversions, etc.

    This tool will also give you information about each flow in the report, such as:
    - flow name (if available)
    - trigger type (if available)
    - flow ID
    """
    all_statistics = [*statistics, *(value_statistics or [])]
    body = {
        "data": {
            "type": "flow-values-report",
            "attributes": {
                "statistics": all_statistics,
                "conversion_metric_id": conversion_metric_id,
                "timeframe": timeframe.value.model_dump(),
                "filter": get_filter_string(filters),
            },
        }
    }

    response = get_klaviyo_client().Reporting.query_flow_values(body)

    clean_result(response["data"])

    # Get flow IDs
    flow_ids = [
        result["groupings"]["flow_id"]
        for result in response["data"]["attributes"]["results"]
    ]

    try:
        # Get flow details including flow names, and insert into results
        flows = get_flow_details(flow_ids)
        filtered_results = []

        for flow_data in response["data"]["attributes"]["results"]:
            flow = flows[flow_data["groupings"]["flow_id"]]
            flow_data["flow_details"] = flow

            # Apply detail filters if provided
            if detail_filters:
                if flow and matches_detail_filters(flow, detail_filters):
                    filtered_results.append(flow_data)
            else:
                filtered_results.append(flow_data)

        response["data"]["attributes"]["results"] = filtered_results

        return response
    except Exception:
        # If we can't get the flow details, just return the response without them
        return response
