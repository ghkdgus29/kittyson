"""The one and only JSON shape. Key order here is the order clients see."""

from pydantic import BaseModel


class Widget(BaseModel):
    time: str
    date: str
    weekday: str
    weather: str
    quote: str
