from datetime import datetime
from typing import Literal, get_args

from pydantic import Field

from klaviyo_mcp_server.models.events import Event, EventMetric, EventProfile
from klaviyo_mcp_server.utils.param_types import (
    FieldsParam,
    FilterConfig,
    FilterParam,
    PageCursorParam,
    SortParam,
    create_filter_models,
)
from klaviyo_mcp_server.utils.utils import (
    clean_result,
    get_filter_string,
    get_klaviyo_client,
)
from klaviyo_mcp_server.utils.tool_decorator import mcp_tool

GetEventsField = Literal[
    "timestamp",
    "event_properties",
    "datetime",
    "uuid",
]

GetEventsMetricField = Literal[
    "name",
    "created",
    "updated",
    "integration",
]

GetEventsProfileField = Literal[
    "email",
    "phone_number",
    "external_id",
    "first_name",
    "last_name",
]

GetEventsSort = Literal[
    "datetime",
    "-datetime",
    "timestamp",
    "-timestamp",
]

GetEventsInclude = Literal[
    "metric",
    "profile",
    "attributions",
]

GetEventsFilter = create_filter_models(
    [
        FilterConfig(field="metric_id", operators=["equals"], value_type=str),
        FilterConfig(field="profile_id", operators=["equals"], value_type=str),
        FilterConfig(field="profile", operators=["has"], value_type=None),
        FilterConfig(
            field="datetime",
            operators=[
                "greater-or-equal",
                "greater-than",
                "less-or-equal",
                "less-than",
            ],
            value_type=datetime,
        ),
        FilterConfig(
            field="timestamp",
            operators=[
                "greater-or-equal",
                "greater-than",
                "less-or-equal",
                "less-than",
            ],
            value_type=datetime,
        ),
    ]
)


@mcp_tool(has_writes=False, handles_user_generated_content=True)
def get_events(
    events_fields: FieldsParam[GetEventsField],
    sort: SortParam[GetEventsSort] = None,
    filters: FilterParam[GetEventsFilter] = None,
    page_cursor: PageCursorParam = None,
):
    """
    Get events for a given filter such as a profile ID or metric ID.
    """
    response = get_klaviyo_client().Events.get_events(
        fields_event=events_fields,
        fields_metric=list(get_args(GetEventsMetricField)),
        fields_profile=list(get_args(GetEventsProfileField)),
        filter=get_filter_string(filters),
        include=list(get_args(GetEventsInclude)),
        page_cursor=page_cursor,
        sort=sort,
    )
    clean_result(response["included"])
    return response


@mcp_tool(has_writes=True)
def create_event(
    event: Event = Field(description="Attributes of the event to create."),
    profile: EventProfile = Field(description="Profile the event is associated with."),
    metric: EventMetric = Field(description="Metric the event is associated with."),
) -> str:
    """
    Create an event.

    At a minimum, profile and metric objects should include at least one profile identifier (e.g., id, email, or phone_number) and the metric name, respectively.

    Returns "Success" if successful. Raises an error if unsuccessful.
    """

    body = {
        "data": {
            "type": "event",
            "attributes": {
                **event.model_dump(exclude_none=True),
                "metric": {"data": metric.model_dump(exclude_none=True)},
                "profile": {"data": profile.model_dump(exclude_none=True)},
            },
        }
    }

    get_klaviyo_client().Events.create_event(event_create_query_v2=body)

    return "Success"
