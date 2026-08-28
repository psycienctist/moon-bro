"""Regression checks for accepted Cosmic Cards trade notifications."""

from pathlib import Path

card_source = Path("cosmic_cards.py").read_text(encoding="utf-8")
store_source = Path("supabase_store.py").read_text(encoding="utf-8")
app_source = Path("app.py").read_text(encoding="utf-8")

assert 'CARD_MODULE_VERSION = "trade_acceptance_notification_v1"' in card_source
assert 'getattr(cosmic_cards, "CARD_MODULE_VERSION", None) != "trade_acceptance_notification_v1"' in app_source
assert "sender_seen_at TIMESTAMP" in card_source
assert "def mark_accepted_trades_seen" in card_source
assert 'trade.get("status") == "accepted" and not trade.get("sender_seen_at")' in card_source
assert 'f"🤝 Trade Cards · {notification_count} new"' in card_source
assert 'st.success(f"✦ {notification_count} {noun} accepted your card trade.")' in card_source
assert 'st.button("Mark trade update as seen", key="acknowledge_accepted_card_trades"' in card_source
assert "mark_accepted_card_trades_seen" in store_source
assert '"sender_seen_at": "is.null"' in store_source
assert '"sender_auth_subject": f"eq.{sender_auth_subject}"' in store_source

print("Cosmic Cards accepted-trade notification checks passed.")
