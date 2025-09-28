from sanitizer import Schema


class Helmet(Schema):
    level: int


class Driver(Schema):
    name: str
    helmet: Helmet


class Car(Schema):
    driver: Driver
    speed: int


car = Car.validate(
    {
        "driver": {
            "name": "Ivan",
            "helmet": {
                "level": "1",
            },
        },
        "speed": 100,
    }
)
print(car)  # noqa T201