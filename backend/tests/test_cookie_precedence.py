"""Request-provided cookies must win over the sidecar's own env cookies.

This is what lets the gateway inject freshly dev-refreshed cookies (from Redis)
without a redeploy: they arrive in the request body and take precedence over the
stale TWITTER_*/WEIBO_* values baked into the sidecar environment.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def test_test_connection_prefers_request_cookies_over_env(client, monkeypatch):
    monkeypatch.setenv("TWITTER_AUTH_TOKEN", "stale")
    monkeypatch.setenv("TWITTER_CT0", "stale")
    seen = {}

    async def fake_probe(platform, cookies):
        seen.update(cookies)
        return True, "Connected"

    monkeypatch.setattr("app.api.analyze_routes.probe_connection", fake_probe)
    await client.post(
        "/test-connection",
        json={"platform": "twitter", "cookies": {"auth_token": "fresh", "ct0": "new"}},
    )
    assert seen == {"auth_token": "fresh", "ct0": "new"}


async def test_test_connection_falls_back_to_env_when_no_request_cookies(
    client, monkeypatch
):
    monkeypatch.setenv("TWITTER_AUTH_TOKEN", "envtok")
    monkeypatch.setenv("TWITTER_CT0", "envct0")
    seen = {}

    async def fake_probe(platform, cookies):
        seen.update(cookies)
        return True, "Connected"

    monkeypatch.setattr("app.api.analyze_routes.probe_connection", fake_probe)
    await client.post("/test-connection", json={"platform": "twitter", "cookies": {}})
    assert seen == {"auth_token": "envtok", "ct0": "envct0"}


async def test_analyze_prefers_request_cookies_over_env(client, monkeypatch):
    monkeypatch.setenv("WEIBO_SUB", "stale")
    monkeypatch.setenv("WEIBO_SUBP", "stale")
    captured = {}

    def fake_start_job(platform, handle, cookies, max_posts):
        captured["cookies"] = cookies
        return "job-1"

    monkeypatch.setattr("app.api.analyze_routes.jobs.start_job", fake_start_job)
    r = await client.post(
        "/analyze",
        json={
            "platform": "weibo",
            "handle": "1669879400",
            "cookies": {"sub": "fresh", "subp": "new"},
        },
    )
    assert r.json() == {"job_id": "job-1"}
    assert captured["cookies"] == {"sub": "fresh", "subp": "new"}
