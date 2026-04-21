from datetime import datetime
from typing import Literal, Annotated

from klaviyo_mcp_server.utils.add_related_data import add_related_data
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

from pydantic import Field

GetSegmentsFields = Literal[
    "name",
    "definition",
    "definition.condition_groups",
    "created",
    "updated",
    "is_active",
    "is_processing",
    "is_starred",
]

GetSegmentsSort = Literal[
    "created", "-created", "id", "-id", "name", "-name", "updated", "-updated"
]

GetSegmentsFilter = create_filter_models(
    [
        FilterConfig(
            field="name",
            operators=["any", "equals"],
            value_type=str,
            description="Filter for segment name. To filter by names that contain a substring, use the 'any' operator.",
        ),
        FilterConfig(field="id", operators=["any", "equals"], value_type=str),
        FilterConfig(field="created", operators=["greater-than"], value_type=datetime),
        FilterConfig(field="updated", operators=["greater-than"], value_type=datetime),
        FilterConfig(field="is_active", operators=["any", "equals"], value_type=bool),
        FilterConfig(field="is_starred", operators=["equals"], value_type=bool),
    ]
)


@mcp_tool(has_writes=False)
def get_segments(
    fields: FieldsParam[GetSegmentsFields],
    filters: FilterParam[GetSegmentsFilter] = None,
    sort: SortParam[GetSegmentsSort] = None,
    page_cursor: PageCursorParam = None,
) -> dict:
    """
    Get all segments in an account.

    To filter by tag, do not use the 'filters' parameter. Instead, call this and look for the 'tags' property.

    You can view and edit a segment in the Klaviyo UI at https://www.klaviyo.com/lists/{SEGMENT_ID}
    """
    response = get_klaviyo_client().Segments.get_segments(
        fields_segment=fields,
        filter=get_filter_string(filters),
        page_cursor=page_cursor,
        sort=sort,
        include=["tags"],
    )
    add_related_data(response, "tag", "tags")
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=False)
def get_segment(
    segment_id: str,
    include_profile_count: Annotated[
        bool,
        Field(
            description="Whether to include the number of profiles. Only set to True if this is requested.",
        ),
    ] = False,
) -> dict:
    """Get a segment with the given segment ID.

    You can view and edit a segment in the Klaviyo UI at https://www.klaviyo.com/lists/{SEGMENT_ID}"""
    additional_fields = ["profile_count"] if include_profile_count else None
    response = get_klaviyo_client().Segments.get_segment(
        segment_id, include=["tags"], additional_fields_segment=additional_fields
    )
    add_related_data(response, "tag", "tags")
    clean_result(response["data"])
    return response
