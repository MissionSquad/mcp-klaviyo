from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field

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

HTML_PARAM_DESCRIPTION = """
The complete HTML of the template. Should include <html> and <body> tags.
To include an image, first upload the image using the upload_image_from_file or upload_image_from_url tool, then use the returned image URL.
Always include an unsubscribe link. Do this by inserting the template string "{% unsubscribe 'Unsubscribe' %}". You can replace 'Unsubscribe' with custom text.

To add an editable region to the template, ensure the has_editable_regions param is true and add the following:
<td align="center" data-klaviyo-region="true" data-klaviyo-region-width-pixels="600"></td>

To add an editable text block, add the following within that region:
<div class="klaviyo-block klaviyo-text-block">Hello world!</div>

To add an editable image block, add the following within that region:
<div class="klaviyo-block klaviyo-image-block"></div>

To add a universal content block, add the following within that region, replacing block_id with the ID of the universal content block:
<div data-klaviyo-universal-block="block_id">&nbsp;<div>
"""


GetEmailTemplatesFields = Literal[
    "name",
    "editor_type",
    "html",
    "text",
    "amp",
    "created",
    "updated",
]

GetEmailTemplatesFilter = create_filter_models(
    [
        FilterConfig(field="id", operators=["any", "equals"], value_type=str),
        FilterConfig(
            field="name",
            operators=["any", "contains", "equals"],
            value_type=str,
        ),
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
    ]
)

GetEmailTemplatesSort = Literal[
    "id",
    "-id",
    "name",
    "-name",
    "created",
    "-created",
    "updated",
    "-updated",
]


@mcp_tool(has_writes=True)
def create_email_template(
    name: Annotated[str, Field(description="The name of the template")],
    html: Annotated[str, Field(description=HTML_PARAM_DESCRIPTION)],
    has_editable_regions: Annotated[
        bool,
        Field(
            description="Whether the template HTML contains editable regions. Should be false unless they explicitly request an editable/drag-and-drop/hybrid template."
        ),
    ] = False,
) -> dict:
    """Create a new email template from the given HTML. Returns the ID of the template.

    You can view and edit a template in the Klaviyo UI at https://www.klaviyo.com/email-editor/{TEMPLATE_ID}/edit."""
    body = {
        "data": {
            "type": "template",
            "attributes": {
                "name": name,
                "editor_type": "USER_DRAGGABLE" if has_editable_regions else "CODE",
                "html": html,
            },
        }
    }
    response = get_klaviyo_client().Templates.create_template(body)
    template_id = response["data"]["id"]
    return {
        "id": template_id,
    }


@mcp_tool(has_writes=False)
def get_email_template(
    template_id: Annotated[str, Field(description="The ID of the template return")],
) -> dict:
    """Get an email template with the given data. Returns attributes including the html or amp.

    You can view and edit a template in the Klaviyo UI at https://www.klaviyo.com/email-editor/{TEMPLATE_ID}/edit."""
    response = get_klaviyo_client().Templates.get_template(template_id)
    clean_result(response["data"])
    return response["data"]


@mcp_tool(has_writes=False)
def get_email_templates(
    fields: FieldsParam[GetEmailTemplatesFields] = None,
    filters: FilterParam[GetEmailTemplatesFilter] = None,
    sort: SortParam[GetEmailTemplatesSort] = None,
    page_cursor: PageCursorParam = None,
) -> dict:
    """Returns some or all email templates in the account based on filters.

    Use this tool to discover available templates when the user wants to clone an existing campaign, browse templates, or identify a template by name. Results are paginated.

    You can view and edit a template in the Klaviyo UI at https://www.klaviyo.com/email-editor/{TEMPLATE_ID}/edit."""
    response = get_klaviyo_client().Templates.get_templates(
        fields_template=fields,
        filter=get_filter_string(filters),
        sort=sort,
        page_cursor=page_cursor,
    )
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=True)
def clone_email_template(
    template_id: Annotated[
        str, Field(description="The ID of the template to clone.")
    ],
    name: Annotated[
        str,
        Field(description="The name for the new cloned template."),
    ] = None,
) -> dict:
    """Clones an existing email template into a new template. Returns the ID of the new template.

    You can view and edit the new template in the Klaviyo UI at https://www.klaviyo.com/email-editor/{TEMPLATE_ID}/edit."""
    attributes = {}
    if name is not None:
        attributes["name"] = name
    body = {
        "data": {
            "type": "template",
            "id": template_id,
            "attributes": attributes,
        }
    }
    response = get_klaviyo_client().Templates.clone_template(body)
    new_template_id = response["data"]["id"]
    return {"id": new_template_id}
