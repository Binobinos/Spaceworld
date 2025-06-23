import inspect
from typing import Optional, Union, List


class BaseCommand:
    """
    Базовый класс Команды SpaceWorld
    """
    __slots__: List[str] = ["name", "alias", "func", "docs", "big_docs", "example",
                            "activate_mode", "hidden", "deprecated", "confirm", "history"]

    def __init__(self,
                 *,
                 name: str,
                 alias: Optional[List[str]] = None,
                 docs: Optional[str] = None,
                 example: str = "",
                 activate_modes: Union[str, List[str]],
                 func: callable,
                 big_docs: Optional[str] = None,
                 hidden: bool = False,
                 deprecated: Union[bool, str] = False,
                 confirm: Union[bool, str] = False,
                 history: bool = True) -> None:
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
        self.name: str = name
        self.alias: Optional[List[str]] = alias
        self.func: callable = func
        self.docs = inspect.getdoc(self.func) if docs is None or docs == "" else docs
        self.big_docs: str = big_docs if not (big_docs is None) else self.docs
        self.example = example
        self.activate_mode: str = [activate_modes] if isinstance(activate_modes, str) else activate_modes

        self.hidden: bool = hidden
        self.deprecated: Union[bool, str] = deprecated
        self.confirm: Union[bool, str] = confirm
        self.history: bool = history

    def get_help_doc(self) -> str:
        return "\n".join([item for item in (f"Name: {self.name}",
                                            f"Alias: {", ".join(self.alias)}" if not (
                                                    self.alias is None) else "",
                                            f"Docs: {self.big_docs}",
                                            f"Example: {self.example}" if self.example else "",
                                            f"Modes: {", ".join([mod.capitalize() for mod in self.activate_mode])}",
                                            f"Args: \n{self._get_args_info()}\n"
                                            f"Hidden: {"YES" if self.hidden else "NO"}",
                                            f"Deprecated: {"YES" if self.deprecated else "NO"}" if isinstance(
                                                self.deprecated, bool) else
                                            f"Deprecated the message: {self.deprecated}",
                                            f"Confirmation Is required: {"YES" if self.confirm else "NO"}" if isinstance(
                                                self.confirm,
                                                bool) else
                                            f"Confirming the message: {self.confirm}") if item])

    def _get_args_info(self) -> str:
        return "\n".join([f"    {param}" for param in inspect.signature(self.func).parameters.values()])

