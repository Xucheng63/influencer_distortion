import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def test_keyless_platform_needs_no_cookie(client):
    r = await client.post("/test-connection", json={"platform": "bluesky", "cookies": {}})
    assert r.status_code == 200
    assert r.json()["ok"] is True


async def test_twitter_ok_when_probe_succeeds(client, monkeypatch):
    async def fake_probe(platform, cookies):
        return True, "Connected"
    monkeypatch.setattr("app.api.analyze_routes.probe_connection", fake_probe)
    r = await client.post(
        "/test-connection",
        json={"platform": "twitter", "cookies": {"auth_token": "A", "ct0": "B"}},
    )
    assert r.json() == {"ok": True, "message": "Connected"}


async def test_youtube_keyless_returns_ok(client):
    r = await client.post("/test-connection", json={"platform": "youtube", "cookies": {}})
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert "No connection test needed" in r.json()["message"]


async def test_reddit_keyless_returns_ok(client):
    r = await client.post("/test-connection", json={"platform": "reddit", "cookies": {}})
    assert r.status_code == 200
    assert r.json()["ok"] is True


async def test_twitter_fail_when_probe_raises(client, monkeypatch):
    async def failing_probe(platform, cookies):
        raise RuntimeError("cookie expired")
    monkeypatch.setattr("app.api.analyze_routes.probe_connection", failing_probe)
    r = await client.post(
        "/test-connection",
        json={"platform": "twitter", "cookies": {"auth_token": "bad", "ct0": "bad"}},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is False
    assert "cookie expired" in r.json()["message"]


async def test_weibo_ok_when_probe_succeeds(client, monkeypatch):
    async def fake_probe(platform, cookies):
        return True, "Connected"
    monkeypatch.setattr("app.api.analyze_routes.probe_connection", fake_probe)
    r = await client.post(
        "/test-connection",
        json={"platform": "weibo", "cookies": {"sub": "abc", "subp": "xyz"}},
    )
    assert r.json() == {"ok": True, "message": "Connected"}


async def test_failed_probe_returns_ok_false(client, monkeypatch):
    async def fake_probe(platform, cookies):
        return False, "Connection failed — invalid or expired cookie"
    monkeypatch.setattr("app.api.analyze_routes.probe_connection", fake_probe)
    r = await client.post(
        "/test-connection",
        json={"platform": "twitter", "cookies": {"auth_token": "bad", "ct0": "bad"}},
    )
    assert r.status_code == 200
    assert r.json() == {"ok": False, "message": "Connection failed — invalid or expired cookie"}
