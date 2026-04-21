from typing import Literal

from klaviyo_mcp_server.utils.utils import (
    clean_result,
    get_klaviyo_client,
    get_filter_string,
)
from klaviyo_mcp_server.utils.param_types import (
    FieldsParam,
    FilterParam,
    SortParam,
    PageCursorParam,
    create_filter_models,
    FilterConfig,
)
from klaviyo_mcp_server.utils.tool_decorator import mcp_tool

GetCatalogItemsFields = Literal[
    "external_id",
    "title",
    "description",
    "price",
    "url",
    "image_full_url",
    "image_thumbnail_url",
    "images",
    "custom_metadata",
    "published",
    "created",
    "updated",
]

GetCatalogItemsFilter = create_filter_models(
    [
        FilterConfig(field="ids", operators=["any"], value_type=str),
        FilterConfig(field="category.id", operators=["equals"], value_type=str),
        FilterConfig(field="title", operators=["contains"], value_type=str),
        FilterConfig(field="published", operators=["equals"], value_type=bool),
    ]
)

GetCatalogsSort = Literal["created", "-created"]


@mcp_tool(has_writes=False)
def get_catalog_items(
    catalog_item_fields: FieldsParam[GetCatalogItemsFields],
    filters: FilterParam[GetCatalogItemsFilter] = None,
    sort: SortParam[GetCatalogsSort] = None,
    page_cursor: PageCursorParam = None,
) -> dict:
    """
    Get all catalog items in an account. (Also known as products)
    """

    response = get_klaviyo_client().Catalogs.get_catalog_items(
        fields_catalog_item=catalog_item_fields,
        filter=get_filter_string(filters),
        include=["variants"],
        sort=sort,
        page_cursor=page_cursor,
    )

    clean_result(response["data"])
    return response
