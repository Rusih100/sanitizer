from sanitizer import Schema


class Human(Schema):
    name: str
    surname: str
    age: int


print(Human(sd=23, surname=3.3))  # noqa T201