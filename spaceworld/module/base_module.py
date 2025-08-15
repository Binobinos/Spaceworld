"""Implementation of the Module's Base Class in SpaceWorld."""

from collections.abc import Callable
from typing import Unpack

from spaceworld.commands.base_command import BaseCommand
from spaceworld.exceptions.command_error import CommandCreateError
from spaceworld.exceptions.module_error import SubModuleCreateError
from spaceworld.types import Args, DynamicCommand, UserAny
from spaceworld.utils.util import BaseCommandAnnotated, register


class BaseModule:
    """
    Base class for creating command modules in SpaceWorld.

    Modules act as containers for related commands and submodules, providing:
    - Command registration and organization
    - Hierarchical command structures via submodules
    - Command metadata and configuration
    - Documentation support

    Attributes:
        name: Module identifier
        docs: Module description
        commands: Dictionary of registered commands
        modules: Dictionary of nested submodules
    """

    __slots__ = ("name", "docs", "commands", "modules", "_help_text", "_cached")

    def __init__(self, name: str, docs: str = "", cached: bool = True) -> None:
        """
        Initialize a new module instance.

        Args:
            name: Unique identifier for the module
            docs: Brief description of the module's purpose (default: "")
        """
        self.name: str = name
        self.docs: str = docs
        self.commands: dict[str, BaseCommand] = {}
        self.modules: dict[str, "BaseModule"] = {}
        self._help_text: None | str = None
        self._cached = cached

    @property
    def cached(self) -> bool:
        """
        Returns the caching value of the function.

        Returns:
            bool
        """
        return self._cached

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

    def decorator(self, func: DynamicCommand) -> DynamicCommand:
        """
        Register a function as a basic command in the module.

        Args:
            func: Callable to register as command

        Returns:
            The original function (decorator pattern)

        Raises:
            CommandCreateError: If command name already exists
        """
        name = func.__name__
        if name in self.commands:
            raise CommandCreateError(f"Command '{name}' already exists")
        command = BaseCommand(
            func=func,
            hidden=False,
            docs="",
            deprecated=False,
            examples=[],
            confirm=False,
            activate_modes={"normal"},
            history=True,
        )
        self.commands[name] = command
        return func

    def command(
        self,
        *,
        name: None | str = None,
        aliases: Args | None = None,
        big_docs: None | str = None,
        **kwargs: Unpack[BaseCommandAnnotated],
    ) -> DynamicCommand:
        """
        Decorate that registers a function as a configured command.

        Args:
            big_docs ():
            name: Command name (defaults to function name)
            aliases: List of command aliases

        Returns:
            Command registration decorator

        Raises:
            CommandCreateError: If command or aliases already exists
        """
        if aliases is None:
            aliases = []

        def decorator(func: DynamicCommand) -> DynamicCommand:
            """
            Register a function with arguments.

            Args:
                func(): Function

            Returns:
                Function
            """
            func_name = name.replace("-", "_") if name else func.__name__
            names = [alias not in self.commands for alias in aliases]
            if not all(names + [name not in self.commands]):
                raise CommandCreateError(
                    f"Command '{'/'.join(aliases + [func_name])} already exists"
                )
            cmd = BaseCommand(
                name=func_name, big_docs=big_docs, aliases=aliases, func=func, **kwargs
            )
            self.commands[func_name] = cmd
            for alias in cmd.aliases:
                self.commands[alias] = cmd
            return func

        return decorator

    def spaceworld(self, target: type[UserAny] | DynamicCommand) -> UserAny:
        """
        Register a callable or class as commands in SpaceWorld.

        This method automatically handles registration of:
        - Classes as modules (converting methods to commands)
        - Callable objects as individual commands

        Args:
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

        Examples:
            # Register a class
            >>> from spaceworld import SpaceWorld
            ... cns = SpaceWorld()
            ... @cns.spaceworld
            ... class MyCommands:
            ...     @staticmethod
            ...     def cmd1(): ...
            ...     @staticmethod
            ...     def cmd2(): ...

            # Register a function
            >>> from spaceworld import SpaceWorld
            ... cns = SpaceWorld()
            ... @cns.spaceworld
            ... def my_command(): ...

        Notes:
            - Class methods become commands under their original names
            - The decorator can be used both on classes and functions
            - Private methods (starting with _) are ignored
        """
        module = BaseModule(name=target.__name__.replace("-", "_"))
        return register(
            target=target,
            module_func=self.submodule,
            command_func=self.command(
                activate_modes={"all"},
                docs="",
                history=True,
                confirm=False,
                examples=[],
                deprecated=False,
                hidden=False,
            ),
            module=module,
        )

    def submodule(self, module: "BaseModule") -> "BaseModule":
        """
        Register a submodule within this module.

        Args:
            module: BaseModule instance to register

        Raises:
            SubModuleCreateError: If submodule name already exists
        """
        if module.name in self.modules:
            raise SubModuleCreateError(f"Submodule '{module.name}' already exists")
        self.modules[module.name] = module
        return self.modules[module.name]

    def module(
        self, *args: DynamicCommand | UserAny, **kwargs: UserAny
    ) -> Callable[[DynamicCommand], "BaseModule"] | UserAny:
        """
        Create a submodule.

        It serves as a wrapper over the decorator to support decorators with and without arguments.
        if only one args element is passed,
        it will return the submodule object, otherwise the decorator

        Args:
            *args(): Positional arguments for the decorator or a single function
            **kwargs(): Named arguments

        Returns:
            Submodule Object or Decorator
        """
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            func: DynamicCommand = args[0]
            name = func.__name__
            docs = func.__doc__ or ""
            return self.submodule(module=BaseModule(name, docs))

        def decorator(func: DynamicCommand) -> BaseModule:
            """
            Register and returns the SubModule.

            Args:
                func(): SubModule

            Returns:
                The same SubModule
            """
            name = kwargs.get("name", func.__name__)
            docs = kwargs.get("docs", func.__doc__) or ""
            return self.submodule(module=BaseModule(name, docs))

        return decorator

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
        examples = "\n\t".join(
            f"{cmd.examples}\t{cmd.config['docs']}" for cmd in self.commands.values()
        )
        msg = f"\n\t{examples}"
        return (
            f"Module `{self.name}` {f'- {self.docs.strip()}' if self.docs.strip() else ''}\n"
            f"Commands: {msg}\n"
            "Module Flags: \n"
            "\n\t--help\\-h \tDisplays the help\n"
            "\n\t--force\\-f\tCancels confirmation\n"
            "For reference on a specific command: \n"
            f"\t{self.name} <command> --help/-h\n"
        )
