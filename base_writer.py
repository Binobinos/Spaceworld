from abc import ABC
from typing import Any


class Writer(ABC):
    def write(self, *text: Any) -> None:
        """
        Выводит текст в консоль с возможностью задания цвета и шрифта.
        """

    def info(self, *text: Any) -> None:
        """
        Выводит информацию на экран
        Args:
            *text: Текст вывода
        Returns:
            None
        """

    def warning(self, *text: Any) -> None:
        """
        Выводит предупреждение на экран
        Args:
            *text: Текст предупреждения
        Returns:
            None
        """

    def input_info(self, *text: Any) -> None:
        """
        Выводит состояние ввода из консоли
        Args:
            *text: Текст вопроса
        Returns:
            None
        """

    def error(self, *text: Any) -> None:
        """
        Выводит ошибку на экран
        Args:
            *text: Текст ошибки
        Returns:
            None
        """
