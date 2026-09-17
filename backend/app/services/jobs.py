"""
app/services/jobs.py  —  in-memory async analysis job store (sidecar, no DB)

Runs the full pipeline (scrape → classify each post → aggregate) as a background
asyncio task with per-post progress. The rate math is ported DB-free from the
original `aggregator.py`: the 5 dimension rates are fractions of the analyzed
posts flagged for each dimension, then `compute_distortion_index` folds them into
the 0-100 index. `consistency_score` and deletion tracking (both DB-coupled in
the original) are dropped — they are not part of the sidecar result shape.
"""
from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from app.services import classifier, scraper

MAX_POSTS_DEFAULT = 30

# 时间失真：链接原文发布日早于帖子发布 30 天以上（源自原 aggregator.py）
TEMPORAL_STALE_DAYS = 30

# 五维度类型 → 结果字段名。顺序即 classifier 的维度顺序。
_RATE_FIELDS = {
    "inflate": "significance_inflation_rate",
    "anxiety": "anxiety_manufacturing_rate",
    "novelty": "novelty_claim_rate",
    "loaded_language": "loaded_language_rate",
    "temporal": "temporal_distortion_rate",
}


@dataclass
class JobState:
    status: str = "pending"
    done: int = 0
    total: int = 0
    result: dict | None = None
    error: str | None = None


_JOBS: dict[str, JobState] = {}


def new_job() -> str:
    jid = uuid.uuid4().hex
    _JOBS[jid] = JobState()
    return jid


def get_job(jid: str) -> JobState | None:
    return _JOBS.get(jid)


async def run_analysis(
    platform: str,
    handle: str,
    cookies: dict[str, str],
    max_posts: int,
    on_progress: Callable[[int, int], None],
) -> dict:
    """Scrape → classify each post → aggregate. `on_progress(done, total)` per post.

    Returns the sidecar result shape:
      {account, profile, posts}
    """
    cookies = cookies or {}

    # ── Step 1: profile + posts (both request-cookie driven) ──────────────
    info = await scraper.fetch_profile_info(handle, cookies=cookies, platform=platform)
    raw_posts = await scraper.fetch_recent_posts(handle, cookies=cookies, platform=platform)
    raw_posts = raw_posts[:max_posts]
    total = len(raw_posts)
    on_progress(0, total)

    # ── Step 2-4: classify each post + temporal cross-check ───────────────
    counters: defaultdict[str, int] = defaultdict(int)
    temporal_mismatch = 0
    out_posts: list[dict] = []

    for i, raw in enumerate(raw_posts):
        content = classifier.strip_lone_surrogates(raw.get("content", ""))
        cls = await classifier.classify(content)
        types = cls.get("types", [])
        for t in types:
            counters[t] += 1

        # 时间失真交叉验证：链接原文发布日早于帖子 >30 天 → 计一次错配
        posted_at = raw.get("posted_at")
        linked_url = raw.get("linked_url")
        if linked_url and posted_at:
            pub = await scraper.fetch_url_publish_date(linked_url)
            if pub and (posted_at - pub).days > TEMPORAL_STALE_DAYS:
                temporal_mismatch += 1

        out_posts.append(
            {
                "content": content,
                "posted_at": posted_at.isoformat() if posted_at else None,
                "distortion_types": types,
                "confidence": cls.get("confidence"),
                "classification_method": cls.get("method"),
                "trigger_signals": cls.get("signals", []),
            }
        )
        on_progress(i + 1, total)

    # ── Step 5: aggregate (rate math ported DB-free from aggregator.py) ───
    profile = _build_profile(total, counters, temporal_mismatch)

    return {
        "account": {
            "handle": handle,
            "display_name": info.get("display_name", handle),
            "platform": platform,
        },
        "profile": profile,
        "posts": out_posts,
    }


def _build_profile(
    total: int, counters: dict[str, int], temporal_mismatch: int
) -> dict:
    """Port of aggregator.py rate math onto in-memory counters (no DB, no CS)."""
    if total == 0:
        rates = {field: 0.0 for field in _RATE_FIELDS.values()}
        return {
            "distortion_index": 0,
            **rates,
            "total_posts_analyzed": 0,
        }

    rates = {
        field: round(counters.get(dtype, 0) / total, 4)
        for dtype, field in _RATE_FIELDS.items()
    }
    # 时间失真率取规则检测与链接日期比对中较大者（源自原 aggregator.py）
    rates["temporal_distortion_rate"] = round(
        max(counters.get("temporal", 0) / total, temporal_mismatch / total), 4
    )

    distortion_index = classifier.compute_distortion_index(rates)

    return {
        "distortion_index": distortion_index,
        **rates,
        "total_posts_analyzed": total,
    }


async def _drive(
    jid: str, platform: str, handle: str, cookies: dict[str, str], max_posts: int
) -> None:
    job = _JOBS[jid]
    job.status = "running"
    try:

        def prog(done: int, total: int) -> None:
            job.done, job.total = done, total

        job.result = await run_analysis(platform, handle, cookies, max_posts, prog)
        job.status = "done"
    except Exception as exc:  # noqa: BLE001 — surface any pipeline failure to the poller
        job.status, job.error = "error", str(exc)


def start_job(
    platform: str, handle: str, cookies: dict[str, str], max_posts: int | None
) -> str:
    jid = new_job()
    asyncio.create_task(
        _drive(jid, platform, handle, cookies, max_posts or MAX_POSTS_DEFAULT)
    )
    return jid
