import pytest

from app.services import classifier


# ── 抢救阶段：结构损坏但字段仍可读时，不应整条丢弃 ──────────────────

def test_salvages_commentary_inside_signals_array():
    raw = ('{"types":["loaded_language"],"confidence":0.85,'
           '"signals":["SHOCKING" → loaded_language (charged word)]}')
    r = classifier._loads_tolerant(raw)
    assert r["types"] == ["loaded_language"]
    assert r["confidence"] == 0.85


def test_salvages_missing_comma_delimiter():
    # server.log 里实际出现过的错误类型：Expecting ',' delimiter
    raw = '{"types":["inflate"],"confidence":0.85,"signals":["x"] "extra":"y"}'
    r = classifier._loads_tolerant(raw)
    assert r["types"] == ["inflate"]
    assert r["confidence"] == 0.85


def test_salvages_multiple_types():
    raw = ('{"types":["inflate","loaded_language"],"confidence":0.8,'
           '"signals":["A","B" → note]}')
    assert classifier._loads_tolerant(raw)["types"] == ["inflate", "loaded_language"]


def test_salvage_rejects_unknown_type_names():
    # 说明文字不能被当成分类结果混进来
    raw = '{"types":["→ some commentary"],"confidence":0.8,"signals":["x" oops]}'
    with pytest.raises(classifier.LLMJsonError):
        classifier._loads_tolerant(raw)


def test_unparseable_reply_raises_with_payload():
    with pytest.raises(classifier.LLMJsonError) as ei:
        classifier._loads_tolerant("I cannot classify this post.")
    # 原始文本必须随异常带出来，否则线上无从排查
    assert "I cannot classify" in ei.value.raw


def test_wellformed_json_still_parses_strictly():
    raw = '{"types":["inflate"],"confidence":0.9,"signals":["x"]}'
    assert classifier._loads_tolerant(raw) == {
        "types": ["inflate"], "confidence": 0.9, "signals": ["x"],
    }


# ── 失败兜底：LLM 出错不得清空规则已判出的类型 ──────────────────────

_RULE_RESULT = {
    "types": ["inflate"],
    "confidence": 0.6,
    "signals": ["huge"],
    "method": "rules_v2",
}


async def test_parse_failure_keeps_rule_types(monkeypatch):
    async def _boom(*a, **kw):
        raise classifier.LLMJsonError("unparseable LLM JSON: boom", raw="{bad")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    monkeypatch.setattr(classifier, "_complete_json", _boom)
    out = await classifier.classify_llm_fresh("some post", fallback=_RULE_RESULT)
    assert out["types"] == ["inflate"]          # 关键：没有被清零
    assert out["confidence"] == 0.6
    assert out["method"].startswith("llm_error:")


async def test_parse_failure_without_fallback_is_empty(monkeypatch):
    async def _boom(*a, **kw):
        raise classifier.LLMJsonError("unparseable LLM JSON: boom", raw="{bad")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    monkeypatch.setattr(classifier, "_complete_json", _boom)
    out = await classifier.classify_llm_fresh("some post")
    assert out["types"] == []


async def test_llm_unavailable_keeps_rule_types(monkeypatch):
    for k in ("ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    out = await classifier.classify_llm_fresh("some post", fallback=_RULE_RESULT)
    assert out["types"] == ["inflate"]
    assert out["method"] == "llm_unavailable"


async def test_fallback_is_not_mutated(monkeypatch):
    async def _boom(*a, **kw):
        raise classifier.LLMJsonError("boom", raw="{bad")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    monkeypatch.setattr(classifier, "_complete_json", _boom)
    await classifier.classify_llm_fresh("some post", fallback=_RULE_RESULT)
    assert _RULE_RESULT["method"] == "rules_v2"   # 调用方的 dict 不能被改写
