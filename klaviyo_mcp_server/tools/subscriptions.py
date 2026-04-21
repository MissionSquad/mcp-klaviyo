from typing import Annotated, Literal

from pydantic import Field

from klaviyo_mcp_server.utils.utils import get_klaviyo_client
from klaviyo_mcp_server.utils.tool_decorator import mcp_tool


@mcp_tool(has_writes=True)
def subscribe_profile_to_marketing(
    channels: Annotated[
        set[Literal["email", "sms"]],
        Field(description="The channels to subscribe the profile to."),
    ],
    list_id: Annotated[
        str,
        Field(
            description="The ID of the list to subscribe the profile to if provided."
        ),
    ] = "",
    profile_id: Annotated[
        str,
        Field(
            description="The ID of the profile to subscribe if the profile already exists and has an ID."
        ),
    ] = "",
    email_address: Annotated[
        str,
        Field(
            description="The email address of the profile to subscribe. Required if email channel is included.",
        ),
    ] = "",
    phone_number: Annotated[
        str,
        Field(
            description="The phone number of the profile to subscribe. Required if sms channel is included.",
        ),
    ] = "",
) -> str:
    """Subscribe a profile to marketing for a given channel. Returns "Success" if successful."""

    list_relationship = {}
    if list_id != "":
        list_relationship = {
            "relationships": {
                "list": {
                    "data": {
                        "type": "list",
                        "id": list_id,
                    },
                },
            }
        }

    body = {
        "data": {
            "type": "profile-subscription-bulk-create-job",
            "attributes": {
                "profiles": {
                    "data": [
                        {
                            "type": "profile",
                            "attributes": {
                                "id": profile_id if profile_id else None,
                                "subscriptions": {
                                    channel: {"marketing": {"consent": "SUBSCRIBED"}}
                                    for channel in channels
                                },
                                "email": email_address if email_address else None,
                                "phone_number": phone_number if phone_number else None,
                            },
                        }
                    ]
                },
                "historical_import": False,
            },
            **list_relationship,
        }
    }

    get_klaviyo_client().Profiles.subscribe_profiles(
        subscription_create_job_create_query=body
    )

    return "Success"


@mcp_tool(has_writes=True)
def unsubscribe_profile_from_marketing(
    channels: Annotated[
        set[Literal["email", "sms"]],
        Field(description="The channels to unsubscribe the profile from."),
    ],
    list_id: Annotated[
        str,
        Field(
            description="The ID of the list to unsubscribe the profile from if provided."
        ),
    ] = "",
    email_address: Annotated[
        str,
        Field(
            description="The email address of the profile to unsubscribe. Required if email channel is included.",
        ),
    ] = "",
    phone_number: Annotated[
        str,
        Field(
            description="The phone number of the profile to unsubscribe. Required if sms channel is included.",
        ),
    ] = "",
) -> str:
    """Unsubscribe a profile from marketing for a given channel. Returns "Success" if successful."""

    list_relationship = {}
    if list_id != "":
        list_relationship = {
            "relationships": {
                "list": {
                    "data": {
                        "type": "list",
                        "id": list_id,
                    },
                },
            }
        }

    body = {
        "data": {
            "type": "profile-subscription-bulk-delete-job",
            "attributes": {
                "profiles": {
                    "data": [
                        {
                            "type": "profile",
                            "attributes": {
                                "subscriptions": {
                                    channel: {"marketing": {"consent": "UNSUBSCRIBED"}}
                                    for channel in channels
                                },
                                "email": email_address if email_address else None,
                                "phone_number": phone_number if phone_number else None,
                            },
                        }
                    ]
                },
            },
            **list_relationship,
        }
    }

    get_klaviyo_client().Profiles.unsubscribe_profiles(
        subscription_delete_job_create_query=body
    )

    return "Success"
