"""The main module Of SpaceWorld That implements the basic logic of the framework."""

import shlex
import sys
from collections.abc import Callable
from typing import Annotated, Never, TypedDict, Unpack

from ._types import (
    Args,
    CacheType,
    DynamicCommand,
    Kwargs,
    NewKwargs,
    TupleArgs,
    UserAny,
)
from .annotation_manager import AnnotationManager
from .commands.base_command import BaseCommand
from .exceptions.annotations_error import AnnotationsError
from .exceptions.command_error import CommandCreateError
from .exceptions.module_error import ModuleCreateError
from .exceptions.spaceworld_error import ExitError
from .module.base_module import BaseModule
from .utils.util import annotation_depends, BaseCommandAnnotated, register
from .writers.my_writer import MyWriter
from .writers.writer import Writer


class CommandCacheEntry(TypedDict):
    """A class for caching command arguments."""

    args: list[str] | tuple[str, ...]
    command: None | BaseCommand
    module: None | BaseModule


class SpaceWorld:
    """The main class of the SpaceWorld Framework."""

    __slots__ = (
        "name",
        "di",
        "command_history",
        "writer",
        "commands",
        "modules",
        "confirmation_command",
        "command_cache",
        "handlers",
        "docs",
        "versions",
    )

    def __init__(
            self,
            writer: None | Writer = None,
            name: str = "",
            versions: str = "",
            docs: str = "",
    ) -> None:
        """
        Initialize the SpaceWorld instance.

        Args:
            writer: An optional Writer class instance or its subclass for output operations.
                   If not provided, a default MyWriter instance will be used.

        Attributes initialized:
            annotations (Dict[str, Any]): A dictionary for storing arbitrary annotations.
            writer (Writer): The writer instance used for output operations.
            mode (str): Current operation mode (default: "normal").
            waiting_for_confirmation (bool): Flag indicating if waiting for user confirmation.
            confirm_message (list[str] | None): Message to display when confirmation is needed.
            confirmation_command (str | None): Command to execute upon confirmation.
            command_cache (Dict[str, dict[str, BaseCommand | list[str]] | bool]):
                Cache for command data.
            args_cache (Dict[tuple, tuple]): Cache for command arguments.
            commands (Dict[str, BaseCommand]): Registered commands.
            modules (Dict[str, BaseModule]): Loaded modules.

        Notes:
            - Automatically adds annotations for self and the writer instance.
            - Uses MyWriter as default if no writer is provided.
        """
        self.commands: dict[str, BaseCommand] = {}
        self.modules: dict[str, BaseModule] = {}
        self.name = name
        self.docs = docs
        self.versions = versions
        self.handlers: dict[str, Callable[..., None | ExitError | UserAny | Never]] = {}
        self.command_cache: dict[TupleArgs, CommandCacheEntry] = {}
        self.di: AnnotationManager = AnnotationManager()
        self.writer: Writer = writer or MyWriter()
        self.confirmation_command: TupleArgs | None = None
        self.di.add_custom_transformer(SpaceWorld, lambda _: self)
        self.di.add_custom_transformer(Writer, lambda _: self.writer)
        self.handler(name="help.command")(self._write_help)
        self.handler(name="help")(self.help_handler)
        self.handler(name="confirm.handle")(self._handle_confirm)
        self.handler(name="deprecated.handle")(self._write_deprecated)
        self.handler(name="errors.handle")(self.error_handler)

    def module(
        self, *args: DynamicCommand | UserAny, **kwargs: UserAny
    ) -> Callable[[DynamicCommand], BaseModule] | BaseModule:
        """
        Create a module.

        It serves as a wrapper over the decorator to support decorators with and without arguments.
        if only one args element is passed,it returns the modified function, otherwise the decorator
        Args:
            *args (Callable | Any): Positional arguments for the decorator or a single function
            **kwargs (Any): Named arguments

        Returns:
            Function or Decorator
        """
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            func: DynamicCommand = args[0]
            name = func.__name__
            docs = func.__doc__ or ""
            return self._register_module(BaseModule(name, docs))

        def decorator(func: DynamicCommand) -> BaseModule | UserAny:
            """
            Register a function with arguments.

            Args:
                func(): Function

            Returns:
                Function
            """
            name = kwargs.get("name", func.__name__)
            docs = kwargs.get("docs", func.__doc__) or ""
            cached = kwargs.get("cached", True)
            return self._register_module(BaseModule(name, docs, cached))

        return decorator

    def command(
        self,
        *,
        name: None | str = None,
        aliases: Args | None = None,
        big_docs: None | str = None,
        **kwargs: Unpack[BaseCommandAnnotated],
    ) -> Callable[[DynamicCommand], DynamicCommand]:
        """
        Decorate that registers a function as a SpaceWorld command.

        This transforms a regular function into a fully-featured SpaceWorld command with:
        - Custom naming and aliases
        - Documentation support
        - Mode-based activation
        - Confirmation prompts
        - Versioning controls

        Args:
            big_docs ():
            name: Command name (defaults to function name)
            aliases: Alternative command names (default: [])

        Returns:
            A decorator that registers the command

        Raises:
            CommandCreateError: If command name or aliases already exists
        """
        if aliases is None:
            aliases = []

        def decorator(func: DynamicCommand) -> DynamicCommand:
            """
            Register and returns a function.

            Args:
                func(): Function

            Returns:
                The same Function
            """
            func_name = (
                name.replace("-", "_") if name else func.__name__.replace("-", "_")
            )
            names = aliases + [func_name]
            if all(name in self.commands for alias in names):
                raise CommandCreateError(f"Command '{'/'.join(names)} already exists")
            command = BaseCommand(
                name=func_name, aliases=aliases, big_docs=big_docs, func=func, **kwargs
            )
            for alias in names:
                self.commands[alias] = command
            return func

        return decorator

    def spaceworld(
        self, target: type[UserAny] | DynamicCommand
    ) -> UserAny | DynamicCommand:
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

        Notes:
            - Class methods become commands under their original names
            - The decorator can be used both on classes and functions
            - Private methods (starting with _) are ignored
        """
        module = BaseModule(name=target.__name__.replace("-", "_"))
        return register(
            target=target,
            module_func=self._register_module,
            command_func=self._register_command,
            module=module,
        )

    def include(  # noqa
        self, obj: Callable[..., UserAny] | BaseModule | type["SpaceWorld"]
    ) -> Callable[..., UserAny] | BaseModule | type["SpaceWorld"]:
        """Add modules to the SpaceWorld environment.

        This method can either:
        - Import Python packages from a directory when given a Path object
        - Directly register module instances when provided in a list/tuple

        Args:
            obj: Either:
                    - A pathlib.Path object pointing to a directory of Python modules
                    - A list or tuple of pre-initialized BaseModule instances

        Behavior:
            - When given a Path:
                * Creates the directory if it doesn't exist
                * Attempts to import all .py files in the directory as modules
                * Silently skips files that fail to import or register
            - When given a list/tuple:
                * Directly registers each provided module

        Returns:
            The input object after processing (for method chaining)

        Notes:
            - For directory imports:
                * Only .py files are processed
                * The directory becomes a Python package
                * Modules must implement a register() function
            - Invalid modules are silently ignored
        """
        if isinstance(obj, BaseModule):
            self._register_module(obj)
            return obj
        if callable(obj):
            self._register_command(obj)
            return obj
        if isinstance(obj, type(self)):
            self.modules |= obj.modules
            self.commands |= obj.commands
            self.di.transformers |= obj.di.transformers
            return obj
        raise TypeError(f"Dont Support Type: {type(obj)}")

    def _register_module(self, module: BaseModule) -> BaseModule:
        """
        Register a module in the SpaceWorld environment.

        Args:
            module: The module to register, must be an instance of BaseModule or its subclass

        Raises:
            ModuleCreateError: If either:
                             - The provided object is not a BaseModule instance
                             - A module with the same name is already registered

        Returns:
            None

        Notes:
            - Module names must be unique within the SpaceWorld instance
            - The module's name is determined by its 'name' attribute
            - Registered modules become immediately available in the environment
        """
        if not isinstance(module, BaseModule):
            raise ModuleCreateError("The provided object is not a BaseModule instance")
        name = module.name
        if module.name in self.modules:
            raise ModuleCreateError(
                f"A module with name '{name}' is already registered"
            )
        self.modules[name] = module
        return module

    def _register_command(self, func: DynamicCommand) -> DynamicCommand:
        """
        Register the team in SpaceWorld.

        Creates a basic BaseCommand wrapper around the function with default settings:
        - Command name matches function name
        - Active in all modes
        - No aliases or special configurations

        Args:
            func: The callable to register as a command. Must have a __name__ attribute.

        Raises:
            CommandCreateError: If a command with the same name already exists.

        Notes:
            - This is an internal method typically called by other registration decorators
            - For more control over command properties, use the @command decorator instead
            - The created command will be active in all operation modes ('all')
        """
        func_name = func.__name__.replace("-", "_")
        if func_name in self.commands:
            raise CommandCreateError(f"Command '{func_name}' already exists")
        self.commands[func_name] = BaseCommand(
            name=func_name,
            func=func,
            activate_modes={"all"},
            docs="",
            history=True,
            confirm=False,
            examples=[],
            deprecated=False,
            hidden=False,
        )
        return func

    def error_handler(self, error: type[Exception]) -> None:
        """
        Handle errors and outputs a message.

        Args:
            error (type[Exception]): Type of error

        Returns:
            None
        """
        self.writer.error(error)

    def get_handler(self, name: str) -> Callable[..., UserAny]:
        """
        Return a handler object by name.

        Args:
            name (str): handler's name

        Returns:
            handler's object
        """
        return self.handlers[name]

    def handler(
        self, *args: DynamicCommand | UserAny, **kwargs: UserAny
    ) -> Callable[[DynamicCommand], DynamicCommand] | DynamicCommand:
        """
        Create a module.

        It serves as a wrapper over the decorator to support decorators with and without arguments.
        if only one args element is passed,it returns the modified function, otherwise the decorator
        Args:
            *args (Callable | Any): Positional arguments for the decorator or a single function
            **kwargs (Any): Named arguments

        Returns:
            Function or Decorator
        """
        if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
            handler: DynamicCommand = args[0]
            name = kwargs.get("name", handler.__name__)
            self.handlers[name] = handler
            return handler

        def _wraps(handler: Callable[..., UserAny]) -> Callable[..., UserAny]:
            """
            Register a function with arguments.

            Args:
                handler(): Function

            Returns:
                Function
            """
            name = kwargs.get("name", handler.__name__)
            self.handlers[name] = handler
            return handler

        return _wraps

    def help_handler(self) -> None:
        examples_command = "\n\t".join(
            f"{cmd.examples}\t{cmd.config['docs']}" for cmd in self.commands.values()
        )
        examples_module = "\n\t".join(
            f"{cmd.examples}\t{cmd.config['docs']}" for cmd in self.modules.values()
        )
        msg = f"\n\t{examples_command}"
        msg_ = f"\n\t{examples_module}"

        self.writer.write(
            (
                f"{self.name} "
                f"{f'- {self.docs.strip()}' if self.docs.strip() else ''} "
                f"{self.versions if self.versions.strip() else ''}\n"
                f"Commands: {msg}\n"
                f"{f"Modules: {msg_}\n" if msg_.strip() else ""}"
                "Flags: \n"
                "\n\t--help\\-h \tDisplays the help\n"
                "\n\t--force\\-f\tCancels confirmation\n\n"
                "For reference on a specific command: \n"
            )
        )

    def execute(self, command: TupleArgs | Args) -> UserAny | None:
        """
        Execute a console command in the SpaceWorld environment.

        Handles command execution with the following features:
        - Empty command validation
        - Pending confirmation handling
        - Error reporting for invalid commands
        - Normal command execution flow

        Args:
            command: The command string to execute. If empty, shows an error.

        Behavior:
            1. Validates the command is a non-empty string
            2. Checks for pending confirmations (handles them first if found)
            3. Executes the command through execute_command()
            4. Handles command execution results:
               - None or False indicates invalid command
               - True indicates successful execution
        """
        if not command:
            self.get_handler("help")()
            return None

        if self.confirmation_command:
            self._handle_confirmation(command)
            return None

        try:
            result = self.execute_command(command)
            return result
        except ExitError:
            return None
        except Exception as error:  # pylint: disable=W0718 # User Function
            self.get_handler("errors.handle")(error)
            self.writer.error(f"Error when executing the command: {error}")
            return None

    def execute_command(
        self, command: TupleArgs | Args, *, confirmation: bool | str = False
    ) -> UserAny | ExitError:
        """
        Execute a SpaceWorld command with full argument processing and validation.

        Handles the complete command execution pipeline including:
        - Command lookup and caching
        - Argument parsing and preparation
        - Mode validation
        - Help flag handling
        - Deprecation warnings
        - Confirmation flow
        - Error handling

        Args:
            command (): The command string to execute (including arguments)
            confirmation: Bypass confirmation prompt if True (default: False)

        Returns:
            bool | None:
                - True if command executed successfully
                - False if command not found or mode mismatch
                - None if execution failed or requires confirmation

        Behavior:
            1. Checks command cache or performs new command search
            2. Validates command is available in current mode
            3. Processes arguments (cached if previously parsed)
            4. Handles help flags (--help/-h) by showing command documentation
            5. Manages deprecation warnings
            6. Handles confirmation requirements
            7. Executes command with prepared arguments
            8. Returns execution status
        Notes:
            - Uses LRU caching for command lookup and argument parsing
            - Automatically handles --help/-h flags
            - Respects command activation modes
            - Manages deprecation warnings
            - Requires confirmation for sensitive commands unless bypassed
        """
        commands: CommandCacheEntry = self._get_command_cache(command)
        args: TupleArgs = tuple(commands["args"])
        cmd: None | BaseCommand = commands["command"]
        module: None | BaseModule = commands["module"]

        positional_args, keyword_args, kwargs = self._get_cached_args(args, cmd, module)

        self.get_handler("help.command")(kwargs, cmd, module)

        confirmation = kwargs.get("force", False)
        self.get_handler("confirm.handle")(cmd, confirmation, command)

        self.get_handler("deprecated.handle")(cmd)
        if not cmd:
            raise AnnotationsError("Command not found")
        return cmd(*positional_args, **keyword_args)

    def run(self, func: DynamicCommand | None = None, args: Args | None = None) -> None:
        """
        Start the main Execution cycle for the SpaceWorld console environment.

        Handles both direct command execution and interactive console operation:
        - Registers commands/functions when provided
        - Processes command-line arguments
        - Manages confirmation prompts
        - Maintains interactive session until completion

        Args:
            func: Optional callable to register as a command before execution
            args: Command arguments (defaults to sys.argv[1:] if None)

        Behavior:
            1. Registers provided function (if any) using spaceworld decorator
            2. Executes command from arguments (joins list into string)
            3. Enters interactive confirmation loop if needed:
               - Prompts for user input
               - Processes responses through execute()
               - Continues until confirmation is resolved

        Notes:
            - Defaults to system arguments if none provided
            - Handles both single commands and interactive sessions
            - Maintains full command processing pipeline
            - Supports SpaceWorld's confirmation workflow
        """
        if func:
            self.spaceworld(func)
        if args is None:
            args = sys.argv[1:]
        try:
            self.execute(tuple(args))
            while self.confirmation_command:
                user_input = input(">>> ")
                self.execute(tuple(shlex.split(user_input)))
        except KeyboardInterrupt:
            sys.exit(-1)

    def interactive(  # noqa
        self, func: DynamicCommand | None = None
    ) -> None:
        """
        Launch interactive mode.

        Args:
            func(): Function for the run
        Returns:
            None
        """
        if func:
            self.spaceworld(func)
        try:
            while True:
                user_input = input(">>> ")
                if user_input in {"exit"}:
                    break
                self.execute(tuple(shlex.split(user_input)))
        except KeyboardInterrupt:
            sys.exit(-1)

    def __call__(
        self, func: DynamicCommand | None = None, args: Args | None = None
    ) -> None:
        """
        Call run of the class.

        It is used for convenient calling
        Args:
            func(): A callable object
            args(): Arguments to call from the code

        Returns:
            None
        """
        self.run(func, args)

    def _write_help(
        self,
        kwargs: Kwargs | NewKwargs,
        cmd: BaseCommand | None,
        module: BaseModule | None,
    ) -> None:
        """
        Output help if there are keys in the dictionary.

        Args:
            kwargs (): Dictionary

        Returns:
            True if the help is displayed, False if not
        """
        if kwargs.get("help", False) or kwargs.get("h", False):
            help_text: str = (
                cmd.help_text if cmd else module.help_text if module else ""
            )
            self.writer.write(help_text)
            raise ExitError

    def _handle_confirm(
        self, cmd: BaseCommand, confirmation: bool, command: TupleArgs
    ) -> None:
        if cmd.config["confirm"] and not confirmation:
            self._set_confirm_command(command, cmd)
            raise ExitError

    def _get_command_cache(self, args: TupleArgs | Args) -> CommandCacheEntry:
        """
        Return cached arguments for later invocation.

        Args:
            args (tuple[str, ...]): Bare arguments

        Returns:
            Ready-made cached arguments
        """
        args = tuple(args)
        if args not in self.command_cache:
            self.command_cache[args] = self._search_command(args)
        return self.command_cache[args]

    def _write_deprecated(self, cmd: BaseCommand) -> None:
        """
        Output a warning command.

        Args:
            cmd(): Command object
        Returns:
            None
        """
        deprecated = cmd.config["deprecated"]
        if deprecated:
            self.writer.warning(deprecated)

    def _check_mode(  # noqa
        self, cmd: None | BaseCommand
    ) -> bool:
        """
        Check the correspondence of the command modes and console.

        Args:
            cmd(): Command object
        Returns:
            Matching modes(bool)
        """
        if not cmd:
            return False
        modes = cmd.config["activate_modes"]
        return "all" not in modes  # and self.mode not in modes

    def _is_cached(
        self, args: TupleArgs, cmd: None | BaseCommand, module: None | BaseModule
    ) -> bool:
        return (
            args not in self.di.args_cache
            or not (module and module.cached)
            or not (cmd and cmd.cached)
        )

    def _get_cached_args(
        self, args: TupleArgs, cmd: None | BaseCommand, module: None | BaseModule
    ) -> CacheType:
        """
        Return cacheable arguments.

        Args:
            args (): Bare arguments
            cmd(): Command object
        Raises:
            TypeError: Exit with None
            ValueError: The help table is displayed and returns with True
        Returns:
            A tuple of new args and kwargs and naked kwargs
        """
        if self._is_cached(args, cmd, module):
            keyword_args: dict[str, bool | str] = {}
            try:
                positional_args, keyword_args = self.di.pre_preparing_arg(args)
                if not cmd:
                    raise AnnotationsError("Command not found")
                self.di.args_cache[args] = self.di.preparing_args(
                    cmd.parameters, positional_args, keyword_args
                )
            except (ValueError, IndexError, TypeError, AnnotationsError) as error:
                self._write_help(keyword_args, cmd, module)
                self.get_handler("errors.handle")(error)
                raise ExitError from error
        return self.di.args_cache[args]

    def _search_command(self, command: Args | TupleArgs) -> CommandCacheEntry:
        """
        Recursively searches for a command in the SpaceWorld command hierarchy.

        This internal method handles command lookup through:
        - Global command registry
        - Module-specific commands
        - Nested module structures
        - Argument separation

        Args:
            command: Tokenized command parts (split by spaces)

        Returns:
            dict | bool:
                - Dictionary with keys:
                  * "command": Found BaseCommand instance
                  * "args": Remaining command arguments
                - False if command not found

        Behavior:
            1. Splits command into first argument and remaining parts
            2. Searches in this order:
               a) Global commands (if no module specified)
               b) Module commands
               c) Submodules (recursively)
            3. Returns immediately when first match is found

        Notes:
            - This is an internal method used by the command execution system
            - Handles both simple commands and module-qualified commands
            - Maintains separation between command and arguments
            - Uses depth-first search through module hierarchy
        """
        first_arg, *args = command
        first_arg = first_arg.replace("-", "_")
        module: BaseModule | UserAny = self
        while [first_arg] + args:
            modules, commands = module.modules, module.commands
            _module: None | BaseModule = None if module is self else module
            if first_arg in commands:
                return {"command": commands[first_arg], "args": args, "module": _module}
            if first_arg in modules:
                module = modules[first_arg]
                try:
                    first_arg, *args = args
                except ValueError:
                    break
            else:
                args = [first_arg.replace("_", "-")] + args
                return {"command": None, "args": args, "module": _module}
        return {"command": None, "args": (), "module": None}

    def _handle_confirmation(self, response: TupleArgs | Args) -> None:
        """
        Handle user confirmation responses for sensitive commands.

        Processes the user's response to a confirmation prompt and either:
        - Executes the pending command (if confirmed)
        - Cancels the operation (if denied)

        Args:
            response: User's input response to the confirmation prompt
        Behavior:
            - Compares response against valid confirmation words (case-sensitive)
            - On confirmation:
              * Logs the execution
              * Executes the pending command with confirmation bypass
            - On denial:
              * Cancels the operation with warning
            - Always resets confirmation state after handling
        Side Effects:
            - Modifies instance state:
              * waiting_for_confirmation (set to False)
              * confirmation_command (set to None)
            - May execute pending command
            - Writes to output via writer
        """
        if response[0].lower() in {"yes", "y"}:
            self.writer.info(f"Executing the command: {response}")
            self.execute_command(response, confirmation=True)
            return
        self.writer.warning("The command has been cancelled.")

    def _set_confirm_command(self, command: TupleArgs, func: BaseCommand) -> None:
        """
        Set up a command confirmation prompt in the SpaceWorld environment.

        Prepares the system for command confirmation by:
        - Displaying the confirmation prompt message
        - Setting the command in pending confirmation state
        - Storing the confirmation requirements

        Args:
            command: The full command string awaiting confirmation
            func: The BaseCommand instance requiring confirmation

        Side Effects:
            - Stores command as confirmation_command
            - Sets confirm_message from command's confirm_word
            - Displays prompt to user via writer

        Behavior:
            - Uses custom confirmation message if specified in command
            - Falls back to default message if no custom message provided
            - Puts system in confirmation state until user responds

        Notes:
            - Actual confirmation handling occurs in _handle_confirmation
            - System remains in confirmation state until user responds
            - Command won't execute until confirmed
        """
        self.writer.input(func.config["confirm"])
        self.confirmation_command = command

    @annotation_depends  # noqa
    def set_mode(
        self,
        mode: Annotated[
            str,
            lambda mode: mode
            if isinstance(mode, str)
            else TypeError("Console mode must be specified as a string"),
        ],
    ) -> None:
        """
        Set the current operating mode of the SpaceWorld console.

        This mode affects which commands are available and how they behave.
        Common modes might include 'normal', 'debug', or 'admin'.

        Args:
            mode: The new mode to set (must be a string).
                  This should match one of the predefined mode names
                  used in command activation checks.

        Raises:
            TypeError: If the provided mode is not a string.

        Side Effects:
            - Updates the internal mode state
            - Affects which commands are available (commands may check current mode)
            - May change console behavior depending on mode-specific implementations

        Notes:
            - Mode names are case-sensitive
            - Commands can declare which modes they support via activate_modes
            - Changing modes doesn't affect currently executing commands
        """
        print(mode.lower())


def run(func: DynamicCommand | None = None, args: Args | None = None) -> None:
    """
    Initialize and runs a SpaceWorld console session.

    This is the main entry point for executing commands in a SpaceWorld environment.
    It handles both direct command execution and interactive sessions with confirmations.

    Args:
        func: A callable to register as a command before execution (optional).
              If provided, will be decorated with @spaceworld.
        args: List of command arguments as strings (optional).
              Defaults to sys.argv[1:] if None (command line arguments).

    Behavior:
        1. Creates a new SpaceWorld instance
        2. Registers the provided function (if any)
        3. Executes the command from arguments
        4. Enters interactive confirmation loop if needed:
           - Shows prompt (> )
           - Processes user input
           - Continues until confirmation is resolved

    Notes:
        - Creates a fresh SpaceWorld instance for each run
        - Supports both programmatic and command-line usage
        - Handles the complete command lifecycle including confirmations
        - Default prompt for confirmations is '> '
    """
    cns = SpaceWorld()
    if func:
        cns.spaceworld(func)
    if args is None:
        args = sys.argv[1:]
    cns.execute(args)
    while cns.confirmation_command:
        user_input = input(">>> ")
        cns.execute(shlex.split(user_input))
