from .base_api_error import ApiError


class ModuleError(ApiError):
    """
    Базовый класс для исключений Методов
    """


class ModuleCreateError(ModuleError):
    """
    Класс ошибки загрузки модуля
    """


class SubModuleCreateError(ModuleCreateError):
    """
    Класс ошибки загрузки под-модуля
    """
