import os
from datetime import datetime
from typing import Any

from klaviyo_api import KlaviyoAPI
from openapi_client.api_arg_options import USE_DICTIONARY_FOR_RESPONSE_DATA
from fastmcp.server.dependencies import get_context
from klaviyo_mcp_server.version import __version__

USER_AGENT_HEADER = "klaviyo-mcp"


class ModelData:
    """Holds data about an AI model using the MCP server."""

    model: str | None = None


current_model_data = ModelData()
"""Data about the AI model currently being used."""


def get_klaviyo_client() -> KlaviyoAPI:
    private_key = os.getenv("PRIVATE_API_KEY")
    if not private_key:
        raise ValueError(
            "Please set PRIVATE_API_KEY environment variable to your Klaviyo private API key"
        )
    client = KlaviyoAPI(private_key, options={USE_DICTIONARY_FOR_RESPONSE_DATA: True})

    try:
        # get_context will return a RuntimeError if the context is not available for some reason
        ctx = get_context()
        client_info = ctx.session._client_params.clientInfo
    except RuntimeError:
        client_info = None

    user_agent = f"{USER_AGENT_HEADER}/{__version__}"
    if client_info and client_info.name and client_info.version:
        user_agent += f" {client_info.name}/{client_info.version}"

    if current_model_data.model:
        user_agent += f" {current_model_data.model}"

    client.api_client.user_agent = user_agent
    return client


def clean_result(data: dict | list):
    if isinstance(data, list):
        for d in data:
            clean_result(d)
    else:
        data.pop("relationships", None)
        data.pop("links", None)


def get_filter_string(filters: list[Any] | None) -> str | None:
    if not filters:
        return None

    formatted_filters = []
    for filter in filters:
        if hasattr(filter, "value"):
            value = _get_filter_value_string(filter.value)
            formatted_filters.append(f"{filter.operator}({filter.field},{value})")
        else:
            # unary operator
            formatted_filters.append(f"{filter.operator}({filter.field})")
    return ",".join(formatted_filters)


def _get_filter_value_string(value: Any) -> str:
    """Transforms a value into its string representation for the filter query param."""
    if isinstance(value, list):
        return f"[{','.join([_get_filter_value_string(v) for v in value])}]"
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bool):
        return str(value).lower()
    return repr(value)
