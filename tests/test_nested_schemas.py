import pytest

from sanitizer import Schema, ValidationError


class TestNestedSchemas:
    """
    Группа тестов на вложенные структуры (Schema в Schema, списки Schema).
    """

    def test_success_nested_schema(self) -> None:
        """
        Успешная валидация вложенной схемы.
        """

        class Address(Schema):
            city: str
            zip_code: int

        class User(Schema):
            id: int
            address: Address

        user = User(
            id=1,
            address={"city": "Moscow", "zip_code": 101000}
        )

        assert isinstance(user.address, Address), "address должен быть экземпляром Address"
        assert user.address.city == "Moscow"
        assert user.address.zip_code == 101000

    def test_invalid_type_in_nested_schema(self) -> None:
        """
        Ошибка при некорректном типе во вложенной схеме.
        """

        class Address(Schema):
            city: str
            zip_code: int

        class User(Schema):
            id: int
            address: Address

        with pytest.raises(ValidationError) as exc:
            User(id=1, address={"city": "Moscow", "zip_code": "bad"})

        error = exc.value.exceptions[0]
        assert "Ожидалось int" in error.message
        assert error.location == ["address", "zip_code"]

    def test_list_of_nested_schemas_success(self) -> None:
        """
        Успешная валидация списка вложенных схем.
        """

        class Item(Schema):
            sku: str
            qty: int

        class Order(Schema):
            items: list[Item]

        order = Order(
            items=[
                {"sku": "A1", "qty": 2},
                {"sku": "B2", "qty": 5},
            ]
        )

        assert all(isinstance(i, Item) for i in order.items)
        assert order.items[0].sku == "A1"
        assert order.items[1].qty == 5

    def test_list_of_nested_schemas_with_errors(self) -> None:
        """
        Ошибка валидации при неправильных данных в списке вложенных схем.
        """

        class Item(Schema):
            sku: str
            qty: int

        class Order(Schema):
            items: list[Item]

        with pytest.raises(ValidationError) as exc:
            Order(
                items=[
                    {"sku": "A1", "qty": "bad"},
                    {"sku": 123, "qty": 10},
                ]
            )

        errors = exc.value.exceptions
        assert len(errors) == 2
        assert errors[0].location == ["items", 0, "qty"]
        assert "Ожидалось int" in errors[0].message
        assert errors[1].location == ["items", 1, "sku"]
        assert "Ожидалось str" in errors[1].message

    def test_invalid_list_type(self) -> None:
        """
        Ошибка, если поле объявлено как список, но пришёл не список.
        """

        class Item(Schema):
            sku: str

        class Order(Schema):
            items: list[Item]

        with pytest.raises(ValidationError) as exc:
            Order(items="not-a-list")

        error = exc.value.exceptions[0]
        assert "Ожидался список" in error.message
        assert error.location == ["items"]
