from app.services import scraper


def test_picks_newest_not_first():
    # 置顶推文排在最前但日期很旧：应取最新的那条，而不是第一条
    dates = [
        "2019-03-01T00:00:00.000Z",   # 置顶旧推，排在最前
        "2026-09-12T03:13:01.000Z",
        "2026-07-28T17:42:14.000Z",
    ]
    assert scraper._newest_article_date(dates) == "2026-09-12T03:13:01.000Z"


def test_already_newest_first_is_unchanged():
    dates = ["2026-09-12T03:13:01.000Z", "2026-07-28T17:42:14.000Z"]
    assert scraper._newest_article_date(dates) == "2026-09-12T03:13:01.000Z"


def test_skips_unparsable_and_empty():
    dates = ["", "not-a-date", "2026-07-28T17:42:14.000Z", None]
    assert scraper._newest_article_date(dates) == "2026-07-28T17:42:14.000Z"


def test_empty_input_returns_empty():
    assert scraper._newest_article_date([]) == ""
    assert scraper._newest_article_date(None) == ""
    assert scraper._newest_article_date(["", "garbage"]) == ""


def test_pinned_old_tweet_no_longer_looks_stale():
    # 回归：置顶旧推 + 新鲜时间轴，不应被判为过时
    from datetime import UTC, datetime, timedelta

    fresh = (datetime.now(UTC).replace(tzinfo=None) - timedelta(days=5)).isoformat() + "Z"
    pinned = "2019-03-01T00:00:00.000Z"
    newest = scraper._newest_article_date([pinned, fresh])
    assert newest == fresh
