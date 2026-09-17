"""Tests for the optional Reddit login fallback."""

from app.services import scraper


class _FakePage:
    """Minimal Playwright page double; records fills/presses, drives page.url."""

    def __init__(self, after_login_url: str = "https://www.reddit.com/") -> None:
        self.url = "https://www.reddit.com/login/"
        self._after = after_login_url
        self.filled: dict[str, str] = {}
        self.pressed: list[str] = []

    def goto(self, url: str, **_kw) -> None:
        self.url = url

    def fill(self, selector: str, value: str, **_kw) -> None:
        self.filled[selector] = value

    def press(self, selector: str, key: str, **_kw) -> None:
        self.pressed.append(key)
        # Simulate the post-submit navigation off the login page.
        self.url = self._after

    def wait_for_load_state(self, *_a, **_kw) -> None:
        pass


def test_reddit_login_noops_without_creds(monkeypatch):
    monkeypatch.delenv("REDDIT_USERNAME", raising=False)
    monkeypatch.delenv("REDDIT_PASSWORD", raising=False)
    page = _FakePage()
    assert scraper._reddit_login(page) is False
    # Never touched the form when creds are unset.
    assert page.filled == {}


def test_reddit_login_drives_form_and_succeeds(monkeypatch):
    monkeypatch.setenv("REDDIT_USERNAME", "test-reddit-user")
    monkeypatch.setenv("REDDIT_PASSWORD", "secret")
    page = _FakePage(after_login_url="https://www.reddit.com/")
    assert scraper._reddit_login(page) is True
    assert page.filled['input[name="username"]'] == "test-reddit-user"
    assert page.filled['input[name="password"]'] == "secret"
    assert "Enter" in page.pressed


def test_reddit_login_reports_failure_when_still_on_login(monkeypatch):
    monkeypatch.setenv("REDDIT_USERNAME", "test-reddit-user")
    monkeypatch.setenv("REDDIT_PASSWORD", "secret")
    page = _FakePage(after_login_url="https://www.reddit.com/login/?error=1")
    assert scraper._reddit_login(page) is False


def test_login_wall_detector():
    class P:
        url = "https://www.reddit.com/login/?dest=/r/foo"

    assert scraper._reddit_page_is_login_wall(P()) is True

    class Q:
        url = "https://www.reddit.com/r/foo/top/?t=month"

    assert scraper._reddit_page_is_login_wall(Q()) is False
