"""Ease-hover-act ordering tests with a fake page (no browser).

Proves fill_first reaches the element via trajectory scroll, then a
hover move, and only then fills. An instant jump
(scroll_into_view_if_needed) must never fire on the happy path.
"""
import asyncio
import pytest
from reddit_camofox_client.domain_camofox import interactions


class FakeMouse:
    def __init__(self, log):
        self.log = log

    async def move(self, x, y):
        self.log.append("mouse.move")

    async def wheel(self, dx, dy):
        self.log.append("wheel")


class FakeLocator:
    def __init__(self, log):
        self.log = log
        self.first = self

    async def count(self):
        return 1

    async def is_visible(self):
        return True

    async def wait_for(self, **kwargs):
        self.log.append("wait_for")

    async def evaluate(self, js, *args):
        if "isWindow" in js:
            return {"isWindow": True}
        if "r.top >= 0" in js:
            self.log.append("visible-check")
            return True
        self.log.append("target-measure")
        return 500

    async def bounding_box(self):
        return {"x": 0, "y": 400, "width": 100, "height": 20}

    async def scroll_into_view_if_needed(self, **kwargs):
        self.log.append("jump")

    async def fill(self, value):
        self.log.append("fill")

    async def click(self, **kwargs):
        self.log.append("click")

    async def element_handle(self):
        return object()


class FakePage:
    viewport_size = {"width": 1280, "height": 800}

    def __init__(self, log):
        self.log = log
        self.mouse = FakeMouse(log)

    def locator(self, selector):
        return FakeLocator(self.log)

    async def evaluate(self, js):
        if js == "window.scrollY":
            return 0
        return 1000


def run(coro):
    return asyncio.run(coro)


def _assert_ease_hover_act(log: list, act: str) -> None:
    assert "wheel" in log, log
    assert "mouse.move" in log, log
    assert "jump" not in log, log
    act_i = log.index(act)
    last_wheel = max(i for i, x in enumerate(log) if x == "wheel")
    hover = [i for i, x in enumerate(log) if x == "mouse.move" and last_wheel < i < act_i]
    assert hover, f"no hover move between last wheel and {act}: {log}"


def test_fill_follows_ease_hover_act():
    log: list = []
    page = FakePage(log)
    assert run(interactions.fill_first(page, ["textarea"], "hi")) is True
    _assert_ease_hover_act(log, "fill")


def test_click_follows_ease_hover_act():
    log: list = []
    page = FakePage(log)
    assert run(interactions.click_first(page, ["button"])) is True
    _assert_ease_hover_act(log, "click")
