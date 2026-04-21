import os
import inspect
from typing import Callable, Literal
from klaviyo_mcp_server.server import mcp
from klaviyo_mcp_server.utils.utils import current_model_data


def mcp_tool(
    *,
    has_writes: bool,
    handles_user_generated_content: bool = False,
    **kwargs,
) -> Callable:
    """
    Registers a tool using mcp.tool.
    Does not register tools that write data if READ_ONLY environment variable is set.
    Does not register tools that handle user generated content if ALLOW_USER_GENERATED_CONTENT environment variable is set to false.
    """
    is_read_only = os.getenv("READ_ONLY") == "true"
    disable_user_generated_content = (
        os.getenv("ALLOW_USER_GENERATED_CONTENT") == "false"
    )
    disabled_due_to_user_generated_content = (
        handles_user_generated_content and disable_user_generated_content
    )
    disabled = has_writes and is_read_only

    def decorator(func: Callable):
        func_with_model_param = _add_model_param(func)

        return mcp.tool(
            func_with_model_param,
            enabled=not (disabled or disabled_due_to_user_generated_content),
            annotations={"readOnlyHint": not has_writes},
            name=f"klaviyo_{func.__name__}",
            **kwargs,
        )

    return decorator


def _add_model_param(func: Callable) -> Callable:
    """Adds a 'model' param to the given tool function.
    This is added to the User-Agent on requests to track what models users use with the server.
    """

    def wrapper(model: Literal["claude", "gpt", "gemini", "other"], *args, **kwargs):
        current_model_data.model = model
        return func(*args, **kwargs)

    # Create new signature with model parameter first
    original_sig = inspect.signature(func)
    wrapper_sig = inspect.signature(wrapper)
    new_params = list(wrapper_sig.parameters.values())[:1] + list(
        original_sig.parameters.values()
    )
    wrapper.__signature__ = original_sig.replace(parameters=new_params)

    # Combine annotations from wrapper and original function
    original_annotations = getattr(func, "__annotations__", {})
    wrapper_annotations = getattr(wrapper, "__annotations__", {})
    wrapper.__annotations__ = {**wrapper_annotations, **original_annotations}

    # Change name and docstring to match the original function
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__

    return wrapper
