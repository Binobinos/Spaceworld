import asyncio
import importlib
import inspect
import logging
import pathlib
from typing import Dict, Union, Optional, List, Any, Tuple

from base_command import BaseCommand
from base_module import BaseModule
from base_writer import Writer
from exceptions.API_error.base_api_error import AnnotationsError
from exceptions.API_error.module_error import ModuleCreateError

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s (SPACEWORLD:%(filename)s) %(message)s")
logging.debug(f"Loading API")


class SpaceWorld:
    """
    Базовый Класс Команд SpaceWorld
    """
    __slots__: List[str] = ["annotations", "modules", "mode", "command_history", "writer",
                            "waiting_for_confirmation", "confirmation_command"]

    def __init__(self, writer: Writer) -> None:
        """
        Инициализация API SpaceWorld
        :param writer: Класс
        """
        logging.debug(f"API INIT")
        self.annotations: Dict[str, Any] = {}
        self.add_annotations(self)
        self.modules: Dict[str, BaseModule] = {}
        self.mode: str = "normal"
        self.command_history: List[str] = []
        self.writer = writer
        self.waiting_for_confirmation: bool = False
        self.confirmation_command: Optional[str] = None

    def add_annotations(self, attribute: Any) -> None:
        """
        Добавляет аннотацию в API
        :param attribute: Класс атрибута
        :return: None
        """
        name = type(attribute).__name__
        logging.debug(f"Add annotations {name} - {attribute}")
        if name in self.annotations:
            logging.error(f"Error Add annotations {name} - {attribute}. Annotations the Create! "
                          f"Using method update_annotations")
            raise AnnotationsError(f"Ошибка добавления анастации {name}. Такая анастация есть"
                                   f"Используйте update_annotations")
        self.annotations[name] = attribute

    def update_annotations(self, name: str, new_attribute: Any):
        """

        :param name:
        :param new_attribute:
        :return:
        """
        logging.debug(f"Update annotations {name} - {new_attribute}")
        if name not in self.annotations:
            logging.error(f"Error updating the {name} annotation. There is no such annotation"
                          f"Use add_annotations")
            raise AnnotationsError(f"Error updating the {name} annotation. There is no such annotation"
                                   f"Use add_annotations")
        self.annotations[name] = new_attribute

    def execute(self, command: Union[str, List[str], Tuple[str]] = ""):
        """
        Выполняет команду, введенную в консоли.
        """
        if isinstance(command, (list, tuple)):
            logging.debug(f"The list of commands has been found. We carry out")
            for com in command:
                if isinstance(com, str):
                    self.execute(com)
        elif isinstance(command, str):
            command = command.strip()
            commands = command.split("\n")
            if len(commands) > 1:
                logging.debug(f"We divide the commands by \n")
                for comm in commands:
                    self.execute(comm)
            else:
                if self.confirmation_command:
                    self.handle_confirmation(command.strip())
                    return
                logging.debug(f"executing the command \"{command}\"")
                self.writer.write(f">>> {command}")
                value = self.execute_command(command)
                if not value and not (value is None):
                    self.writer.error(f"Wrong command: {command}")

    def handle_confirmation(self, response):
        """
        Обрабатывает ответ пользователя на запрос подтверждения.
        """
        logging.debug(f"checking the team's permission {self.confirmation_command}")
        if response in ["y", "yes"]:
            logging.debug(f"The command is allowed. We carry out")
            self.writer.info(f"Executing the command: {self.confirmation_command}")
            self.execute_command(self.confirmation_command, confirmation=True)
        else:
            self.writer.warning("The command has been cancelled.")
        self.waiting_for_confirmation = False
        self.confirmation_command = None

    def include_modules(self, modules: Union[pathlib.Path, List[BaseModule], Tuple[BaseModule]]) -> None:
        """
        Uploads modules to SpaceWorld
        :param modules:
        :return:
        """
        if isinstance(modules, pathlib.Path):
            modules_dir = modules
            logging.debug(f"Importing package from a folder {modules_dir}")
            if not modules_dir.exists():
                modules_dir.mkdir()
                return

            for py_file in modules_dir.glob("*.py"):
                module_name = py_file.stem
                full_module_name = f"{modules_dir}.{module_name}"
                try:
                    module = importlib.import_module(full_module_name)
                    logging.debug(f"Loading the package: {full_module_name}")
                    self.register_module(module=module.register())
                    logging.debug(f"The module was package successfully: {full_module_name}")
                except Exception as e:
                    logging.error(f"Module loading error {full_module_name}: {e}")
        elif isinstance(modules, (list, tuple)):
            logging.debug(f"Importing modules from the list of modules")
            for module in modules:
                self.register_module(module=module)

    def register_module(self, *, module: BaseModule) -> None:
        """
        Регистрирует модуль в SpaceWorld Api
        Args:
            module: Загружаемый модуль
        Returns:
            None
        """
        if not isinstance(module, BaseModule):
            raise ModuleCreateError("This module is not BaseModule")
        logging.debug(f"Importing module {module.name}")
        if module.name in self.modules:
            raise ModuleCreateError("This module is create")
        self.modules[module.name] = module

    def search_command(self,
                       command: str,
                       module: Union[BaseModule, None] = None):
        """

        :param command:
        :param module:
        :return:
        """
        command = command.split()
        try:
            first_arg = command[0]
        except IndexError:
            first_arg = ""
        if first_arg in self.modules:
            return self.search_command(" ".join(command[1:]), module=self.modules[command[0]], )
        elif not (module is None) and first_arg in module.pod_modules:
            return self.search_command(" ".join(command[1:]), module=module.pod_modules[command[0]], )
        elif not (module is None) and first_arg in module.commands:
            return {"command": module.commands[command[0]], "args": command[1:]}
        else:
            return False

    def preparing_args(self, func, args):
        """

        :param func:
        :param args:
        :return:
        """
        logging.debug(f"Preparing args")
        signature = inspect.signature(func)
        args: List[str] = list(args)
        positional_args, keyword_args = [], {}
        logging.debug(f"Initial preparation of arguments:")
        for arg in args:
            if not arg.startswith("--"):
                logging.debug(f"    Positional Args - {arg} ")
                positional_args.append(arg)
            else:
                arg = arg[2:]
                if "=" in arg:
                    index = arg.index("=") + 1
                    name, value = arg[:index - 1], arg[index:]
                    if value.lower() in ["false", "true"]:
                        keyword_args[name] = True if value.lower() == "true" else False
                        logging.debug(f"    Flag named argument \"{name} \"with the value {True
                        if value.lower() == "true" else False}")
                    else:
                        keyword_args[name] = value
                        logging.debug(f"    Keyword argument is \"{name}\" with the value {value} ")
                else:
                    if arg.startswith("no-"):
                        logging.debug(f"    Flag named argument \"{arg[3:]}\" with the value False")
                        keyword_args[arg[3:]] = False
                    else:
                        logging.debug(f"    Flag named argument \"{arg}\" with the value True")
                        keyword_args[arg] = True
        positional_args_index, keyword_args_index = 0, 0
        new_args_positional, new_args_keyword = [], {}
        logging.debug(f"Validation preparation of arguments: ")
        for param in signature.parameters.values():
            kind = param.kind
            param_name = param.name
            is_annotation = param.annotation != param.empty
            logging.debug(f"    Param {param_name}:")
            # 1. Инъекция зависимостей
            if param.annotation.__name__ in self.annotations:
                name = param.annotation.__name__
                logging.debug(f"        Dependency Injection {name}.")
                value = self.annotations[name]
                new_args_positional.append(value)
                continue
            # 2. *args аргумент
            elif kind == param.VAR_POSITIONAL:
                logging.debug(f"        Passing the remaining arguments to *args")
                new_args = positional_args[positional_args_index:]
                new_args_positional.extend(list(map(param.annotation, new_args)) if is_annotation else new_args)
                positional_args_index = len(positional_args)
                continue

            # 3. Именованный аргумент
            elif kind == param.KEYWORD_ONLY:
                try:
                    value = keyword_args[param_name]
                    logging.debug(f"        Passing the named argument {param_name} with the value {value}")
                    new_args_keyword[param_name] = param.annotation(value) if is_annotation else value
                    keyword_args_index += 1
                    continue
                except Exception as e:
                    raise ValueError(f"Invalid argument for '{param_name}': {e}") from e

            # 4. **kwargs аргумент
            elif kind == param.VAR_KEYWORD:
                try:
                    logging.debug(f"        Passing the remaining arguments to **kwargs:")
                    for name, value in list(keyword_args.items())[keyword_args_index:]:
                        logging.debug(f"            Passing the named argument \"{name}\" with the value {value}")
                        new_args_keyword[name] = param.annotation(value) if is_annotation else value
                        keyword_args_index += 1
                    continue
                except Exception as e:
                    raise ValueError(f"Invalid argument for '{param_name}': {e}") from e

            # позиционный аргумент
            elif positional_args_index < len(positional_args):
                try:
                    value = positional_args[positional_args_index]
                    logging.debug(f"        Passing the positional argument {value}")
                    new_args_positional.append(param.annotation(value) if is_annotation else value)
                    positional_args_index += 1
                    continue
                except Exception as e:
                    raise ValueError(f"Invalid argument for '{param_name}': {e}") from e

            # Дефолтный аргумент
            elif param.default != param.empty:
                logging.debug(f"        Passing the default argument {param.default}")
                new_args_positional.append(param.default)
                continue
            else:
                raise TypeError(f"Missing required argument: '{param_name}'")
        return new_args_positional, new_args_keyword, True if "help" in keyword_args and keyword_args["help"] else False

    def execute_command(self,
                        command: str,
                        *,
                        confirmation: bool = False) -> Union[bool, None]:
        """
        Исполняет команду
        :param command: Команда
        :param confirmation: Флаг выполнения команды без подтверждения
        :return:
        """
        commands = self.search_command(command)
        if not commands:
            logging.debug(f"The command was not found")
            return False
        args, command_ = commands["args"], commands["command"]
        func = command_.func
        modes = list(map(str.lower, command_.activate_mode))
        logging.debug(f"Command {command_.name} found, args: {args}")
        if self.mode.lower() not in modes and "all" not in modes:
            logging.debug(f"Wrong command execution mode")
            return False
        try:
            new_args_positional, new_args_keyword, help_menu = self.preparing_args(func, args)
        except Exception as e:
            logging.error(e)
            return False
        if help_menu:
            logging.debug(f"Display the help menu")
            self.writer.write(command_.get_help_doc())
            return True
        if command_.history:
            logging.debug(f"Adding commands to the history")
            self.command_history.append(command)
        if command_.deprecated and not confirmation:
            logging.debug(f"We are displaying a message about an outdated command")
            self.writer.warning(f"This command is deprecated and will be removed in future versions.")
        if command_.confirm and not confirmation:
            logging.debug(f"Setting the command confirmation status")
            self.set_confirm_command(command_.name, command_)
            return None
        logging.debug(f"Executing the command")
        try:
            if inspect.iscoroutinefunction(func):
                logging.debug(f"Executing an asynchronous command")
                asyncio.run(func(*new_args_positional, **new_args_keyword))
            else:
                logging.debug(f"Executing a synchronous command")
                func(*new_args_positional, **new_args_keyword)
            return True
        except Exception as error:
            self.writer.error(f"Error when executing the command: {error}")
            return False

    def return_commands(self, *, modules: BaseModule | None = None,
                        names: str = "",
                        string: Optional[List[str]] = []) -> list:
        """

        :param modules:
        :param names:
        :param string:
        :return:
        """
        if modules is None:
            for name, module in self.modules.items():
                string.append(f"{name} - {module.docs}")
                self.return_commands(modules=module, names=module.name)
                for command_name, command in module.commands.items():
                    if not command.hidden:
                        string.append(f"{name} {command_name} - {command.docs}")
        elif not (modules is None) and modules.pod_modules:
            for name, module in modules.pod_modules.items():
                string.append(f"{names} {name} - {module.docs}")
                self.return_commands(modules=module, names=f"{names} {name}")
                for command_name, command in module.commands.items():
                    if not command.hidden:
                        string.append(f"{names} {name} {command_name} - {command.docs}")
        return string

    def set_confirm_command(self, command, func: BaseCommand):
        """

        :param command:
        :param func:
        :return:
        """
        def_message = "You are confirming the execution of the command"
        self.writer.input_info(f"{func.confirm if isinstance(func.confirm, str) else def_message} {command}? (y/n)")
        self.waiting_for_confirmation = True
        self.confirmation_command = command

    def set_mode(self, mode: str):
        """
        Устанавливает режим консоли
        :param mode:
        :return:
        """
        if isinstance(mode, str):
            self.mode = mode


class MyWriter(Writer):
    def write(self, *text: Any) -> None:
        print(f"{" ".join([item.__str__() for item in text])}")

    def info(self, *text: Any) -> None:
        print(f"INFO: {" ".join([item.__str__() for item in text])}")

    def warning(self, *text: Any) -> None:
        print(f"WARNING: {" ".join([item.__str__() for item in text])}")

    def error(self, *text: Any) -> None:
        print(f"ERROR: {" ".join([item.__str__() for item in text])}")

    def input_info(self, *text: Any):
        print(f"INPUT: {" ".join([item.__str__() for item in text])}")


if __name__ == '__main__':
    console = SpaceWorld(MyWriter())
    console.include_modules(pathlib.Path("modules"))
    console.add_annotations(console.writer)
    console.execute("""
    sw help --name=3
    """)
