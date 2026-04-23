import json
from types import SimpleNamespace
from typing import Annotated, Any, Literal

from pydantic import Field

from klaviyo_mcp_server.utils.param_types import PageCursorParam
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
    Any,
    Field(
        description=(
            "Optional fields to return. Prefer a single string or an array of strings. "
            "Common values are `name`, `definition`, `created`, `updated`, "
            "`screenshot_status`, `screenshot_url`, and `definition.data.content` when you only "
            "need the reusable text or HTML content."
        )
    ),
]

UNIVERSAL_CONTENT_FIELD_VALUES = {
    "name",
    "definition",
    "created",
    "updated",
    "screenshot_status",
    "screenshot_url",
    "definition.data.content",
}

UNIVERSAL_CONTENT_SORT_VALUES = {
    "id",
    "-id",
    "name",
    "-name",
    "created",
    "-created",
    "updated",
    "-updated",
}

UNIVERSAL_CONTENT_ERROR_EXAMPLES = {
    "basic_name_search": {"name": "Header Promo"},
    "block_type_search": {"block_type": "html"},
    "combined_search": {
        "name": "Footer",
        "block_type": "text",
        "fields": ["name", "definition.data.content"],
    },
}


def _error_response(message: str, **details: Any) -> dict:
    response = {
        "ok": False,
        "error": message,
    }
    response.update(details)
    return response


def _require_update_fields(name: str | None, definition: Any) -> dict | None:
    if name is None and definition is None:
        return _error_response(
            "At least one of `name` or `definition` must be provided when updating universal content.",
            example={
                "universal_content_id": "uc_123",
                "name": "Updated Header Promo",
            },
        )
    return None


def _require_non_empty_string(value: str | None, field_name: str, example: dict | None = None) -> dict | None:
    if value is not None:
        return None
    payload: dict[str, Any] = {}
    if example is not None:
        payload["example"] = example
    return _error_response(f"`{field_name}` is required.", **payload)


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


def _coerce_string(value: Any, field_name: str) -> tuple[str | None, dict | None]:
    if value is None:
        return None, None
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized, None
        return None, None
    return None, _error_response(
        f"`{field_name}` must be a string when provided.",
        received_type=type(value).__name__,
    )


def _coerce_string_list(
    value: Any,
    field_name: str,
    allowed_values: set[str] | None = None,
) -> tuple[list[str] | None, dict | None]:
    if value is None:
        return None, None

    raw_items: list[Any]
    if isinstance(value, str):
        raw_items = [value]
    elif isinstance(value, list):
        raw_items = value
    else:
        return None, _error_response(
            f"`{field_name}` must be a string or an array of strings.",
            received_type=type(value).__name__,
        )

    items: list[str] = []
    invalid_items: list[Any] = []
    for item in raw_items:
        if not isinstance(item, str):
            invalid_items.append(item)
            continue
        normalized = item.strip()
        if not normalized:
            continue
        items.append(normalized)

    if invalid_items:
        return None, _error_response(
            f"`{field_name}` must contain only strings.",
            invalid_items=invalid_items,
        )

    if allowed_values is not None:
        invalid_values = [item for item in items if item not in allowed_values]
        if invalid_values:
            return None, _error_response(
                f"`{field_name}` contains unsupported values.",
                invalid_values=invalid_values,
                allowed_values=sorted(allowed_values),
            )

    return items or None, None


def _coerce_page_size(value: Any) -> tuple[int | None, dict | None]:
    if value is None or value == "":
        return None, None
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None, None
        if not stripped.isdigit():
            return None, _error_response(
                "`page_size` must be an integer between 1 and 100.",
                received=value,
            )
        parsed = int(stripped)
    else:
        return None, _error_response(
            "`page_size` must be an integer between 1 and 100.",
            received_type=type(value).__name__,
        )

    if parsed < 1 or parsed > 100:
        return None, _error_response(
            "`page_size` must be between 1 and 100.",
            received=parsed,
        )
    return parsed, None


def _coerce_definition(definition: Any, field_name: str) -> tuple[dict[str, Any] | None, dict | None]:
    if definition is None:
        return None, None
    if isinstance(definition, dict):
        return definition, None
    if isinstance(definition, str):
        stripped = definition.strip()
        if not stripped:
            return None, _error_response(f"`{field_name}` cannot be empty when provided.")
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            return None, _error_response(
                f"`{field_name}` must be a JSON object or a parsed object.",
                parse_error=str(exc),
            )
        if not isinstance(parsed, dict):
            return None, _error_response(
                f"`{field_name}` JSON must decode to an object.",
                decoded_type=type(parsed).__name__,
            )
        return parsed, None
    return None, _error_response(
        f"`{field_name}` must be a JSON object or a JSON string representing an object.",
        received_type=type(definition).__name__,
    )


def _coerce_legacy_filters(filters: Any) -> tuple[list[dict[str, Any]] | None, dict | None]:
    if filters is None:
        return None, None
    if isinstance(filters, dict):
        filter_items = [filters]
    elif isinstance(filters, list):
        filter_items = filters
    else:
        return None, _error_response(
            "`filters` must be an object or an array of objects when provided.",
            received_type=type(filters).__name__,
            example={"filters": [{"field": "name", "operator": "any", "value": ["Header Promo"]}]},
            simpler_examples=UNIVERSAL_CONTENT_ERROR_EXAMPLES,
        )

    normalized: list[dict[str, Any]] = []
    for item in filter_items:
        if not isinstance(item, dict):
            return None, _error_response(
                "`filters` must contain only objects.",
                invalid_item=item,
                simpler_examples=UNIVERSAL_CONTENT_ERROR_EXAMPLES,
            )
        field = item.get("field")
        operator = item.get("operator")
        value = item.get("value")
        if not isinstance(field, str) or not isinstance(operator, str):
            return None, _error_response(
                "Each filter object must include string `field` and `operator` values.",
                invalid_filter=item,
                simpler_examples=UNIVERSAL_CONTENT_ERROR_EXAMPLES,
            )
        normalized.append(
            {
                "field": field.strip(),
                "operator": operator.strip(),
                "value": value,
            }
        )
    return normalized or None, None


def _build_discovery_filters(
    name: str | None,
    block_type: str | None,
    content_type: str | None,
    legacy_filters: list[dict[str, Any]] | None,
) -> list[Any] | None:
    filters: list[dict[str, Any]] = []
    if legacy_filters:
        filters.extend(legacy_filters)
    if name:
        filters.append({"field": "name", "operator": "any", "value": [name]})
    if block_type:
        filters.append({"field": "definition.type", "operator": "equals", "value": block_type})
    if content_type:
        filters.append(
            {
                "field": "definition.content_type",
                "operator": "equals",
                "value": content_type,
            }
        )
    if not filters:
        return None
    return [SimpleNamespace(**item) for item in filters]


@mcp_tool(has_writes=False)
def get_universal_content_blocks(
    name: Annotated[
        Any,
        Field(
            description=(
                "Optional friendly search by block name. Prefer this over advanced `filters` "
                "when you want to find a reusable block by name."
            )
        ),
    ] = None,
    block_type: Annotated[
        Any,
        Field(
            description=(
                "Optional block type filter. Use values such as `text`, `html`, `image`, "
                "`button`, `spacer`, `horizontal_rule`, or `drop_shadow`."
            )
        ),
    ] = None,
    type: Annotated[
        Any,
        Field(
            description=(
                "Alias for `block_type`. Use values such as `text`, `html`, or `image` if that "
                "is easier for your client or model to produce."
            )
        ),
    ] = None,
    content_type: Annotated[
        Any,
        Field(
            description=(
                "Optional content type filter mapped to `definition.content_type` for advanced "
                "searches."
            )
        ),
    ] = None,
    fields: UniversalContentFieldsParam = None,
    filters: Annotated[
        Any,
        Field(
            description=(
                "Optional advanced filter object or array of filter objects. Prefer top-level "
                "`name`, `block_type`, and `content_type` for LLM calls because they are easier "
                "to use correctly."
            )
        ),
    ] = None,
    sort: Annotated[
        Any,
        Field(
            description=(
                "Optional sort value such as `name`, `-name`, `created`, `-created`, `updated`, "
                "or `-updated`."
            )
        ),
    ] = None,
    page_cursor: PageCursorParam = None,
    page_size: Annotated[
        Any,
        Field(description="Optional page size between 1 and 100."),
    ] = None,
) -> dict:
    """Returns some or all universal content blocks in the account based on filters.

    Use this tool to discover reusable content blocks before embedding them into templates or updating them. Results are paginated.

    Prefer the top-level `name`, `block_type`, `type`, and `content_type` parameters for normal LLM calls. Use `filters` only for advanced exact filtering.

    Filter by `block_type` or `type` to find a specific block type such as `text`, `html`, or `image`. Use sparse fields when you only need part of the block, for example `definition.data.content`.

    You can view and edit a universal content block in the Klaviyo UI from the email template editor once it is attached to a template."""
    name_value, error = _coerce_string(name, "name")
    if error:
        return error
    block_type_value, error = _coerce_string(block_type, "block_type")
    if error:
        return error
    type_value, error = _coerce_string(type, "type")
    if error:
        return error
    if block_type_value and type_value and block_type_value != type_value:
        return _error_response(
            "`block_type` and `type` were both provided but do not match.",
            block_type=block_type_value,
            type=type_value,
        )
    if block_type_value is None:
        block_type_value = type_value
    content_type_value, error = _coerce_string(content_type, "content_type")
    if error:
        return error
    field_values, error = _coerce_string_list(
        fields, "fields", UNIVERSAL_CONTENT_FIELD_VALUES
    )
    if error:
        return error
    sort_value, error = _coerce_string(sort, "sort")
    if error:
        return error
    if sort_value is not None and sort_value not in UNIVERSAL_CONTENT_SORT_VALUES:
        return _error_response(
            "`sort` contains an unsupported value.",
            received=sort_value,
            allowed_values=sorted(UNIVERSAL_CONTENT_SORT_VALUES),
        )
    page_size_value, error = _coerce_page_size(page_size)
    if error:
        return error
    legacy_filters, error = _coerce_legacy_filters(filters)
    if error:
        return error

    combined_filters = _build_discovery_filters(
        name_value, block_type_value, content_type_value, legacy_filters
    )

    response = get_klaviyo_client().Templates.get_all_universal_content(
        fields_template_universal_content=field_values,
        filter=get_filter_string(combined_filters),
        sort=sort_value,
        page_cursor=page_cursor,
        page_size=page_size_value,
    )
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=False)
def get_universal_content_block(
    universal_content_id: Annotated[
        Any, Field(description="The ID of the universal content block to retrieve.")
    ] = None,
    fields: UniversalContentFieldsParam = None,
) -> dict:
    """Get a universal content block with the given ID.

    Use this tool before updating a block so you can preserve the full existing `definition`. If you only need part of the block, request sparse fields such as `definition.data.content`."""
    universal_content_id_value, error = _coerce_string(
        universal_content_id, "universal_content_id"
    )
    if error:
        return error
    error = _require_non_empty_string(
        universal_content_id_value,
        "universal_content_id",
        {"universal_content_id": "uc_123"},
    )
    if error:
        return error

    field_values, error = _coerce_string_list(
        fields, "fields", UNIVERSAL_CONTENT_FIELD_VALUES
    )
    if error:
        return error

    response = get_klaviyo_client().Templates.get_universal_content(
        universal_content_id_value,
        fields_template_universal_content=field_values,
    )
    clean_result(response["data"])
    return response["data"]


@mcp_tool(has_writes=True)
def create_universal_content_block(
    name: Annotated[
        Any, Field(description="The name for the new universal content block.")
    ] = None,
    definition: Annotated[
        Any,
        Field(
            description=(
                "Complete Klaviyo universal content definition JSON. This object is passed "
                "through to Klaviyo as-is. Currently documented create/update block types are "
                "`button`, `drop_shadow`, `horizontal_rule`, `html`, `image`, `spacer`, and `text`. "
                "For HTML blocks, do not include `styles`."
            )
        ),
    ] = None,
) -> dict:
    """Create a new universal content block. Returns the ID of the new block.

    Use this tool when the user wants reusable content that can be embedded into multiple templates. The `definition` object is passed through to Klaviyo as-is, so it must be a complete valid universal content definition for the target block type.

    After creation, embed the returned ID in template HTML using:
    <div data-klaviyo-universal-block="BLOCK_ID">&nbsp;<div>"""
    name_value, error = _coerce_string(name, "name")
    if error:
        return error
    error = _require_non_empty_string(
        name_value,
        "name",
        {
            "name": "Header Promo",
            "definition": {"type": "html", "data": {"content": "<div>Promo</div>"}},
        },
    )
    if error:
        return error

    definition_value, error = _coerce_definition(definition, "definition")
    if error:
        return error
    if definition_value is None:
        return _error_response(
            "`definition` is required.",
            example={
                "name": "Header Promo",
                "definition": {"type": "html", "data": {"content": "<div>Promo</div>"}},
            },
        )

    body = {
        "data": {
            "type": "template-universal-content",
            "attributes": {
                "name": name_value,
                "definition": definition_value,
            },
        }
    }
    response = get_klaviyo_client().Templates.create_universal_content(body)
    return {"id": response["data"]["id"]}


@mcp_tool(has_writes=True)
def update_universal_content_block(
    universal_content_id: Annotated[
        Any, Field(description="The ID of the universal content block to update.")
    ] = None,
    name: Annotated[
        Any,
        Field(
            description=(
                "Optional new name for this universal content block. Provide this and/or "
                "`definition`."
            )
        ),
    ] = None,
    definition: Annotated[
        Any,
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
    universal_content_id_value, error = _coerce_string(
        universal_content_id, "universal_content_id"
    )
    if error:
        return error
    error = _require_non_empty_string(
        universal_content_id_value,
        "universal_content_id",
        {"universal_content_id": "uc_123", "name": "Updated Header Promo"},
    )
    if error:
        return error

    name_value, error = _coerce_string(name, "name")
    if error:
        return error

    error = _require_update_fields(name_value, definition)
    if error:
        return error

    definition_value, error = _coerce_definition(definition, "definition")
    if error:
        return error

    attributes: dict[str, Any] = {}
    if name_value is not None:
        attributes["name"] = name_value
    if definition_value is not None:
        attributes["definition"] = definition_value

    body = {
        "data": {
            "type": "template-universal-content",
            "id": universal_content_id_value,
            "attributes": attributes,
        }
    }
    response = get_klaviyo_client().Templates.update_universal_content(
        universal_content_id_value, body
    )
    clean_result(response["data"])
    return response["data"]


@mcp_tool(has_writes=True)
def delete_universal_content_block(
    universal_content_id: Annotated[
        Any, Field(description="The ID of the universal content block to delete.")
    ] = None,
) -> dict:
    """Delete a universal content block with the given ID.

    Warning: deleting a universal content block affects every template that uses it. Templates will no longer reference the universal block, although they will generally remain visually unchanged because Klaviyo converts the block into a regular non-universal block."""
    universal_content_id_value, error = _coerce_string(
        universal_content_id, "universal_content_id"
    )
    if error:
        return error
    error = _require_non_empty_string(
        universal_content_id_value,
        "universal_content_id",
        {"universal_content_id": "uc_123"},
    )
    if error:
        return error

    get_klaviyo_client().Templates.delete_universal_content(universal_content_id_value)
    return {"id": universal_content_id_value, "deleted": True}


@mcp_tool(has_writes=False)
def get_universal_content_block_html(
    universal_content_id: Annotated[
        Any, Field(description="The ID of the universal content block to inspect.")
    ] = None,
) -> dict:
    """Get the main content payload for a universal content block.

    Use this when the user only needs the block's reusable text or HTML and does not need the full definition object."""
    universal_content_id_value, error = _coerce_string(
        universal_content_id, "universal_content_id"
    )
    if error:
        return error
    error = _require_non_empty_string(
        universal_content_id_value,
        "universal_content_id",
        {"universal_content_id": "uc_123"},
    )
    if error:
        return error

    response = get_klaviyo_client().Templates.get_universal_content(
        universal_content_id_value,
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
