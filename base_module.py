from typing import Dict, Self, Optional, List, Union

from base_command import BaseCommand
from exceptions.API_error.command_error import CommandCreateError
from exceptions.API_error.module_error import ModuleCreateError, SubModuleCreateError


class BaseModule:
    """
    Базовый класс Модуля
    """
    __modules = []

    def __init__(self,
                 name: str,
                 docs: str,
                 *,
                 big_docs: str = "",
                 deprecated: bool = False) -> None:
        """
        Инициализирует класс модуля
        Args:
            name: Название модуля
            docs: Описание модуля
        """
        if name not in self.__modules:
            self.__modules.append(name)
        else:
            raise ModuleCreateError("This module is create")
        self.name = name
        self.docs = docs
        self.commands: Dict[str, BaseCommand] = {}
        self.pod_modules: Dict[str, Self] = {}

    def register_command(self,
                         *,
                         name: str,
                         alias: Optional[List[str]] = None,
                         docs: Optional[str] = None,
                         example: str = "",
                         activate_modes: Union[str, List[str]] = "normal",
                         big_docs: Optional[str] = None,
                         hidden: bool = False,
                         deprecated: Union[bool, str] = False,
                         confirm: Union[bool, str] = False,
                         history: bool = True):
        """
        Инициализирует класс команды SpaceWorld
        Args:
            name: Имя команды
            docs: Краткое описание команды
            example: Пример использования команды
            activate_modes: Режим(-ы) активации команды
            func: Функция привязанная к команде
            big_docs: подробная документация для флага --help
            hidden: Флаг скрытой команды. Если True, то команда не отображается в документации и дополнении,
                но продолжает работать. По умолчанию False
            deprecated: Флаг устаревший команды. Если True, то при использовании показывается предупреждение, что
                команда устаревшая. Если строка, то выводится кастомное предупреждение.
                По умолчанию False
            confirm: Флаг подтверждения команды. Если True, то при использовании запрашивается
                стандартное подтверждение (Y/N). Если строка, то выводится кастомное предупреждение.
                По умолчанию False
            history: Флаг сохранения в историю. Если False, то использование команды не добавляется в историю.
                По умолчанию True
        """

        def decorator(func):
            if name not in self.commands:
                self.commands[name] = BaseCommand(name=name,
                                                  alias=alias,
                                                  docs=docs,
                                                  example=example,
                                                  activate_modes=activate_modes,
                                                  func=func,
                                                  big_docs=big_docs,
                                                  hidden=hidden,
                                                  deprecated=deprecated,
                                                  confirm=confirm,
                                                  history=history)
            else:
                raise CommandCreateError(f"{name} command is create")
            return func

        return decorator

    def register_sub_module(self,
                            *,
                            Module: Self) -> None:
        """
        Регистрирует под модуль в Модуль
        Args:
            Module: Класс Модуля BaseModule
        Returns:
            None
        """
        if Module.name not in self.pod_modules:
            self.pod_modules[Module.name] = Module
        else:
            raise SubModuleCreateError(f"{Module.name} sub-module is create")
