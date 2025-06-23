from .base_api_error import ApiError


class CommandError(ApiError):
    """
    Базовый класс для исключений методов класса команд
    """


class CommandCreateError(CommandError):
    """
    Класс ошибки загрузки команд
    """
