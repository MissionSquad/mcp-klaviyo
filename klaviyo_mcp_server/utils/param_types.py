import typing
from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field, create_model

from klaviyo_mcp_server.utils.filter_utils import (
    ListOperator,
    SingleOperator,
    UnaryOperator,
    list_only_operators,
    valid_list_operators,
    valid_single_operators,
    valid_unary_operators,
)

T = TypeVar(
    "T"
)  # using old style type parameters, as new style type parameters do not work with the Cursor client

FieldsParam = Annotated[list[T], Field(description="Fields to return.")]
SortParam = Annotated[T, Field(description="What to sort by.")]
PageSizeParam = Annotated[
    int, Field(description="Maximum number of results", ge=1, le=100)
]
PageCursorParam = Annotated[
    str,
    Field(
        description="Only used for pagination. If links.next is null then you've reached the last page of results. Otherwise, pass links.next to this parameter to get the next page."
    ),
]
FilterParam = Annotated[
    list[T],
    Field(description="Filters to apply. To apply no filters, pass any empty list."),
]
IncludeParam = Annotated[
    list[T],
    Field(
        description="Fields indicating additional resources to include in the response. Providing no include values will only return the base resource."
    ),
]


class UnionWrapper(BaseModel, Generic[T]):
    """
    Wrapper for union types that are top-level tool parameters.

    This is needed because Claude Desktop has an issue where if a tool has a top-level union of two Pydantic models,
    it will pass a JSON string instead of an object.
    """

    value: T


class FilterConfig(BaseModel):
    field: str
    operators: list[SingleOperator | ListOperator | UnaryOperator]
    value_type: Any
    description: str | None = None


class BaseFilter(BaseModel):
    field: str
    operator: str
    value: Any


def create_filter_models(configs: list[FilterConfig]):
    models = []
    for config in configs:
        single_operators = [
            op for op in config.operators if op in valid_single_operators
        ]
        if single_operators:
            model = create_model(
                f"{config.field}SingleFilter",
                field=Literal[config.field],
                operator=Literal[*single_operators],
                value=config.value_type,
                __doc__=config.description,
            )
            models.append(model)

        # only add list operators if there are some list-only operators
        # for example, if the only operator is "equals", we shouldn't add this as a list operator
        # however, if the operators are "any" and "equals", we add them both as list operators
        if list_only_operators & set(config.operators):
            list_operators = [
                op for op in config.operators if op in valid_list_operators
            ]
            if list_operators:
                description = config.description
                if "any" in list_operators:
                    any_description = (
                        f"Use the 'any' operator to return results where {config.field} equals "
                        "or contains any of the provided values."
                    )
                    if description:
                        description += f"\n{any_description}"
                    else:
                        description = any_description
                model = create_model(
                    f"{config.field}ListFilter",
                    field=Literal[config.field],
                    operator=Literal[*list_operators],
                    value=list[config.value_type],
                    __doc__=description,
                )
                models.append(model)

        unary_operators = [op for op in config.operators if op in valid_unary_operators]
        if unary_operators:
            model = create_model(
                f"{config.field}UnaryFilter",
                field=Literal[config.field],
                operator=Literal[*unary_operators],
                __doc__=config.description,
            )
            models.append(model)

    return typing.Union[*models]
