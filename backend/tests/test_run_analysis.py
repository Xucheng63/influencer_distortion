from datetime import datetime

from app.services import jobs, scraper, classifier


async def test_run_analysis_computes_rates_and_index(monkeypatch):
    """Feed 4 posts, 2 flagged `inflate`. Prove the ported rate math:
    significance_inflation_rate == 0.5, total_posts_analyzed == 4, and
    distortion_index matches compute_distortion_index for those rates.
    Scraper + classifier fully mocked (no browser, no network).
    """
    posts = [
        {"content": "post A", "posted_at": datetime(2026, 1, 1), "linked_url": None},
        {"content": "post B", "posted_at": datetime(2026, 1, 2), "linked_url": None},
        {"content": "post C", "posted_at": datetime(2026, 1, 3), "linked_url": None},
        {"content": "post D", "posted_at": datetime(2026, 1, 4), "linked_url": None},
    ]

    async def fake_profile(handle, cookies=None):
        return {"handle": handle, "display_name": "Fake Name", "followers": 123}

    async def fake_recent(handle, cookies=None, max_pages=3):
        return posts

    # First two posts flagged inflate, last two clean.
    flags = {
        "post A": ["inflate"],
        "post B": ["inflate"],
        "post C": [],
        "post D": [],
    }

    async def fake_classify(content):
        return {
            "types": flags[content],
            "confidence": 0.9 if flags[content] else 1.0,
            "signals": ["changes everything"] if flags[content] else [],
            "method": "rules_v2",
        }

    monkeypatch.setattr(scraper, "fetch_profile_info", fake_profile)
    monkeypatch.setattr(scraper, "fetch_recent_posts", fake_recent)
    monkeypatch.setattr(classifier, "classify", fake_classify)

    seen = []
    result = await jobs.run_analysis(
        "bluesky", "someone.bsky.social", {}, 30, lambda d, t: seen.append((d, t))
    )

    profile = result["profile"]
    assert profile["total_posts_analyzed"] == 4
    assert profile["significance_inflation_rate"] == 0.5
    assert profile["anxiety_manufacturing_rate"] == 0.0
    assert profile["novelty_claim_rate"] == 0.0
    assert profile["loaded_language_rate"] == 0.0
    assert profile["temporal_distortion_rate"] == 0.0

    expected_index = classifier.compute_distortion_index(
        {
            "significance_inflation_rate": 0.5,
            "anxiety_manufacturing_rate": 0.0,
            "novelty_claim_rate": 0.0,
            "loaded_language_rate": 0.0,
            "temporal_distortion_rate": 0.0,
        }
    )
    assert profile["distortion_index"] == expected_index

    # account block echoes handle + platform, picks up fetched display name
    assert result["account"]["handle"] == "someone.bsky.social"
    assert result["account"]["platform"] == "bluesky"
    assert result["account"]["display_name"] == "Fake Name"

    # posts carry through the classification fields
    assert len(result["posts"]) == 4
    assert result["posts"][0]["distortion_types"] == ["inflate"]
    assert result["posts"][0]["classification_method"] == "rules_v2"

    # progress fired once per post, ending at (4, 4)
    assert seen[-1] == (4, 4)


async def test_run_analysis_temporal_from_linked_date(monkeypatch):
    """A post whose linked article predates it by >30 days counts as temporal
    distortion even without a `temporal` classifier flag (ported max() rule)."""
    posts = [
        {
            "content": "breaking",
            "posted_at": datetime(2026, 3, 1),
            "linked_url": "https://example.com/old",
        },
        {"content": "clean", "posted_at": datetime(2026, 3, 2), "linked_url": None},
    ]

    async def fake_profile(handle, cookies=None):
        return {"handle": handle, "display_name": "N", "followers": 0}

    async def fake_recent(handle, cookies=None, max_pages=3):
        return posts

    async def fake_classify(content):
        return {"types": [], "confidence": 1.0, "signals": [], "method": "rules_v2"}

    async def fake_pub_date(url):
        return datetime(2026, 1, 1)  # ~59 days before the post

    monkeypatch.setattr(scraper, "fetch_profile_info", fake_profile)
    monkeypatch.setattr(scraper, "fetch_recent_posts", fake_recent)
    monkeypatch.setattr(classifier, "classify", fake_classify)
    monkeypatch.setattr(scraper, "fetch_url_publish_date", fake_pub_date)

    result = await jobs.run_analysis("twitter", "x", {}, 30, lambda d, t: None)
    assert result["profile"]["temporal_distortion_rate"] == 0.5
