from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

from klaviyo_mcp_server.models.profiles import (
    Profile,
    ProfilePatchProperties,
    ProfileUpdate,
)
from klaviyo_mcp_server.utils.param_types import (
    FieldsParam,
    FilterConfig,
    FilterParam,
    PageCursorParam,
    PageSizeParam,
    SortParam,
    create_filter_models,
)
from klaviyo_mcp_server.utils.utils import (
    clean_result,
    get_filter_string,
    get_klaviyo_client,
)
from klaviyo_mcp_server.utils.tool_decorator import mcp_tool

GetProfilesField = Literal[
    "email",
    "phone_number",
    "external_id",
    "first_name",
    "last_name",
    "organization",
    "locale",
    "title",
    "image",
    "created",
    "updated",
    "last_event_date",
    "location",
    "location.address1",
    "location.address2",
    "location.city",
    "location.country",
    "location.latitude",
    "location.longitude",
    "location.region",
    "location.zip",
    "location.timezone",
    "location.ip",
    "properties",
]

GetProfilesSort = Literal[
    "created", "-created", "email", "-email", "id", "-id", "updated", "-updated"
]

GetProfilesFilter = create_filter_models(
    [
        FilterConfig(field="id", operators=["any", "equals"], value_type=str),
        FilterConfig(field="email", operators=["any", "equals"], value_type=str),
        FilterConfig(field="phone_number", operators=["any", "equals"], value_type=str),
        FilterConfig(field="external_id", operators=["any", "equals"], value_type=str),
        FilterConfig(field="_kx", operators=["equals"], value_type=str),
        FilterConfig(
            field="created",
            operators=["greater-than", "less-than"],
            value_type=datetime,
            description="If using greater-than, you may only sort by 'created'. If using less-than, you may only sort by '-created'.",
        ),
        FilterConfig(
            field="updated",
            operators=["greater-than", "less-than"],
            value_type=datetime,
            description="If using greater-than, you may only sort by 'updated'. If using less-than, you may only sort by '-updated'.",
        ),
    ]
)


@mcp_tool(has_writes=False, handles_user_generated_content=True)
def get_profiles(
    fields: FieldsParam[GetProfilesField],
    sort: SortParam[GetProfilesSort] = None,
    filters: FilterParam[GetProfilesFilter] = None,
    page_size: PageSizeParam = 5,
    page_cursor: PageCursorParam = None,
) -> dict:
    """Get all profiles in an account.

    You can view and edit a profile in the Klaviyo UI at https://www.klaviyo.com/profile/{PROFILE_ID}
    """
    response = get_klaviyo_client().Profiles.get_profiles(
        page_size=page_size,
        fields_profile=fields,
        sort=sort,
        filter=get_filter_string(filters),
        page_cursor=page_cursor,
    )
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=False, handles_user_generated_content=True)
def get_profile(profile_id: str) -> dict:
    """Get details of the profile with the given profile ID. Includes additional information about their subscriptions.

    You can view and edit a profile in the Klaviyo UI at https://www.klaviyo.com/profile/{PROFILE_ID}
    """
    response = get_klaviyo_client().Profiles.get_profile(
        profile_id, additional_fields_profile=["subscriptions"]
    )
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=True)
def create_profile(profile_data: Profile) -> dict:
    """Create a new profile. Must include either email, phone_number, or external_id.

    You can view and edit a profile in the Klaviyo UI at https://www.klaviyo.com/profile/{PROFILE_ID}
    """
    body = {
        "data": {
            "type": "profile",
            "attributes": profile_data.model_dump(exclude_none=True),
        }
    }
    response = get_klaviyo_client().Profiles.create_profile(body)
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=True, handles_user_generated_content=True)
def update_profile(
    profile_id: str,
    profile_update_data: ProfileUpdate,
    patch_properties: Annotated[
        ProfilePatchProperties,
        Field(
            description="Specify one or more patch operations to apply to existing data for custom properties."
        ),
    ] = None,
) -> dict:
    """Update the profile with the given profile ID.

    You can view and edit a profile in the Klaviyo UI at https://www.klaviyo.com/profile/{PROFILE_ID}
    """
    body = {
        "data": {
            "type": "profile",
            "id": profile_id,
            "attributes": profile_update_data.model_dump(exclude_none=True),
        }
    }
    if patch_properties:
        body["data"]["meta"] = {"patch_properties": patch_properties.model_dump()}
    response = get_klaviyo_client().Profiles.update_profile(profile_id, body)
    clean_result(response["data"])
    return response
