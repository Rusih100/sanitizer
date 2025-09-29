from __future__ import annotations

from typing import TYPE_CHECKING, Any, get_origin, get_type_hints

from sanitizer.exceptions import FieldValidationError, ValidationError

if TYPE_CHECKING:
    from typing import Self


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

        values, errors = type(self)._run_validators(fields)

        for k, v in values.items():
            setattr(self, k, v)

        if errors:
            raise ValidationError(f"{type(self).__name__}: validation failed", errors)

    @classmethod
    def validate(cls, fields: FieldsMapping) -> Self:
        """
        Метод для валидации входных данных. Возвращает готовый экземпляр схемы.

        :raise ValidationError: Ошибка валидации схемы.
        """

        return cls(**fields)

    @classmethod
    def _run_validators(cls, fields: FieldsMapping) -> tuple[FieldsMapping, list[FieldValidationError]]:
        """
        Базовый метод для валидации и нормализации переданной сущности по заданным type hints в схеме.

        :returns: Словарь нормализованных данных, список ошибок
        """

        errors: list[FieldValidationError] = []
        type_hints = get_type_hints(cls)

        errors += cls._validate_missing_fields(fields, type_hints)
        errors += cls._validate_disallowed_fields(fields, type_hints)

        validated_fields, fields_errors = cls._validate_allowed_fields(fields, type_hints)
        errors += fields_errors

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

    @classmethod
    def _validate_allowed_fields(
        cls, fields: FieldsMapping, type_hints: TypeHintsMapping
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

            validated_value, validation_errors = cls._check_field_type(field, value, expected_type)

            validated_fields[field] = validated_value
            errors += validation_errors

        return validated_fields, errors

    @staticmethod
    def _check_field_type(
        field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | ellipsis, list[FieldValidationError]]:
        """
        Метод для проверки на соответствие типов и нормализации конкретного типов полей:
        - Any
        - Скалярные значения: (int, float, str, bool, ...)
        - Schema
        - Списки

        Если поле провалидировано с ошибкой будет проставлен ellipsis (...)

        :returns: Нормализованное значение для поля, ошибка валидации при наличии
        """

        # Проверка на Any
        if expected_type is Any:
            return value, []

        # Проверка на сложные typing типы
        if get_origin(expected_type) is not None:
            return ..., [
                FieldValidationError(
                    field=field,
                    message=f"Переданный тип не поддерживается: {expected_type!r}",
                    location=[field],
                )
            ]

        # Проверка, что объект - класс
        if not isinstance(expected_type, type):
            return ..., [
                FieldValidationError(
                    field=field,
                    message=f"Переданный тип является классом: {expected_type!r}",
                    location=[field],
                )
            ]

        # Проверка вложенных схем
        if issubclass(expected_type, Schema):
            if isinstance(value, expected_type):
                return value, []

            if isinstance(value, dict):
                try:
                    return expected_type(**value), []
                except ValidationError as exc:
                    return ..., [
                        FieldValidationError(
                            field=exc.field,
                            message=exc.message,
                            location=[field, *exc.location],
                        )
                        for exc in exc.exceptions
                    ]

        # Обычные типы
        if not isinstance(value, expected_type):
            return ..., [
                FieldValidationError(
                    field=field,
                    message=f"Ожидалось {expected_type.__name__}, передано {type(value).__name__}",
                    location=[field],
                )
            ]

        return value, []

