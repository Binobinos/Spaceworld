from exceptions.spaceworld_error import SpaceWorldError


class ApiError(SpaceWorldError, Exception):
    """
    Базовый класс для Api SpaceWorld
    """


class AnnotationsError(ApiError):
    """
    Ошибка Добавления аннотации
    """
