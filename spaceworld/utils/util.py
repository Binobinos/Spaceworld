"""Additional functions file in SpaceWorld."""

from collections.abc import Callable
from functools import wraps
from inspect import signature
from typing import TypedDict

from spaceworld.annotation_manager import AnnotationManager
from spaceworld.types import UserAny, DynamicCommand, Transformer


def register(
    target: type[UserAny] | DynamicCommand,
    module_func: Transformer,
    command_func: Callable[[DynamicCommand], DynamicCommand],
    module: UserAny,
) -> UserAny | DynamicCommand:
    """
    Register a callable or class as commands or submodule in SpaceWorld.

    This method automatically handles registration of:
        - Classes as modules or submodule (converting methods to commands)
        - Callable objects as individual commands

        Args:
            module ():
            module_func ():
            command_func ():
            target: Either:
                    - A class (converted to module with command methods)
                    - A callable object (registered as single command)

        Behavior:
            For classes:
            - Creates a BaseModule with the class name
            - Registers all non-private methods as commands
            - Skips methods starting with '_'

            For callables:
            - Registers the function directly as a command
        Notes:
            - Class methods become commands under their original names
            - The decorator can be used both on classes and functions
            - Private methods (starting with _) are ignored
    """
    if hasattr(target, "__bases__") and hasattr(target, "__mro__"):
        module_func(module)
        for name in dir(target):
            if name.startswith("_"):
                module.decorator(getattr(target, name))
        return target
    return command_func(target)


def annotation_depends(func: Callable[..., UserAny]) -> Callable[..., UserAny]:
    """
    Decorate for automatic dependency injection based on function annotations.

    Converts arguments according to the annotations of the function types.
    Args:
        func: A decorated function with annotations of parameter types

    Returns:
        A wrapper function with embedded dependencies
    """

    @wraps(func)
    def wrapper(*args: UserAny, **kwargs: UserAny) -> UserAny:
        """
        Annotates arguments.

        Args:
            *args (UserAny):
            **kwargs (UserAny):

        Returns:
            UserAny
        """
        parameters = tuple(signature(func).parameters.values())
        annotations = AnnotationManager()
        processed_args, processed_kwargs, _ = annotations.preparing_args(
            parameters, list(args), kwargs
        )
        result = func(*processed_args, **processed_kwargs)
        return result

    return wrapper


class BaseCommandConfig(TypedDict):
    """Class for the configuration of the command object."""

    hidden: bool  # noqa
    deprecated: bool | str  # noqa
    confirm: bool | str  # noqa
    history: bool  # noqa
    activate_modes: set[str]  # noqa
    example: str  # noqa
    big_docs: str  # noqa
    docs: str  # noqa
    is_async: None | bool  # noqa
    cached: bool  # noqa


class BaseCommandAnnotated(TypedDict, total=False):
    """Class for command cache arguments."""

    hidden: bool  # noqa
    deprecated: bool | str  # noqa
    confirm: bool | str  # noqa
    examples: str | list[str]  # noqa
    history: bool  # noqa
    activate_modes: set[str]  # noqa
    docs: str  # noqa
