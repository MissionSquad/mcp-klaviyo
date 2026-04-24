from datetime import datetime
from types import SimpleNamespace
from typing import Annotated, Literal

from pydantic import Field

from klaviyo_mcp_server.models.campaigns import (
    CampaignMessage,
    SendStrategy,
    TrackingOptions,
)
from klaviyo_mcp_server.utils.add_related_data import add_related_data
from klaviyo_mcp_server.utils.param_types import (
    FieldsParam,
    FilterConfig,
    FilterParam,
    PageCursorParam,
    UnionWrapper,
    create_filter_models,
)
from klaviyo_mcp_server.utils.tool_decorator import mcp_tool
from klaviyo_mcp_server.utils.utils import (
    clean_result,
    get_filter_string,
    get_klaviyo_client,
)

GetCampaignsFields = Literal[
    "name",
    "status",
    "archived",
    "audiences",
    "audiences.included",
    "audiences.excluded",
    "send_options",
    "send_options.use_smart_sending",
    "tracking_options",
    "tracking_options.add_tracking_params",
    "tracking_options.custom_tracking_params",
    "tracking_options.is_tracking_clicks",
    "tracking_options.is_tracking_opens",
    "send_strategy",
    "send_strategy.method",
    "send_strategy.datetime",
    "send_strategy.options",
    "send_strategy.options.is_local",
    "send_strategy.options.send_past_recipients_immediately",
    "send_strategy.throttle_percentage",
    "send_strategy.date",
    "created_at",
    "scheduled_at",
    "updated_at",
    "send_time",
]

GetCampaignsFilter = create_filter_models(
    [
        FilterConfig(field="name", operators=["equals"], value_type=str),
        FilterConfig(field="archived", operators=["equals"], value_type=bool),
        FilterConfig(
            field="created_at",
            operators=[
                "greater-or-equal",
                "greater-than",
                "less-or-equal",
                "less-than",
            ],
            value_type=datetime,
        ),
        FilterConfig(
            field="scheduled_at",
            operators=[
                "greater-or-equal",
                "greater-than",
                "less-or-equal",
                "less-than",
            ],
            value_type=datetime,
        ),
        FilterConfig(
            field="updated_at",
            operators=[
                "greater-or-equal",
                "greater-than",
                "less-or-equal",
                "less-than",
            ],
            value_type=datetime,
        ),
        FilterConfig(
            field="status",
            operators=["any", "equals"],
            value_type=Literal[
                "Scheduled",
                "Sent",
                "Draft",
                "Cancelled",
                "Adding Recipients",
                "Sending",
                "Variations Sent",
                "Sending Segments",
                "Cancelled: Smart Sending",
                "Preparing to send",
                "Cancelled: Account Disabled",
                "Cancelled: No Recipients",
                "Preparing to schedule",
                "Cancelled: Internal Error",
                "Queued without Recipients",
                "Unknown",
            ],
        ),
    ]
)


@mcp_tool(has_writes=False)
def get_campaigns(
    fields: FieldsParam[GetCampaignsFields],
    channel: Annotated[
        Literal["email", "sms", "mobile_push"],
        Field(
            description="Which types of campaigns to return. To get all types of campaigns, call this tool for each channel."
        ),
    ],
    filters: FilterParam[GetCampaignsFilter] = None,
    page_cursor: PageCursorParam = None,
) -> dict:
    """Returns some or all campaigns based on filters. To get performance data, use get_campaign_report.

    You can view and edit a campaign in the Klaviyo UI at https://www.klaviyo.com/campaign/{CAMPAIGN_ID}/wizard
    """

    # channel is a special filter (is it required and there can only be one), so add it manually based on a parameter
    channel_filter = SimpleNamespace(
        field="messages.channel", operator="equals", value=channel
    )
    if not filters:
        filters = []
    filters.append(channel_filter)

    response = get_klaviyo_client().Campaigns.get_campaigns(
        fields_campaign=fields,
        filter=get_filter_string(filters),
        include=["campaign-messages"],
        page_cursor=page_cursor,
    )
    add_related_data(response, "campaign-message", "campaign-messages")
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=False)
def get_campaign(campaign_id: str) -> dict:
    """Returns a specific campaign based on a required id.

    You can view and edit a campaign in the Klaviyo UI at https://www.klaviyo.com/campaign/{CAMPAIGN_ID}/wizard
    """
    response = get_klaviyo_client().Campaigns.get_campaign(
        campaign_id,
        include=["campaign-messages"],
    )
    add_related_data(response, "campaign-message", "campaign-messages")
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=True)
def create_campaign(
    name: Annotated[str, Field(description="The name of the campaign.")],
    campaign_message: Annotated[
        UnionWrapper[CampaignMessage],
        Field(description="The message to send to the campaign."),
    ],
    included_audiences: Annotated[
        list[str],
        Field(
            description="The list IDs or segment IDs to which the campaign should be sent. Use the get_lists and get_segments tools to get the available lists and segments."
        ),
    ],
    excluded_audiences: Annotated[
        list[str],
        Field(
            description="The list or segment IDs to which the campaign should not be sent. Use the get_lists and get_segments tools to get the available lists and segments."
        ),
    ] = None,
    use_smart_sending: Annotated[
        bool,
        Field(
            description="Whether the campaign should use Smart Sending. If true, the campaign will not be sent to profiles that have recently received a message."
        ),
    ] = True,
    tracking_options: Annotated[
        UnionWrapper[TrackingOptions],
        Field(description="The tracking options associated with the campaign"),
    ] = None,
    send_strategy: Annotated[
        UnionWrapper[SendStrategy],
        Field(
            description="The send strategy the campaign will send with. Defaults to 'Immediate' send strategy."
        ),
    ] = None,
) -> dict:
    """
    Creates a new draft campaign.

    For email campaigns, this can be used with the create_email_template tool for template creation and then assign_template_to_campaign_message to assign the template to the email campaign.

    You can view and edit a campaign in the Klaviyo UI at https://www.klaviyo.com/campaign/{CAMPAIGN_ID}/wizard
    """
    body = {
        "data": {
            "type": "campaign",
            "attributes": {
                "name": name,
                "audiences": {
                    "included": included_audiences,
                    "excluded": excluded_audiences or [],
                },
                "send_options": {
                    "use_smart_sending": use_smart_sending,
                },
                "campaign-messages": {
                    "data": [
                        {
                            "type": "campaign-message",
                            "attributes": {
                                "definition": campaign_message.value.model_dump(
                                    exclude_none=True
                                )
                            },
                        }
                    ]
                },
            },
        }
    }
    if send_strategy:
        body["data"]["attributes"]["send_strategy"] = send_strategy.value.model_dump(
            exclude_none=True
        )
    if tracking_options:
        body["data"]["attributes"]["tracking_options"] = (
            tracking_options.value.model_dump(exclude_none=True)
        )
    response = get_klaviyo_client().Campaigns.create_campaign(body)

    clean_result(
        response["data"]["relationships"]
    )  # response needs to include campaign-messages relationship to use in assign template
    return response


@mcp_tool(has_writes=True)
def assign_template_to_campaign_message(
    campaign_message_id: Annotated[
        str,
        Field(
            description="The ID of the email campaign message to assign the template to."
        ),
    ],
    email_template_id: Annotated[
        str,
        Field(
            description="The ID of the email template to assign to the campaign message."
        ),
    ],
) -> dict:
    """
    Assigns an email template to a campaign message.
    This should be used after creating a template with the create_email_template tool and creating an email campaign.
    """
    response = get_klaviyo_client().Campaigns.assign_template_to_campaign_message(
        {
            "data": {
                "type": "campaign-message",
                "id": campaign_message_id,
                "relationships": {
                    "template": {"data": {"type": "template", "id": email_template_id}}
                },
            }
        }
    )
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=False)
def get_messages_for_campaign(
    campaign_id: Annotated[
        str, Field(description="The ID of the campaign whose messages to retrieve.")
    ],
) -> dict:
    """Returns all campaign messages for a given campaign.

    A campaign message is the per-channel content for a campaign (email, SMS, push). For email channels, each message has a template associated with it which can be fetched via get_template_for_campaign_message.

    Use this tool to enumerate campaign messages before fetching their templates or cloning workflows."""
    response = get_klaviyo_client().Campaigns.get_messages_for_campaign(campaign_id)
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=False)
def get_template_for_campaign_message(
    campaign_message_id: Annotated[
        str,
        Field(
            description="The ID of the campaign message whose template to retrieve."
        ),
    ],
) -> dict:
    """Returns the full email template associated with a campaign message.

    This is the inverse of assign_template_to_campaign_message: given a campaign message, retrieve the template it currently renders. Only applicable to email-channel campaign messages. Returns attributes including html or amp.

    You can view and edit a template in the Klaviyo UI at https://www.klaviyo.com/email-editor/{TEMPLATE_ID}/edit."""
    response = get_klaviyo_client().Campaigns.get_template_for_campaign_message(
        campaign_message_id
    )
    clean_result(response["data"])
    return response["data"]


@mcp_tool(has_writes=False)
def get_template_id_for_campaign_message(
    campaign_message_id: Annotated[
        str,
        Field(
            description="The ID of the campaign message whose template ID to retrieve."
        ),
    ],
) -> dict:
    """Returns only the template ID associated with a campaign message.

    Lightweight alternative to get_template_for_campaign_message when only the identifier is needed, e.g. as an input to clone_email_template. Only applicable to email-channel campaign messages."""
    response = get_klaviyo_client().Campaigns.get_template_id_for_campaign_message(
        campaign_message_id
    )
    return {"id": response["data"]["id"]}


@mcp_tool(has_writes=True)
def clone_campaign(
    campaign_id: Annotated[
        str, Field(description="The ID of the campaign to clone.")
    ],
    new_name: Annotated[
        str,
        Field(description="The name for the new cloned campaign."),
    ] = None,
) -> dict:
    """Clones an existing campaign into a new draft campaign. Returns the cloned campaign resource including its relationships to new campaign-messages.

    The clone preserves campaign messages, audiences, tracking options, and send strategy. Templates referenced by campaign messages are also cloned into new non-reusable templates attached to the new campaign messages. The clone is always created as a Draft regardless of the source campaign's status.

    You can view and edit the new campaign in the Klaviyo UI at https://www.klaviyo.com/campaign/{CAMPAIGN_ID}/wizard."""
    attributes = {}
    if new_name is not None:
        attributes["new_name"] = new_name
    body = {
        "data": {
            "type": "campaign",
            "id": campaign_id,
            "attributes": attributes,
        }
    }
    response = get_klaviyo_client().Campaigns.create_campaign_clone(body)
    response["data"].pop("links", None)
    return response
