def test_pipeline_symbols_importable():
    from app.services.classifier import (
        STRONG_PATTERNS, WEAK_PATTERNS, EXCLUSION_PATTERNS,
        classify, classify_rules, compute_distortion_index,
    )
    assert set(STRONG_PATTERNS) == {
        "inflate", "anxiety", "novelty", "loaded_language", "temporal",
    }
    # Frozen tuning constants — guard against accidental edits.
    from app.services import classifier as c
    assert c.LLM_THRESHOLD == 0.70
    assert c.CONFIDENCE_CAP == 0.95
    assert c.WEAK_MIN == 2
