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

GetListsFields = Literal["name", "created", "updated", "opt_in_process"]

GetListsSort = Literal[
    "created", "-created", "id", "-id", "name", "-name", "updated", "-updated"
]

GetListsFilter = create_filter_models(
    [
        FilterConfig(
            field="name",
            operators=["any", "equals"],
            value_type=str,
            description="Filter for list name. To filter by names that contain a substring, use the 'any' operator.",
        ),
        FilterConfig(field="id", operators=["any", "equals"], value_type=str),
        FilterConfig(field="created", operators=["greater-than"], value_type=datetime),
        FilterConfig(field="updated", operators=["greater-than"], value_type=datetime),
    ]
)


@mcp_tool(has_writes=False)
def get_lists(
    fields: FieldsParam[GetListsFields],
    filters: FilterParam[GetListsFilter] = None,
    sort: SortParam[GetListsSort] = None,
    page_cursor: PageCursorParam = None,
) -> dict:
    """
    Get all lists in an account.

    To filter by tag, do not use the 'filters' parameter. Instead, call this and look for the 'tags' property.

    You can view and edit a list in the Klaviyo UI at https://www.klaviyo.com/lists/{LIST_ID}
    """
    response = get_klaviyo_client().Lists.get_lists(
        fields_list=fields,
        filter=get_filter_string(filters),
        page_cursor=page_cursor,
        sort=sort,
        include=["tags"],
    )
    add_related_data(response, "tag", "tags")
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=False)
def get_list(
    list_id: str,
    include_profile_count: Annotated[
        bool,
        Field(
            description="Whether to include the number of profiles. Only set to True if this is requested.",
        ),
    ] = False,
) -> dict:
    """Get a list with the given list ID.

    You can view and edit a list in the Klaviyo UI at https://www.klaviyo.com/lists/{LIST_ID}"""
    additional_fields = ["profile_count"] if include_profile_count else None
    response = get_klaviyo_client().Lists.get_list(
        list_id, include=["tags"], additional_fields_list=additional_fields
    )
    add_related_data(response, "tag", "tags")
    clean_result(response["data"])
    return response
