"""The one and only JSON shape. Key order here is the order clients see."""

from pydantic import BaseModel


class Widget(BaseModel):
    meow: str
    now: str
    weekday: str
    cat: str
    weather: str
    fortune: str
