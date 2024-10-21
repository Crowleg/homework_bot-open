class APIRequestException(Exception):
    """Исключение для ошибок, связанных с запросами к API."""


class ResponseException(Exception):
    """Исключение для ошибок, связанных с некорректным ответом API."""


class SendMessageException(Exception):
    """Исключение для ошибок, связанных с отправкой сообщения."""


class HomeworkStatusException(Exception):
    """Исключение для ошибок, связанных со статусом домашних работ."""


class WrongStatusCode(Exception):
    """Исключение для ошибок, связанных с некорректным статусом ответа."""
