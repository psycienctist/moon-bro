import tarot_ai


def _cards():
    from tarot_reading import DECK
    lookup = {card["name"]: card for card in DECK}
    return [
        (lookup["Justice"], False),
        (lookup["Six of Swords"], False),
        (lookup["Ten of Pentacles"], False),
    ]


def test_openrouter_success_does_not_call_gemini(monkeypatch):
    monkeypatch.setattr(tarot_ai, "_openrouter", lambda prompt: "A" * 120)
    monkeypatch.setattr(
        tarot_ai, "_gemini",
        lambda prompt: (_ for _ in ()).throw(AssertionError("fallback should not run")),
    )
    text, provider = tarot_ai.generate_combined_reading(_cards(), "finding balance")
    assert len(text) >= 100
    assert provider == "OpenRouter"


def test_gemini_is_used_when_openrouter_fails(monkeypatch):
    monkeypatch.setattr(
        tarot_ai, "_openrouter",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("provider down")),
    )
    monkeypatch.setattr(tarot_ai, "_gemini", lambda prompt: "B" * 120)
    text, provider = tarot_ai.generate_combined_reading(_cards())
    assert len(text) >= 100
    assert provider == "Gemini fallback"


def test_local_fallback_signal_when_both_providers_fail(monkeypatch):
    monkeypatch.setattr(
        tarot_ai, "_openrouter",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("provider down")),
    )
    monkeypatch.setattr(
        tarot_ai, "_gemini",
        lambda prompt: (_ for _ in ()).throw(RuntimeError("provider down")),
    )
    text, provider = tarot_ai.generate_combined_reading(_cards())
    assert text == ""
    assert provider == "Local fallback"


def test_prompt_includes_cards_positions_and_intention():
    prompt = tarot_ai._prompt(_cards(), "finding a steadier path")
    assert "Justice" in prompt
    assert "Six of Swords" in prompt
    assert "Ten of Pentacles" in prompt
    assert "What shaped this" in prompt
    assert "finding a steadier path" in prompt
