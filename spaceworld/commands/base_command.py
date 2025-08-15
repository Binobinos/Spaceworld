"""Implementing the basic SpaceWorld command."""

import asyncio
from inspect import iscoroutinefunction, Parameter, signature
from typing import Unpack

from spaceworld.types import (
    Args,
    DynamicCommand,
    NewArgs,
    NewKwargs,
    Parameters,
    UserAny,
)
from spaceworld.utils.util import BaseCommandAnnotated, BaseCommandConfig


class BaseCommand:
    """
    Base class for SpaceWorld command implementations.

    Encapsulates command behavior and metadata including:
    - Command execution (sync/async)
    - Help documentation generation
    - Parameter inspection
    - Activation modes
    - Deprecation status
    - Confirmation requirements

    Attributes:
        name: Primary command name
        aliases: Alternative command names
        func: Callable implementation
    """

    __slots__ = (
        "name",
        "aliases",
        "func",
        "_help_text",
        "_parameters",
        "config",
        "_examples",
    )

    def __init__(
        self,
        *,
        name: None | str = None,
        aliases: Args | None = None,
        func: DynamicCommand,
        big_docs: None | str = None,
        **opt: Unpack[BaseCommandAnnotated],
    ) -> None:
        """
        Initialize a new command instance.

        Args:
            name: Command name (defaults to function name)
            aliases: Alternative command names
            docs: Short description (defaults to function docstring)
            examples: Usage example (auto-generated if empty)
            activate_modes: Valid activation modes (default: ["normal"])
            func: Command implementation function
            big_docs: Detailed documentation (defaults to short docs)
            hidden: If True, hides from help/autocomplete
            deprecated: Deprecation flag or custom message
            confirm: Confirmation requirement flag or custom prompt
            history: If False, excludes from command history
        """
        self.func: DynamicCommand = func
        self.name: str = name or self.func.__name__
        self.aliases: Args = aliases or []
        self._parameters: Parameters | None = None
        self._examples = opt.get("examples", "")
        self._help_text: None | str = None

        docs = opt.get("docs", self.func.__doc__) or ""
        self.config: BaseCommandConfig = {
            "activate_modes": opt.get("activate_modes", {"normal"}),
            "hidden": opt.get("hidden", False),
            "deprecated": opt.get("deprecated", False),
            "big_docs": big_docs or docs,
            "confirm": opt.get("confirm", ""),
            "history": opt.get("history", False),
            "is_async": None,
            "docs": docs,
            "example": "",
            "cached": True,
        }

    @property  # noqa
    def is_async(self) -> None | bool:
        """
        Lazily returns the is_async.

        Returns:
            is_async
        """
        if self.config["is_async"] is None:
            self.config["is_async"] = iscoroutinefunction(self.func)
        return self.config["is_async"]

    @property
    def cached(self) -> bool:
        """
        Returns the caching value of the function.

        Returns:
            bool
        """
        return True

    @property
    def help_text(self) -> str:
        """
        Lazily returns the help table.

        Returns:
            help table
        """
        if self._help_text is None:
            self._help_text = self.get_help_doc()
        return self._help_text

    @property
    def big_docs(self) -> str:
        """
        Return a large documentation on the function.

        Returns:
            returns the docs
        """
        return self.config["big_docs"]

    @property
    def examples(self) -> str:
        """
        Lazily returns the example table.

        Returns:
            example table
        """
        if not self.config["example"]:
            self.config["example"] = self.generate_example(self._examples)
        return self.config["example"]

    @property
    def parameters(self) -> Parameters:
        """
        Return function parameters.

        Returns:
            Returns the signature of the command
        """
        if self._parameters is None:
            self._parameters = tuple(signature(self.func).parameters.values())
        return self._parameters

    def get_msg(self) -> tuple[str, str]:
        """
        Возвращает кортеж сообщений.

        Returns:
            Сообщение об устаревшей команде и confirm команде
        """
        deprecated_msg = (
            f"Deprecated: {'YES' if isinstance(dp, bool) else f'the message: {dp}'}"
            if (dp := self.config["deprecated"])
            else ""
        )
        confirmation_msg = (
            f"Confirm {'ation YES' if isinstance(cm, bool) else f'ing the message: {cm}'} "
            if (cm := self.config["confirm"])
            else ""
        )
        return deprecated_msg, confirmation_msg

    def get_help_doc(self) -> str:
        """
        Generate formatted help documentation for the command.

        Returns:
            str: Multi-line help text containing:
                 - Name and aliases
                 - Documentation
                 - Usage example
                 - Activation modes
                 - Parameter details
                 - Visibility status
                 - Deprecation status
                 - Confirmation requirements
        """
        deprecated_msg, confirmation_msg = self.get_msg()
        return (
            f"Usage: {self.examples}"
            f"{self.big_docs or 'None documentation'}\n"
            f"{f'Args: \n{args}\n\n' if (args := self._get_args_info()) else ''}\n"
            f"Options: \n{self._get_options_info()}\n"
            f"{'Hidden' if self.config['hidden'] else ''}\n"
            f"{deprecated_msg}"
            f"{confirmation_msg}"
        )

    def generate_example(self, examples: str | Args) -> str:
        """
        Generate documentation for the team.

        Args:
            examples (): One example or a list of examples
        Returns:
            example table
        """
        prefix: dict[UserAny, str] = {
            Parameter.KEYWORD_ONLY: "--",
            Parameter.VAR_POSITIONAL: "*",
            Parameter.VAR_KEYWORD: "**",
        }

        msg = " ".join([
            (
                "["
                f"{prefix.get(prm.kind, '')}"
                f"{prm.name}: {an.__name__ if (an := prm.annotation) != prm.empty else 'Any'}"
                f"{f" = '{prm.default}'" if prm.default != prm.empty else ''}"
                "]"
            )
            for prm in self.parameters
        ])
        examples = "\n".join(examples) if isinstance(examples, list) else examples
        return f"{self.name} [ARGS] [OPTIONS] {msg} \n{examples}"

    def _get_args_info(self) -> str:
        """
        Format parameter information for help documentation.

        Returns:
            str: Formatted parameter details with:
                 - Parameter names
                 - Types
                 - Default values
        """
        return "\n".join([
            f"  {prm.name}: {prm.annotation}"
            for prm in self.parameters
            if prm.kind not in {prm.KEYWORD_ONLY, prm.VAR_KEYWORD}
            and prm.annotation is not bool
        ])

    def _get_options_info(self) -> str:
        """
        Format parameter information for help documentation.

        Returns:
            str: Formatted parameter details with:
                 - Parameter names
                 - Types
                 - Default values
        """
        system_options = [
            "  --help - Displays the help on the command",
            "  --force - Disables command confirmations(For confirm command)"
            if self.config["confirm"]
            else "",
        ]
        options = [
            f"  --{prm.name.replace('_', '-')}: {prm.annotation.__name__} = {prm.default}"
            for prm in self.parameters
            if prm.kind in {prm.KEYWORD_ONLY, prm.VAR_KEYWORD} or prm.annotation is bool
        ] + system_options
        return "\n".join(options)

    async def run_async_command(  # noqa
        self, args: NewArgs, kwargs: NewKwargs
    ) -> UserAny:
        """
        Execute an async command with provided arguments.

        Args:
            args: Positional arguments
            kwargs: Keyword arguments
        """
        return await self.func(*args, **kwargs)

    def __call__(self, *args: UserAny, **kwargs: UserAny) -> UserAny:
        """
        Run func.

        Args:
            *args ():
            **kwargs ():

        Returns:
            None
        """
        if self.is_async:
            coroutine = self.func(*args, **kwargs)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return asyncio.run(coroutine)
            return loop.run_until_complete(coroutine)
        return self.func(*args, **kwargs)
