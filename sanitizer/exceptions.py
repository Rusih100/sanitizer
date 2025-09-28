from __future__ import annotations


class ValidationError(ExceptionGroup):
    """
    Исключение (Группа исключений), описывающая ошибки валидации.
    """

    pass


class FieldValidationError(Exception):
    """
    Исключение, описывающее ошибку валидации данных для конкретного поля схемы.
    """

    def __init__(self, field: str, message: str) -> None:
        self.field: str = field
        self.message: str = message
