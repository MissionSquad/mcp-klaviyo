from typing import Literal, get_args

SingleOperator = Literal[
    "equals",
    "less-than",
    "less-or-equal",
    "greater-than",
    "greater-or-equal",
    "contains",
    "ends-with",
    "starts-with",
]

valid_single_operators = set(get_args(SingleOperator))

ListOperator = Literal["equals", "contains-any", "contains-all", "any"]

valid_list_operators = set(get_args(ListOperator))

UnaryOperator = Literal["has"]

valid_unary_operators = set(get_args(UnaryOperator))


list_only_operators = valid_list_operators - valid_single_operators
