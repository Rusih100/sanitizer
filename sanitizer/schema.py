from __future__ import annotations

from typing import TYPE_CHECKING, get_type_hints

from sanitizer.exceptions import FieldValidationError, ValidationError

if TYPE_CHECKING:
    from typing import Any, Self


# TODO: Roadmap
#   1. Добавить поддержку списков и т.д
#   2. Изобрести валидатор
#   3. Написать тесты


type FieldName = str
type FieldValue = Any

type FieldsMapping = dict[FieldName, FieldValue]
type TypeHintsMapping = dict[FieldName, Any]


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
    def validate(cls, fields: FieldsMapping) -> Self:
        """
        Метод для валидации входных данных. Возвращает готовый экземпляр схемы.

        :raise ValidationError: Ошибка валидации схемы.
        """

        return cls(**fields)

    @classmethod
    def _validate(cls, fields: FieldsMapping) -> tuple[FieldsMapping, list[FieldValidationError]]:
        """
        Базовый метод для валидации и нормализации переданной сущности по заданным type hints в схеме.

        :returns: Словарь нормализованных данных, список ошибок
        """

        errors: list[FieldValidationError] = []
        type_hints = get_type_hints(cls)

        errors += cls._validate_missing_fields(fields, type_hints)
        errors += cls._validate_disallowed_fields(fields, type_hints)
        validated_fields, errors = cls._validate_allowed_fields(fields, type_hints)

        return validated_fields, errors

    @staticmethod
    def _validate_missing_fields(fields: FieldsMapping, type_hints: TypeHintsMapping) -> list[FieldValidationError]:
        """
        Метод для валидации пропущенных полей схемы.
        """

        errors: list[FieldValidationError] = []
        missing_fields: set[FieldName] = type_hints.keys() - fields.keys()

        for field in missing_fields:
            errors.append(
                FieldValidationError(
                    field=field,
                    message="Обязательное поле не передано",
                    location=[field],
                )
            )
        return errors

    @staticmethod
    def _validate_disallowed_fields(fields: FieldsMapping, type_hints: TypeHintsMapping) -> list[FieldValidationError]:
        """
        Метод для валидации неразрешенных полей схемы.
        """

        errors: list[FieldValidationError] = []
        disallowed_fields: set[FieldName] = fields.keys() - type_hints.keys()

        for field in disallowed_fields:
            errors.append(
                FieldValidationError(
                    field=field,
                    message="Поле не предусмотрено схемой",
                    location=[field],
                )
            )
        return errors

    @staticmethod
    def _validate_allowed_fields(
        fields: FieldsMapping, type_hints: TypeHintsMapping
    ) -> tuple[FieldsMapping, list[FieldValidationError]]:
        """
        Метод для валидации разрешенных полей схемы.
        """

        errors: list[FieldValidationError] = []
        allowed_fields: set[FieldName] = type_hints.keys() & fields.keys()
        validated_fields: FieldsMapping = {}

        for field in allowed_fields:
            value = fields[field]
            expected_type = type_hints[field]

            if issubclass(expected_type, Schema):
                if isinstance(value, expected_type):
                    validated_fields[field] = value
                    continue

                if isinstance(value, dict):
                    try:
                        validated_fields[field] = expected_type(**value)
                        continue
                    except ValidationError as group:
                        for exc in group.exceptions:
                            errors.append(
                                FieldValidationError(
                                    field=exc.field,
                                    message=exc.message,
                                    location=[field, *exc.location],
                                )
                            )
                        continue

                errors.append(
                    FieldValidationError(
                        field=field,
                        message=f"Ожидался {expected_type.__name__} или dict, передано {type(value).__name__}",
                        location=[field],
                    )
                )
                continue

            if not isinstance(value, expected_type):
                errors.append(
                    FieldValidationError(
                        field=field,
                        message=f"Ожидалось {expected_type.__name__}, передано {type(value).__name__}",
                        location=[field],
                    )
                )
                continue

            validated_fields[field] = value

        return validated_fields, errors
