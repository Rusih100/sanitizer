import pytest

from sanitizer import Schema, ValidationError


class TestListType:
    """
    Группа тестов на валидацию списков: списки скаляров, списки схем, вложенные списки,
    поведение Any, множественные ошибки и неверный корневой тип.
    """

    @pytest.mark.parametrize(
        "value",
        [
            [1, 2, 3],
            [],
            [10**6, 0, -5],
        ],
    )
    def test_list_of_int_success(self, value: list[int]) -> None:
        """
        Успешная валидация list[int].
        """

        class S(Schema):
            field: list[int]

        s = S(field=value)
        assert s.field == value
        assert all(isinstance(x, int) for x in s.field)

    @pytest.mark.parametrize(
        "value",
        [
            ["a", "b", "c"],
            [],
            ["", "текст", "ユニコード"],
        ],
    )
    def test_list_of_str_success(self, value: list[str]) -> None:
        """
        Успешная валидация list[str].
        """

        class S(Schema):
            field: list[str]

        s = S(field=value)
        assert s.field == value
        assert all(isinstance(x, str) for x in s.field)

    def test_list_of_int_with_invalid_element(self) -> None:
        """
        Ошибка, если один из элементов не int.
        Ожидаем корректную вставку индекса элемента в location: ["field", <idx>].
        """

        class S(Schema):
            field: list[int]

        with pytest.raises(ValidationError) as exc:
            S(field=[1, "bad", 3])

        errors = exc.value.exceptions
        assert len(errors) == 1, "Должна быть одна ошибка"
        assert "Ожидалось int" in errors[0].message
        assert errors[0].location == ["field", 1]

    def test_list_of_str_multiple_invalids(self) -> None:
        """
        Несколько ошибок в разных индексах в list[str].
        Проверяем, что обе ошибки имеют корректные локации.
        """

        class S(Schema):
            field: list[str]

        with pytest.raises(ValidationError) as exc:
            S(field=["ok", 123, 4.5, "also ok"])

        errors = exc.value.exceptions

        assert len(errors) == 2
        assert errors[0].location == ["field", 1]
        assert "Ожидалось str" in errors[0].message
        assert errors[1].location == ["field", 2]
        assert "Ожидалось str" in errors[1].message

    def test_invalid_list_root_type(self) -> None:
        """
        Ошибка, если пришёл не список, когда ожидается list[T].
        """

        class S(Schema):
            field: list[int]

        with pytest.raises(ValidationError) as exc:
            S(field="not-a-list")

        error = exc.value.exceptions[0]
        assert "Ожидался список" in error.message
        assert error.location == ["field"]

    def test_list_of_schema_success(self) -> None:
        """
        Успешная валидация списка вложенных схем.
        """

        class Item(Schema):
            sku: str
            qty: int

        class Order(Schema):
            items: list[Item]

        order = Order(items=[{"sku": "A1", "qty": 2}, {"sku": "B2", "qty": 5}])

        assert all(isinstance(i, Item) for i in order.items)
        assert order.items[0].sku == "A1"
        assert order.items[1].qty == 5

    def test_list_of_schema_with_child_errors(self) -> None:
        """
        Ошибка валидации во вложенной схеме внутри списка.
        Дочерние ошибки должны «разворачиваться» с добавлением индекса: ["items", idx, <child_field>].
        """

        class Item(Schema):
            sku: str
            qty: int

        class Order(Schema):
            items: list[Item]

        with pytest.raises(ValidationError) as exc:
            Order(items=[{"sku": "A1", "qty": "bad"}, {"sku": 123, "qty": 10}])

        errors = exc.value.exceptions
        assert len(errors) == 2
        assert errors[0].location == ["items", 0, "qty"]
        assert "Ожидалось int" in errors[0].message
        assert errors[1].location == ["items", 1, "sku"]
        assert "Ожидалось str" in errors[1].message

    def test_nested_lists_success(self) -> None:
        """
        Успешная валидация вложенных списков: list[list[int]].
        """

        class S(Schema):
            field: list[list[int]]

        s = S(field=[[1, 2], [], [3]])
        assert s.field == [[1, 2], [], [3]]
        assert all(isinstance(x, list) for x in s.field)
        assert all(all(isinstance(v, int) for v in row) for row in s.field)

    def test_nested_lists_with_errors(self) -> None:
        """
        Ошибки внутри вложенных списков: list[list[int]].
        Должны корректно проставляться обе координаты: ["field", i, j].
        """

        class S(Schema):
            field: list[list[int]]

        with pytest.raises(ValidationError) as exc:
            S(field=[[1, "bad"], ["also", "bad"], [3]])

        errors = exc.value.exceptions
        assert len(errors) == 3
        assert errors[0].location == ["field", 0, 1]
        assert "Ожидалось int" in errors[0].message
        assert errors[1].location == ["field", 1, 0]
        assert "Ожидалось int" in errors[1].message
        assert errors[2].location == ["field", 1, 1]
        assert "Ожидалось int" in errors[2].message

    @pytest.mark.parametrize(
        "value",
        [
            [1, "two", 3.14, {"k": "v"}, [5, 6]],
            [],
        ],
    )
    def test_list_of_any(self, value: list) -> None:
        """
        Для list[Any] элементы не типизируются и возвращаются как есть.
        """

        from typing import Any

        class S(Schema):
            field: list[Any]

        s = S(field=value)
        assert s.field == value
