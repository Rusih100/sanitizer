"""
Пример создания и использования кастомных валидаторов.
"""

import re
from typing import Annotated

from sanitizer import Schema

RUSSIAN_PHONE_CLEANER = re.compile(r"\D+")


def russian_phone_validator(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Номер телефона должен быть строкой")

    digits = RUSSIAN_PHONE_CLEANER.sub("", value)

    if digits.startswith("8"):
        digits = "7" + digits[1:]
    elif digits.startswith("7"):
        pass
    elif digits.startswith("+7"):
        digits = digits[1:]
    else:
        raise ValueError("Номер должен начинаться с 8 или +7")

    if len(digits) != 11 or not digits.isdigit():
        raise ValueError("Номер телефона должен содержать 11 цифр")

    return digits


def min_age_validator(age: int) -> int:
    if age < 10:
        raise ValueError("age must be at least 10")
    return age


class Person(Schema):
    name: str
    age: Annotated[int, min_age_validator]
    phone: Annotated[str, russian_phone_validator]


person = Person.validate(
    {
        "name": "Ruslan",
        "age": 23,
        "phone": "8 (950) 288-56-23",
    }
)

print(person.name)  # noqa
print(person.age) # noqa
print(person.phone) # noqa