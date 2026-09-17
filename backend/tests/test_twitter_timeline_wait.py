from app.services import scraper


def test_text_present_is_ready_immediately():
    # 正文一出现就放行，不必等满宽限期
    assert scraper._timeline_state(articles=5, tweet_texts=3, ms_since_articles=0) == "ready_text"


def test_no_articles_is_not_ready():
    assert scraper._timeline_state(articles=0, tweet_texts=0, ms_since_articles=0) == "not_ready"
    assert scraper._timeline_state(articles=0, tweet_texts=0, ms_since_articles=60000) == "not_ready"


def test_media_only_top_waits_grace_then_releases():
    # 顶部全是纯媒体推文：先等一段宽限期，超过后就绪放行，不再死等 tweetText
    grace = scraper._TIMELINE_GRACE_MS
    assert scraper._timeline_state(5, 0, grace - 1) == "not_ready"
    assert scraper._timeline_state(5, 0, grace) == "ready_media_only"


def test_grace_is_far_below_total_timeout():
    # 宽限期必须远小于 45s 总超时，否则纯媒体顶部仍会拖满整个超时
    assert scraper._TIMELINE_GRACE_MS <= 15000


class _FakePage:
    """按脚本逐次返回 DOM 计数的假 page。"""

    def __init__(self, counts):
        self._counts = list(counts)
        self.calls = 0

    def evaluate(self, _js):
        self.calls += 1
        return self._counts[min(self.calls - 1, len(self._counts) - 1)]

    def inner_text(self, _sel):
        return "body text"


def test_wait_returns_as_soon_as_text_appears():
    page = _FakePage([
        {"articles": 0, "tweetTexts": 0},
        {"articles": 3, "tweetTexts": 0},
        {"articles": 5, "tweetTexts": 2},
    ])
    assert scraper._wait_twitter_timeline(page, "someone", timeout_ms=45000) == "ready_text"
    assert page.calls == 3


def test_wait_releases_on_media_only_without_burning_timeout():
    # 全程没有 tweetText：应在宽限期后返回 ready_media_only，而不是等满 timeout
    import time

    page = _FakePage([{"articles": 5, "tweetTexts": 0}])
    started = time.time()
    state = scraper._wait_twitter_timeline(page, "someone", timeout_ms=45000)
    elapsed_ms = (time.time() - started) * 1000
    assert state == "ready_media_only"
    assert elapsed_ms < scraper._TIMELINE_GRACE_MS + 3000


def test_wait_reports_not_ready_when_nothing_renders():
    page = _FakePage([{"articles": 0, "tweetTexts": 0}])
    assert scraper._wait_twitter_timeline(page, "someone", timeout_ms=1000) == "not_ready"


def test_wait_survives_evaluate_errors():
    class _Boom(_FakePage):
        def evaluate(self, _js):
            raise RuntimeError("page closed")

    assert scraper._wait_twitter_timeline(_Boom([]), "someone", timeout_ms=1000) == "not_ready"
