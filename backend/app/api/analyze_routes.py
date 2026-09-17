# app/api/analyze_routes.py
from fastapi import APIRouter
from pydantic import BaseModel
from app.services import jobs, scraper

router = APIRouter()
KEYLESS = {"youtube", "reddit", "bluesky"}


class TestConnReq(BaseModel):
    platform: str
    cookies: dict[str, str] = {}


async def probe_connection(platform: str, cookies: dict[str, str]) -> tuple[bool, str]:
    """One minimal authenticated fetch to prove the cookie is live."""
    # Both probes target a KNOWN-ACTIVE account (twitter "x"; a known weibo uid),
    # so an empty result genuinely means auth failed — bool(posts) is the signal.
    if platform == "twitter":
        posts = await scraper._fetch_twitter("x", cookies, max_results=1)
        ok = bool(posts)
        return (
            ok,
            "Connected" if ok else "Connection failed — invalid or expired cookie",
        )
    if platform == "weibo":
        uid = await scraper.resolve_weibo_uid("1669879400")
        posts = await scraper._fetch_weibo(uid, cookies, max_posts=1)
        ok = bool(posts)
        return (
            ok,
            "Connected" if ok else "Connection failed — invalid or expired cookie",
        )
    return True, "No connection test needed"


@router.post("/test-connection")
async def test_connection(req: TestConnReq) -> dict:
    if req.platform in KEYLESS:
        return {"ok": True, "message": "No connection test needed"}
    # Request-provided cookies win (the gateway injects freshly dev-refreshed
    # cookies from Redis here); otherwise fall back to the sidecar's own
    # environment (TWITTER_*/WEIBO_*). Tests inject cookies the same way.
    cookies = req.cookies or scraper.cookies_for_platform(req.platform)
    try:
        ok, msg = await probe_connection(req.platform, cookies)
    except Exception as exc:  # cookie invalid / blocked
        return {"ok": False, "message": f"Connection failed: {exc}"}
    return {"ok": ok, "message": msg}


class AnalyzeReq(BaseModel):
    platform: str
    handle: str
    cookies: dict[str, str] = {}
    max_posts: int | None = None


@router.post("/analyze")
async def analyze(req: AnalyzeReq) -> dict:
    # Request-provided cookies win (the gateway injects freshly dev-refreshed
    # cookies from Redis here); otherwise fall back to the sidecar's own
    # environment (TWITTER_*/WEIBO_*). Tests inject cookies the same way.
    cookies = req.cookies or scraper.cookies_for_platform(req.platform)
    jid = jobs.start_job(req.platform, req.handle, cookies, req.max_posts)
    return {"job_id": jid}


@router.get("/analyze/{job_id}")
async def analyze_status(job_id: str) -> dict:
    job = jobs.get_job(job_id)
    if job is None:
        return {
            "status": "error",
            "progress": {"done": 0, "total": 0},
            "result": None,
            "error": "unknown job",
        }
    return {
        "status": job.status,
        "progress": {"done": job.done, "total": job.total},
        "result": job.result,
        "error": job.error,
    }
