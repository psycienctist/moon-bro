from datetime import date, timedelta

from tarot_reading import DECK, MAJORS, POSITIONS, SUITS, _combine_three_cards, _daily_draw, _draw_cards


def test_complete_tarot_deck_has_78_unique_cards():
    assert len(DECK) == 78
    assert len({card["name"] for card in DECK}) == 78
    assert sum(card["arcana"] == "Major Arcana" for card in DECK) == 22
    assert sum(card["arcana"] == "Minor Arcana" for card in DECK) == 56


def test_every_card_has_upright_reversed_and_constructive_guidance():
    for card in DECK:
        assert card["upright"].strip()
        assert card["reversed"].strip()
        assert card["advice"].strip()
        assert card["image_file"].strip()


def test_spreads_have_expected_positions():
    assert len(POSITIONS["One-card reflection"]) == 1
    assert len(POSITIONS["Three-card reflection"]) == 3
    assert len(POSITIONS["Celtic Cross"]) == 10


def test_draw_has_no_duplicate_cards():
    for count in (1, 3, 10):
        cards = _draw_cards(count)
        assert len(cards) == count
        assert len({card["name"] for card, _ in cards}) == count



def test_three_card_reflection_connects_positions_and_guidance():
    lookup = {card["name"]: card for card in DECK}
    cards = [
        (lookup["Justice"], False),
        (lookup["Six of Swords"], False),
        (lookup["Ten of Pentacles"], False),
    ]
    narrative = _combine_three_cards(cards, "finding a steadier path")
    assert "What shaped this" in narrative
    assert "What is present" in narrative
    assert "A helpful next step" in narrative
    assert "finding a steadier path" in narrative
    assert "not a fixed forecast" in narrative



def test_daily_draw_is_stable_for_account_and_date():
    today = date(2026, 10, 26)
    first = _daily_draw("account-a", today)
    second = _daily_draw("account-a", today)
    assert [(c["name"], rev) for c, rev in first] == [(c["name"], rev) for c, rev in second]
    assert len({c["name"] for c, _ in first}) == 3


def test_daily_draw_changes_with_date_or_account():
    today = date(2026, 10, 26)
    baseline = [(c["name"], rev) for c, rev in _daily_draw("account-a", today)]
    next_day = [(c["name"], rev) for c, rev in _daily_draw("account-a", today + timedelta(days=1))]
    other_account = [(c["name"], rev) for c, rev in _daily_draw("account-b", today)]
    assert baseline != next_day
    assert baseline != other_account


def test_combined_reading_uses_specific_third_card_guidance():
    lookup = {card["name"]: card for card in DECK}
    cards = [
        (lookup["Justice"], False),
        (lookup["Six of Swords"], False),
        (lookup["Ten of Pentacles"], False),
    ]
    narrative = _combine_three_cards(cards, "finding a steadier path")
    assert "Justice" in narrative and "Six of Swords" in narrative and "Ten of Pentacles" in narrative
    assert "concrete, sustainable step" in narrative
    assert "not a fixed forecast" in narrative
