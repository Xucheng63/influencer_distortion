import asyncio

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def test_analyze_runs_to_done(client, monkeypatch):
    async def fake_run(platform, handle, cookies, max_posts, on_progress):
        on_progress(1, 1)
        return {
            "account": {"handle": handle, "display_name": "H", "platform": platform},
            "profile": {
                "distortion_index": 42,
                "total_posts_analyzed": 1,
                "significance_inflation_rate": 0.1,
                "anxiety_manufacturing_rate": 0.0,
                "novelty_claim_rate": 0.0,
                "loaded_language_rate": 0.0,
                "temporal_distortion_rate": 0.0,
            },
            "posts": [
                {
                    "content": "x",
                    "posted_at": "2026-01-01T00:00:00",
                    "distortion_types": ["inflate"],
                    "confidence": 0.9,
                    "classification_method": "rules_v2",
                    "trigger_signals": [],
                }
            ],
        }

    monkeypatch.setattr("app.services.jobs.run_analysis", fake_run)

    start = await client.post(
        "/analyze", json={"platform": "bluesky", "handle": "a.bsky.social"}
    )
    assert start.status_code == 200
    job_id = start.json()["job_id"]

    r = None
    for _ in range(50):
        r = (await client.get(f"/analyze/{job_id}")).json()
        if r["status"] in ("done", "error"):
            break
        await asyncio.sleep(0.02)

    assert r["status"] == "done"
    assert r["result"]["profile"]["distortion_index"] == 42
    assert r["progress"] == {"done": 1, "total": 1}


async def test_unknown_job_id_returns_error(client):
    r = (await client.get("/analyze/does-not-exist")).json()
    assert r["status"] == "error"
    assert r["error"] == "unknown job"
    assert r["result"] is None


async def test_analyze_reports_error_when_run_raises(client, monkeypatch):
    async def boom(platform, handle, cookies, max_posts, on_progress):
        raise RuntimeError("scrape blew up")

    monkeypatch.setattr("app.services.jobs.run_analysis", boom)

    start = await client.post(
        "/analyze", json={"platform": "bluesky", "handle": "a.bsky.social"}
    )
    job_id = start.json()["job_id"]

    r = None
    for _ in range(50):
        r = (await client.get(f"/analyze/{job_id}")).json()
        if r["status"] in ("done", "error"):
            break
        await asyncio.sleep(0.02)

    assert r["status"] == "error"
    assert "scrape blew up" in r["error"]
    assert r["result"] is None
