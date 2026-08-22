"""Static regression check for LunaTicK's fixed five-tab mobile navigation rail."""

from pathlib import Path


source = Path("app.py").read_text(encoding="utf-8")

assert '("Community", "👥", "Connect")' in source
assert '("Journal", "📓", "Journal")' in source
assert '("Calendar", "📅", "Track")' in source
assert '("Cosmic Cards", "🃏", "Deal")' in source
assert '("Tones", "🎵", "Heal")' in source
assert 'key=f"bottom_nav_{page_name.lower().replace(\' \', \'_\')}"' in source

journal_selector = ".st-key-lunatick-bottom-nav .st-key-bottom_nav_journal button"
assert journal_selector in source
journal_rule = source[source.index(journal_selector):source.index(journal_selector) + 500]
assert "font-size: 0.56rem !important;" in journal_rule
assert "white-space: nowrap !important;" in journal_rule
assert "word-break: keep-all !important;" in journal_rule

community_selector = ".st-key-lunatick-bottom-nav .st-key-bottom_nav_community button"
assert community_selector in source

print("Fixed five-tab rail and Journal no-wrap mobile guard passed.")
