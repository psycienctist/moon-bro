from tarot_reading import DECK, MAJORS, POSITIONS, SUITS, _draw_cards


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
