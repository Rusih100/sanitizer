"""
Пример базового создания и использования схем с помощью стандартного конструктора
"""

from sanitizer import Schema


class Human(Schema):
    name: str
    surname: str
    age: int


Human(
    sd=23,  # Необъявленное поле
    surname=3.3,  # Некорректный тип
    # Пропущено поле age
)
