import inspect
from app.services import scraper


def test_twitter_fetch_takes_cookies_arg():
    sig = inspect.signature(scraper._fetch_twitter)
    assert "cookies" in sig.parameters


def test_twitter_sync_builds_cookies_from_arg(monkeypatch):
    # Prove the cookie list is built from the passed dict, not the environment.
    monkeypatch.delenv("TWITTER_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_CT0", raising=False)
    cookies = scraper._twitter_cookie_list({"auth_token": "A", "ct0": "B"})
    names = {c["name"]: c["value"] for c in cookies}
    assert names["auth_token"] == "A"
    assert names["ct0"] == "B"


def test_weibo_fetch_takes_cookies_arg():
    sig = inspect.signature(scraper._fetch_weibo)
    assert "cookies" in sig.parameters


async def test_resolve_weibo_uid_passthrough_numeric():
    assert await scraper.resolve_weibo_uid("1234567890") == "1234567890"


def test_cookies_for_platform_twitter_from_env(monkeypatch):
    monkeypatch.setenv("TWITTER_AUTH_TOKEN", "tok")
    monkeypatch.setenv("TWITTER_CT0", "ct")
    assert scraper.cookies_for_platform("twitter") == {"auth_token": "tok", "ct0": "ct"}


def test_cookies_for_platform_weibo_from_env(monkeypatch):
    monkeypatch.setenv("WEIBO_SUB", "s")
    monkeypatch.setenv("WEIBO_SUBP", "sp")
    assert scraper.cookies_for_platform("weibo") == {"sub": "s", "subp": "sp"}


def test_cookies_for_platform_empty_when_unset(monkeypatch):
    for var in ("TWITTER_AUTH_TOKEN", "TWITTER_CT0", "WEIBO_SUB", "WEIBO_SUBP"):
        monkeypatch.delenv(var, raising=False)
    assert scraper.cookies_for_platform("twitter") == {}
    assert scraper.cookies_for_platform("weibo") == {}


def test_cookies_for_platform_keyless_is_empty():
    assert scraper.cookies_for_platform("bluesky") == {}
    assert scraper.cookies_for_platform("reddit") == {}
    assert scraper.cookies_for_platform("youtube") == {}
