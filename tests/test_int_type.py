import pytest

from sanitizer import Schema, ValidationError


class TestIntType:
    """
    Группа тестов на валидацию скалярного типа int
    """

    @pytest.mark.parametrize(
        "value",
        [
            -123,
            0,
            23,
            1,
            10 ** 15,
        ],
    )
    def test_success(self, value: int) -> None:
        """
        Успешные тесты на валидацию
        """

        class S(Schema):
            field: int

        s = S(field=value)

        assert s.field == value, "check field value"
        assert isinstance(s.field, int), "check field type"

    @pytest.mark.parametrize(
        "value",
        [
            None,
            ...,
            "1234",
            "",
            "123.32",
            0.0,
            34.43,
            [],
            [123, 23],
            (2, 3),
        ],
    )
    def test_invalid_type(self, value: int) -> None:
        """
        Тесты валидацию, при переданном некорректном типе
        """

        class S(Schema):
            field: int

        with pytest.raises(ValidationError) as exc:
            S(field=value)

        error = exc.value.exceptions[0]

        assert len(exc.value.exceptions) == 1, "Check errors count"
        assert "Ожидалось int" in error.message, "Check error message"
        assert error.location == ["field"], "Check error location"
