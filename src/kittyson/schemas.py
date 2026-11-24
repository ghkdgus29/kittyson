"""The JSON the clients get. Key order here is the order they see."""

from datetime import date

from pydantic import BaseModel

from kittyson.theme import Theme


class Widget(BaseModel):
    """The lines on the screen: every key here is drawn, in this order."""

    time: str
    date: str
    weekday: str
    weather: str
    quote: str
    by: str


class TodayCat(BaseModel):
    """The cat whose photo /cat/today.jpg hands out."""

    day: date       # the day it was made for. A new day here means a new photo to fetch
    source: str
    theme: Theme    # the text colors that read well over the photo


class Today(BaseModel):
    """Everything a client needs but the photo itself."""

    widget: Widget
    cat: TodayCat | None  # None until the first cat is made
