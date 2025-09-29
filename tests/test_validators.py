from __future__ import annotations

from typing import Annotated, Any

import pytest

from sanitizer import Schema, ValidationError


def v_positive_int(x: int) -> int:
    """
    Пропускаем только положительные int
    """
    if x <= 0:
        raise ValueError("должно быть > 0")
    return x


def v_strip(x: str) -> str:
    """
    Тримим строку
    """
    return x.strip()


def v_lower(x: str) -> str:
    """
    Нижний регистр строки
    """
    return x.lower()


def v_non_empty_list(x: list[Any]) -> list[Any]:
    """
    Список не должен быть пустым
    """
    if not x:
        raise ValueError("список пуст")
    return x


def v_max_len_3(x: list[Any]) -> list[Any]:
    """
    Ограничение длины списка ≤ 3
    """
    if len(x) > 3:
        raise ValueError("слишком длинный список")
    return x


def v_even(x: int) -> int:
    """
    Разрешаем только чётные числа
    """
    if x % 2 != 0:
        raise ValueError("нечётное значение")
    return x


class TestAnnotatedScalar:
    """
    Тесты валидаторов для скалярных полей через Annotated[T, validator...].
    Поведение валидаторов и порядок вызова описаны в _resolve_validators:
    - сначала проверяется базовый тип,
    - затем по очереди вызываются валидаторы, при исключении формируется FieldValidationError
      с сообщением 'Ошибка валидатора {name}: {exc}' и location=[field]
    """

    def test_scalar_transform_success(self) -> None:
        """
        Успешная валидация и трансформация значения валидатором.
        """

        class S(Schema):
            field: Annotated[str, v_strip, v_lower]

        s = S(field="  HeLLo  ")
        assert s.field == "hello"

    def test_scalar_validator_error(self) -> None:
        """
        Падение валидатора: сообщение и локация должны соответствовать контракту.
        """

        class S(Schema):
            field: Annotated[int, v_positive_int]

        with pytest.raises(ValidationError) as exc:
            S(field=0)

        err = exc.value.exceptions[0]
        assert "Ошибка валидатора v_positive_int: должно быть > 0" in err.message
        assert err.location == ["field"]

    def test_scalar_type_error_before_validators(self) -> None:
        """
        Если базовый тип не совпал — валидаторы не вызываются (ошибка типа).
        """

        class S(Schema):
            field: Annotated[int, v_positive_int]

        with pytest.raises(ValidationError) as exc:
            S(field="123")

        err = exc.value.exceptions[0]
        assert "Ожидалось int" in err.message
        assert err.location == ["field"]


class TestAnnotatedLists:
    """
    Валидация Annotated для списков:
    - валидатор на уровне списка: Annotated[list[T], validator...]
    - валидатор на уровне элемента: list[Annotated[T, validator...]]
    Вставка индекса элемента делается в _resolve_list_type при прокидывании ошибок дочерних значений.:contentReference[oaicite:2]{index=2}
    """

    def test_list_level_validators_success(self) -> None:
        """
        Валидаторы применяются к целому списку, затем элементы валидируются по базовому типу.
        """

        class S(Schema):
            field: Annotated[list[int], v_non_empty_list, v_max_len_3]

        s = S(field=[1, 2, 3])
        assert s.field == [1, 2, 3]

    def test_list_level_validator_error_empty(self) -> None:
        """
        Ошибка валидатора уровня списка (пустой список запрещён).
        """

        class S(Schema):
            field: Annotated[list[int], v_non_empty_list]

        with pytest.raises(ValidationError) as exc:
            S(field=[])

        err = exc.value.exceptions[0]
        assert "Ошибка валидатора v_non_empty_list: список пуст" in err.message
        assert err.location == ["field"]

    def test_list_item_validators_success(self) -> None:
        """
        Валидатор применяется к каждому элементу через Annotated[int, ...] внутри list.
        """

        class S(Schema):
            field: list[Annotated[int, v_even, v_positive_int]]

        s = S(field=[2, 4, 6])
        assert s.field == [2, 4, 6]

    def test_list_item_validator_error_indexed(self) -> None:
        """
        Ошибки валидаторов элементов должны иметь location с индексом элемента: ['field', idx].
        """

        class S(Schema):
            field: list[Annotated[int, v_even, v_positive_int]]

        with pytest.raises(ValidationError) as exc:
            S(field=[2, 3, -4])

        errors = exc.value.exceptions
        assert len(errors) == 2

        assert errors[0].location == ["field", 1]
        assert "Ошибка валидатора v_even: нечётное значение" in errors[0].message

        assert errors[1].location == ["field", 2]
        assert "Ошибка валидатора v_positive_int: должно быть > 0" in errors[1].message

    def test_list_root_type_error(self) -> None:
        """
        Если пришёл не list при Annotated[list[T], ...] — сообщение об ожидании списка.
        """

        class S(Schema):
            field: Annotated[list[int], v_non_empty_list]

        with pytest.raises(ValidationError) as exc:
            S(field="not-a-list")

        err = exc.value.exceptions[0]
        assert "Ожидался список" in err.message
        assert err.location == ["field"]
