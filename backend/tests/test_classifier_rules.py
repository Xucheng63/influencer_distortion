from app.services import classifier
from app.services.classifier import classify_rules

_LLM_KEYS = ("ANTHROPIC_API_KEY", "OPENROUTER_API_KEY", "OPENAI_API_KEY")


def _clear_llm_keys(monkeypatch):
    for k in _LLM_KEYS:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.delenv("DISTORTION_LLM_MODEL", raising=False)


def test_llm_provider_none_when_no_keys(monkeypatch):
    _clear_llm_keys(monkeypatch)
    assert classifier._llm_provider() is None
    assert classifier._llm_available() is False


def test_llm_provider_prefers_anthropic(monkeypatch):
    _clear_llm_keys(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-oai")
    assert classifier._llm_provider() == (
        "anthropic",
        classifier.DEFAULT_ANTHROPIC_MODEL,
    )


def test_llm_provider_openrouter_when_no_anthropic(monkeypatch):
    _clear_llm_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-oai")
    assert classifier._llm_provider() == (
        "openrouter",
        classifier.DEFAULT_OPENROUTER_MODEL,
    )


def test_llm_provider_model_override(monkeypatch):
    _clear_llm_keys(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or")
    monkeypatch.setenv("DISTORTION_LLM_MODEL", "anthropic/claude-sonnet-4-6")
    assert classifier._llm_provider() == ("openrouter", "anthropic/claude-sonnet-4-6")


def test_strip_code_fences():
    assert classifier._strip_code_fences('```json\n{"a":1}\n```') == '{"a":1}'
    assert classifier._strip_code_fences('{"a":1}') == '{"a":1}'


def test_extract_json_object_handles_trailing_prose():
    # OpenRouter/Claude may append an explanation after the JSON.
    raw = '{"types": ["inflate"], "confidence": 0.8}\n\nThis post exaggerates.'
    import json

    assert json.loads(classifier._extract_json_object(raw)) == {
        "types": ["inflate"],
        "confidence": 0.8,
    }


def test_extract_json_object_handles_leading_prose_and_fences():
    raw = 'Here is the result:\n```json\n{"types": [], "confidence": 1.0}\n```'
    import json

    assert json.loads(classifier._extract_json_object(raw)) == {
        "types": [],
        "confidence": 1.0,
    }


def test_extract_json_object_ignores_braces_in_strings():
    raw = '{"signals": ["use {curly} braces"], "confidence": 0.5} trailing'
    import json

    assert json.loads(classifier._extract_json_object(raw)) == {
        "signals": ["use {curly} braces"],
        "confidence": 0.5,
    }


def test_coerce_result_fills_missing_fields():
    # LLM omitted confidence + signals; types missing → safe, gateway-valid shape.
    out = classifier._coerce_result({"types": ["inflate"]}, fallback_confidence=0.7)
    assert out["types"] == ["inflate"]
    assert out["confidence"] == 0.7
    assert out["signals"] == []


def test_coerce_result_normalises_bad_types():
    out = classifier._coerce_result(
        {"types": None, "confidence": "not-a-number", "signals": "x"},
        fallback_confidence=0.4,
    )
    assert out["types"] == []
    assert out["confidence"] == 0.4
    assert out["signals"] == []


def test_inflate_strong_pattern_fires():
    r = classify_rules("This changes the world forever.")
    assert "inflate" in r["types"]
    assert r["confidence"] > 0


def test_anxiety_strong_pattern_fires():
    r = classify_rules("You will be left behind if you ignore this.")
    assert "anxiety" in r["types"]


def test_clean_text_scores_nothing():
    r = classify_rules("Here is a neutral factual sentence about the weather.")
    assert r["types"] == []


# ── Chinese coverage (added for inflate/anxiety/novelty/temporal gaps) ──────────


def test_zh_inflate_fires():
    r = classify_rules("这款产品将改变世界，史上最强，史无前例的突破")
    assert "inflate" in r["types"]


def test_zh_anxiety_fires():
    r = classify_rules("再不学AI就晚了，你即将被淘汰，中年危机来临")
    assert "anxiety" in r["types"]


def test_zh_novelty_fires():
    r = classify_rules("独家爆料：不为人知的内幕，没人敢告诉你")
    assert "novelty" in r["types"]


def test_zh_temporal_fires():
    r = classify_rules("突发！刚刚，官方宣布重磅消息")
    assert "temporal" in r["types"]


def test_zh_loaded_language_extra_fires():
    r = classify_rules("触目惊心！骇人听闻的丧心病狂事件")
    assert "loaded_language" in r["types"]


def test_zh_neutral_scores_nothing():
    r = classify_rules("今天天气不错，我去公园散步，读了一本书。")
    assert r["types"] == []


def test_zh_neutral_news_scores_nothing():
    r = classify_rules("本周我们发布了季度财报，营收同比增长。")
    assert r["types"] == []


# ── English clickbait gaps ─────────────────────────────────────────────────────


def test_en_novelty_clickbait_fires():
    r = classify_rules("This is the secret they don't want you to know")
    assert "novelty" in r["types"]


def test_en_inflate_once_in_a_lifetime_fires():
    r = classify_rules("A once in a lifetime opportunity, a defining moment for us")
    assert "inflate" in r["types"]


def test_en_anxiety_before_too_late_fires():
    # "before it's too late" is genuine urgency-anxiety; must NOT be swallowed by
    # the "it's never too late" encouragement exclusion.
    r = classify_rules("Act now before it's too late")
    assert "anxiety" in r["types"]


def test_en_encouragement_still_excluded():
    r = classify_rules("It's never too late to learn a new skill")
    assert "anxiety" not in r["types"]
