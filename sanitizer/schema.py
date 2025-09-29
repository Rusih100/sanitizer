from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, get_args, get_origin, get_type_hints

from sanitizer.exceptions import FieldValidationError, ValidationError

if TYPE_CHECKING:
    from typing import Self


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

        values, errors = type(self)._run_validation(fields)

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
    def _run_validation(cls, fields: FieldsMapping) -> tuple[FieldsMapping, list[FieldValidationError]]:
        """
        Базовый метод для валидации и нормализации переданной сущности по заданным type hints в схеме.

        :returns: Словарь нормализованных данных, список ошибок
        """

        errors: list[FieldValidationError] = []
        type_hints = get_type_hints(cls, include_extras=True)

        errors += cls._validate_missing_fields(fields, type_hints)
        errors += cls._validate_disallowed_fields(fields, type_hints)

        validated_fields, fields_errors = cls._validate_allowed_fields(fields, type_hints)
        errors += fields_errors

        return validated_fields, errors

    @staticmethod
    def _validate_missing_fields(fields: FieldsMapping, type_hints: TypeHintsMapping) -> list[FieldValidationError]:
        """
        Метод для валидации пропущенных полей схемы.

        :returns: Список ошибок валидации
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

        :returns: Список ошибок валидации
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

        :returns: Нормализованные значения полей, список ошибок валидации
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

    @classmethod
    def _check_field_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | ellipsis, list[FieldValidationError]]:
        """
        Метод для проверки на соответствие типов и нормализации конкретного типов полей:
            - Any
            - Скалярные значения: (int, float, str, bool, и т.д.)
            - Schema
            - Списки

        Если поле провалидировано с ошибкой будет проставлен ellipsis (...)

        :returns: Нормализованное значение для поля, список ошибок валидации
        """

        # Проверка на Any
        if expected_type is Any:
            return cls._resolve_any_type(field, value, expected_type)

        # Проверка кастомных валидаторов
        if get_origin(expected_type) is Annotated:
            return cls._resolve_validators(field, value, expected_type)

        # Проверка на списки
        if get_origin(expected_type) is list:
            return cls._resolve_list_type(field, value, expected_type)

        # Проверка на неподдерживаемые сложные типы
        if get_origin(expected_type) is not None or not isinstance(expected_type, type):
            return cls._resolve_unsupported_type(field, value, expected_type)

        # Проверка вложенных схем
        if issubclass(expected_type, Schema):
            return cls._resolve_schema_type(field, value, expected_type)

        # Проверка обычные типов
        if not isinstance(value, expected_type):
            return cls._resolve_scalar_type(field, value, expected_type)

        return value, []

    @classmethod
    def _resolve_any_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | ellipsis, list[FieldValidationError]]:
        """
        Резолвер для типа Any.

        Логика:
            - Любое переданное значение считается валидным, без проверки типа.
            - Значение возвращается в исходном виде.
            - Ошибки валидации не формируются никогда.

        :returns: Нормализованное значение для поля, список ошибок валидации
        """

        return value, []

    @classmethod
    def _resolve_list_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | ellipsis, list[FieldValidationError]]:
        """
        Резолвер для списков.

        Логика:
            - Проверяет, что значение является list.
            - Извлекает ожидаемый тип элементов из аннотации list[T].
            - Каждый элемент списка рекурсивно валидируется через _check_field_type.
            - При ошибках у дочерних элементов их location дополняется индексом списка.

        :returns: Нормализованное значение для поля, список ошибок валидации
        """

        item_type = get_args(expected_type)[0]

        if not isinstance(value, list):
            return ..., [
                FieldValidationError(
                    field=field,
                    message=f"Ожидался список {expected_type!r}, получено {type(value).__name__}",
                    location=[field],
                )
            ]

        validated_list: list[Any] = []
        errors: list[FieldValidationError] = []

        for index, item in enumerate(value):
            validated_item, item_errors = cls._check_field_type(field, item, item_type)
            if item_errors:
                for error in item_errors:
                    error.location.insert(1, index)
                errors.extend(item_errors)
                validated_list.append(...)
            else:
                validated_list.append(validated_item)

        return validated_list, errors

    @classmethod
    def _resolve_unsupported_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | ellipsis, list[FieldValidationError]]:
        """
        Резолвер-заглушка для неподдержанных типов.

        Логика:
            - Вызывается, если аннотация поля относится к generic или конструкциям typing,
              которые ещё не реализованы (например, Union, Dict, Tuple, Annotated и т.п.).
            - Всегда возвращает ellipsis вместо значения.
            - Формирует единственную ошибку FieldValidationError с указанием,
              что данный тип не поддерживается.

        :returns: Нормализованное значение для поля, список ошибок валидации
        """

        return ..., [
            FieldValidationError(
                field=field,
                message=f"Переданный тип не поддерживается: {expected_type!r}",
                location=[field],
            )
        ]

    @classmethod
    def _resolve_schema_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | ellipsis, list[FieldValidationError]]:
        """
        Резолвер для вложенных схем (подклассов Schema).

        Логика:
            - Если значение уже является экземпляром ожидаемой схемы — возвращается как есть.
            - Если значение является dict — выполняется попытка сконструировать
              экземпляр expected_type(**dict).
            - При возникновении ValidationError из дочерней схемы ошибки разворачиваются
              в список FieldValidationError с добавлением текущего поля в location.
            - Если значение не соответствует ожидаемому формату, возвращается ошибка

        :returns: Нормализованное значение для поля, список ошибок валидации
        """

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

        return ..., [
            FieldValidationError(
                field=field,
                message=f"Ожидались dict или {expected_type.__name__}; передано {type(value).__name__}",
                location=[field],
            )
        ]

    @classmethod
    def _resolve_scalar_type(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | ellipsis, list[FieldValidationError]]:
        """
        Резолвер для скалярных и произвольных классовых типов.

        Логика:
            - Сюда попадает значение, если expected_type является классом
              (int, str, float, bool или любой другой класс),
              но isinstance(value, expected_type) вернул False.
            - Формируется единичная ошибка FieldValidationError с указанием
              ожидаемого и фактического типа.
            - Всегда возвращается ellipsis вместо значения.

        :returns: Нормализованное значение для поля, список ошибок валидации
        """

        return ..., [
            FieldValidationError(
                field=field,
                message=f"Ожидалось {expected_type.__name__}, передано {type(value).__name__}",
                location=[field],
            )
        ]

    @classmethod
    def _resolve_validators(
        cls, field: FieldName, value: FieldValue, expected_type: Any
    ) -> tuple[FieldValue | ellipsis, list[FieldValidationError]]:
        """
        Резолвер для кастомных валидаторов через Annotate

        :returns: Нормализованное значение для поля, список ошибок валидации
        """

        base_type, *validators = get_args(expected_type)
        value, errors = cls._check_field_type(field, value, base_type)

        if errors:
            return ..., errors

        validator_errors: list[FieldValidationError] = []
        for validator in validators:
            try:
                value = validator(value)
            except Exception as exc:
                validator_errors.append(
                    FieldValidationError(
                        field=field,
                        message=f"Ошибка валидатора {validator.__name__}: {exc}",
                        location=[field],
                    )
                )

        if validator_errors:
            return ..., validator_errors

        return value, []
