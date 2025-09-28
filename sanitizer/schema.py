from __future__ import annotations

from typing import TYPE_CHECKING, get_type_hints

from sanitizer.exceptions import FieldValidationError, ValidationError

if TYPE_CHECKING:
    from typing import Any, Self


# TODO: Roadmap
#   OK 1. Сделать нормальную текстовку ошибок
#   OK 2. Реализовать метод _validate
#   3. Добавить поддержку списков и т.д
#   OK 4. Добавить поддержку структур
#   5. Изобрести валидатор
#   6. Написать тесты


type FieldName = str
type FieldValue = Any


class Schema:
    """
    Базовый класс для описания схем данных с использованием аннотаций типов,
    для валидации и нормализации данных.
    """

    def __init__(self, **fields: FieldValue) -> None:
        """
        Базовый конструктор схемы.

        :raise ValidationError: Ошибка валидации схемы.
        """

        values, errors = type(self)._validate(fields)
        if errors:
            raise ValidationError(f"{type(self).__name__}: validation failed", errors)

        for k, v in values.items():
            setattr(self, k, v)

    @classmethod
    def validate(cls, fields: dict[FieldName, FieldValue]) -> Self:
        """
        Метод для валидации входных данных. Возвращает готовый экземпляр схемы.

        :raise ValidationError: Ошибка валидации схемы.
        """

        return cls(**fields)

    @classmethod
    def _validate(
        cls, fields: dict[FieldName, FieldValue]
    ) -> tuple[dict[FieldName, FieldValue], list[FieldValidationError]]:
        """
        Базовый метод для валидации и нормализации переданной сущности по заданным type hints в схеме.

        :returns: Словарь нормализованных данных, список ошибок
        """

        values: dict[FieldName, FieldValue] = {}
        errors: list[FieldValidationError] = []

        type_hints = get_type_hints(cls)

        missing_fields = type_hints.keys() - fields.keys()
        for field in missing_fields:
            errors.append(
                FieldValidationError(
                    field,
                    "Обязательное поле не передано",
                    [field],
                )
            )

        disallowed_fields = fields.keys() - type_hints.keys()
        for field in disallowed_fields:
            errors.append(
                FieldValidationError(
                    field,
                    "Поле не предусмотрено схемой",
                    [field],
                )
            )

        allowed_fields = type_hints.keys() & fields.keys()
        for field in allowed_fields:
            value = fields[field]
            expected_type = type_hints[field]

            if issubclass(expected_type, Schema):
                if isinstance(value, expected_type):
                    values[field] = value
                    continue

                if isinstance(value, dict):
                    try:
                        values[field] = expected_type(**value)
                        continue
                    except ValidationError as group:
                        for exc in group.exceptions:
                            errors.append(
                                FieldValidationError(
                                    exc.field,
                                    exc.message,
                                    [field, *exc.location],
                                )
                            )
                        continue

                errors.append(
                    FieldValidationError(
                        field,
                        f"Ожидался {expected_type.__name__} или dict, передано {type(value).__name__}",
                        [field],
                    )
                )
                continue

            if not isinstance(value, expected_type):
                errors.append(
                    FieldValidationError(
                        field,
                        f"Ожидалось {expected_type.__name__}, передано {type(value).__name__}",
                        [field],
                    )
                )
                continue

            values[field] = value

        return values, errors

