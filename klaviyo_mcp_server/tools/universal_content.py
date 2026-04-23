from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import Field

from klaviyo_mcp_server.utils.param_types import (
    FilterConfig,
    FilterParam,
    PageCursorParam,
    PageSizeParam,
    SortParam,
    create_filter_models,
)
from klaviyo_mcp_server.utils.tool_decorator import mcp_tool
from klaviyo_mcp_server.utils.utils import clean_result, get_filter_string, get_klaviyo_client

UniversalContentFields = Literal[
    "name",
    "definition",
    "created",
    "updated",
    "screenshot_status",
    "screenshot_url",
    "definition.data.content",
]

UniversalContentFieldsParam = Annotated[
    list[UniversalContentFields],
    Field(
        description=(
            "Fields to return. Common values are `name`, `definition`, `created`, "
            "`updated`, `screenshot_status`, `screenshot_url`, and "
            "`definition.data.content` when you only need the reusable text or HTML content."
        )
    ),
]

GetUniversalContentFilter = create_filter_models(
    [
        FilterConfig(field="id", operators=["any", "equals"], value_type=str),
        FilterConfig(field="name", operators=["any", "equals"], value_type=str),
        FilterConfig(
            field="created",
            operators=[
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
                "greater-or-equal",
                "greater-than",
                "less-or-equal",
                "less-than",
            ],
            value_type=datetime,
        ),
        FilterConfig(
            field="definition.content_type",
            operators=["equals"],
            value_type=str,
        ),
        FilterConfig(
            field="definition.type",
            operators=["equals"],
            value_type=str,
        ),
    ]
)

GetUniversalContentSort = Literal[
    "id",
    "-id",
    "name",
    "-name",
    "created",
    "-created",
    "updated",
    "-updated",
]


def _require_update_fields(name: str | None, definition: dict[str, Any] | None) -> None:
    if name is None and definition is None:
        raise ValueError(
            "At least one of `name` or `definition` must be provided when updating universal content."
        )


def _extract_definition_type(definition: Any) -> str | None:
    if isinstance(definition, dict):
        definition_type = definition.get("type")
        if isinstance(definition_type, str):
            return definition_type
    return None


def _extract_definition_content(definition: Any) -> str | None:
    if isinstance(definition, dict):
        data = definition.get("data")
        if isinstance(data, dict):
            content = data.get("content")
            if isinstance(content, str):
                return content
    return None


@mcp_tool(has_writes=False)
def get_universal_content_blocks(
    fields: UniversalContentFieldsParam = None,
    filters: FilterParam[GetUniversalContentFilter] = None,
    sort: SortParam[GetUniversalContentSort] = None,
    page_cursor: PageCursorParam = None,
    page_size: PageSizeParam = None,
) -> dict:
    """Returns some or all universal content blocks in the account based on filters.

    Use this tool to discover reusable content blocks before embedding them into templates or updating them. Results are paginated.

    Filter by `definition.type` to find a specific block type such as `text`, `html`, or `image`. Use sparse fields when you only need part of the block, for example `definition.data.content`.

    You can view and edit a universal content block in the Klaviyo UI from the email template editor once it is attached to a template."""
    response = get_klaviyo_client().Templates.get_all_universal_content(
        fields_template_universal_content=fields,
        filter=get_filter_string(filters),
        sort=sort,
        page_cursor=page_cursor,
        page_size=page_size,
    )
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=False)
def get_universal_content_block(
    universal_content_id: Annotated[
        str, Field(description="The ID of the universal content block to retrieve.")
    ],
    fields: UniversalContentFieldsParam = None,
) -> dict:
    """Get a universal content block with the given ID.

    Use this tool before updating a block so you can preserve the full existing `definition`. If you only need part of the block, request sparse fields such as `definition.data.content`."""
    response = get_klaviyo_client().Templates.get_universal_content(
        universal_content_id,
        fields_template_universal_content=fields,
    )
    clean_result(response["data"])
    return response["data"]


@mcp_tool(has_writes=True)
def create_universal_content_block(
    name: Annotated[
        str, Field(description="The name for the new universal content block.")
    ],
    definition: Annotated[
        dict[str, Any],
        Field(
            description=(
                "Complete Klaviyo universal content definition JSON. This object is passed "
                "through to Klaviyo as-is. Currently documented create/update block types are "
                "`button`, `drop_shadow`, `horizontal_rule`, `html`, `image`, `spacer`, and `text`. "
                "For HTML blocks, do not include `styles`."
            )
        ),
    ],
) -> dict:
    """Create a new universal content block. Returns the ID of the new block.

    Use this tool when the user wants reusable content that can be embedded into multiple templates. The `definition` object is passed through to Klaviyo as-is, so it must be a complete valid universal content definition for the target block type.

    After creation, embed the returned ID in template HTML using:
    <div data-klaviyo-universal-block="BLOCK_ID">&nbsp;<div>"""
    body = {
        "data": {
            "type": "template-universal-content",
            "attributes": {
                "name": name,
                "definition": definition,
            },
        }
    }
    response = get_klaviyo_client().Templates.create_universal_content(body)
    return {"id": response["data"]["id"]}


@mcp_tool(has_writes=True)
def update_universal_content_block(
    universal_content_id: Annotated[
        str, Field(description="The ID of the universal content block to update.")
    ],
    name: Annotated[
        str,
        Field(
            description=(
                "Optional new name for this universal content block. Provide this and/or "
                "`definition`."
            )
        ),
    ] = None,
    definition: Annotated[
        dict[str, Any],
        Field(
            description=(
                "Optional complete replacement definition JSON. If supplied, this fully "
                "replaces the existing definition rather than merging nested fields. "
                "Read the block first if you need to preserve existing styles or display options."
            )
        ),
    ] = None,
) -> dict:
    """Update an existing universal content block.

    Warning: updating a universal content block changes every template that uses it.

    If you provide `definition`, it fully replaces the stored definition rather than merging nested fields. Read the block first with `get_universal_content_block` and send the full intended `definition` if you need to preserve existing styles or display options."""
    _require_update_fields(name, definition)
    attributes: dict[str, Any] = {}
    if name is not None:
        attributes["name"] = name
    if definition is not None:
        attributes["definition"] = definition

    body = {
        "data": {
            "type": "template-universal-content",
            "id": universal_content_id,
            "attributes": attributes,
        }
    }
    response = get_klaviyo_client().Templates.update_universal_content(
        universal_content_id, body
    )
    clean_result(response["data"])
    return response["data"]


@mcp_tool(has_writes=True)
def delete_universal_content_block(
    universal_content_id: Annotated[
        str, Field(description="The ID of the universal content block to delete.")
    ],
) -> dict:
    """Delete a universal content block with the given ID.

    Warning: deleting a universal content block affects every template that uses it. Templates will no longer reference the universal block, although they will generally remain visually unchanged because Klaviyo converts the block into a regular non-universal block."""
    get_klaviyo_client().Templates.delete_universal_content(universal_content_id)
    return {"id": universal_content_id, "deleted": True}


@mcp_tool(has_writes=False)
def get_universal_content_block_html(
    universal_content_id: Annotated[
        str, Field(description="The ID of the universal content block to inspect.")
    ],
) -> dict:
    """Get the main content payload for a universal content block.

    Use this when the user only needs the block's reusable text or HTML and does not need the full definition object."""
    response = get_klaviyo_client().Templates.get_universal_content(
        universal_content_id,
        fields_template_universal_content=["name", "definition"],
    )
    clean_result(response["data"])
    attributes = response["data"].get("attributes", {})
    definition = attributes.get("definition")
    return {
        "id": response["data"]["id"],
        "name": attributes.get("name"),
        "type": _extract_definition_type(definition),
        "content": _extract_definition_content(definition),
    }
