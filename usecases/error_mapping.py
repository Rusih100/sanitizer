"""
Пример создания сложных схем и сопоставления ошибок.
"""

from pprint import pprint

from sanitizer import Schema, ValidationError


class User(Schema):
    nickname: str
    phone: str
    coins: list[int]


class Storage(Schema):
    users: list[User]


try:
    storage = Storage.validate(
        {
            "users": [
                {
                    "nickname": "Ivan",
                    "phone": "79008008080",
                    "coins": [
                        1,
                        2,
                        "Str",  # Некорректный тип
                    ],
                },
                {
                    "nickname": "Oleg",
                    # Пропущены поля phone и coins
                },
                1,  # Некорректный тип
            ],
        }
    )
except ValidationError as exc:
    pprint(  # noqa T203
        [
            {
                "field": error.message,
                "message": error.message,
                "location": error.location,
            }
            for error in exc.exceptions
        ]
    )
