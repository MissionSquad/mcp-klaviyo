from typing import Annotated

from pydantic import Field

from klaviyo_mcp_server.utils.utils import clean_result, get_klaviyo_client
from klaviyo_mcp_server.utils.tool_decorator import mcp_tool


@mcp_tool(has_writes=True)
def upload_image_from_file(
    file_path: Annotated[
        str, Field(description="The absolute file path of the image file to upload")
    ],
    name: Annotated[
        str,
        Field(
            description="A name for the image. Defaults to the filename if None is passed."
        ),
    ] = None,
) -> dict:
    """Upload an image from a file. If you want to upload an image from an existing URL or a data URI, use the
    upload_image_from_url tool instead."""
    response = get_klaviyo_client().Images.upload_image_from_file(file_path, name)
    clean_result(response["data"])
    return response


@mcp_tool(has_writes=True)
def upload_image_from_url(
    image_url: Annotated[str, Field(description="The URL of the image to upload")],
    name: Annotated[
        str,
        Field(
            description="A name for the image. Defaults to the filename if None is passed."
        ),
    ] = None,
) -> dict:
    """Upload an image from a URL or data URI. If you want to upload an image from a file, use the
    upload_image_from_file tool instead."""
    body = {
        "data": {
            "type": "image",
            "attributes": {"import_from_url": image_url, "name": name},
        }
    }
    response = get_klaviyo_client().Images.upload_image_from_url(body)
    clean_result(response["data"])
    return response
