"""Regression checks for direct Cosmic Cards username lookup and trade initiation."""

from pathlib import Path

card_source = Path("cosmic_cards.py").read_text(encoding="utf-8")
app_source = Path("app.py").read_text(encoding="utf-8")

assert 'CARD_MODULE_VERSION = "trade_acceptance_notification_v1"' in card_source
assert 'getattr(cosmic_cards, "CARD_MODULE_VERSION", None) != "trade_acceptance_notification_v1"' in app_source
assert "def _render_trade_profile_lookup(user_hash: str)" in card_source
assert 'st.markdown("##### Find a LunaTicK member")' in card_source
assert 'with st.expander("Find a LunaTicK member"' not in card_source
assert 'st.form_submit_button("Find member", use_container_width=True)' in card_source
assert "get_card_profile_by_username_server_only" in card_source
assert "send_trade(user_hash, target_subject)" in card_source
assert "Send a request now; once accepted, this member is added to your collection." in card_source
assert "card_lookup_trade_message" not in card_source
assert 'with st.popover(trade_label, help="Find a member or send a card-trade request")' in card_source
assert "target_subject = str((source or {}).get(\"auth_subject\") or \"\").strip()" in card_source
assert "profile_auth_subject" not in card_source[card_source.index("def _render_trade_profile_lookup"):card_source.index("def _render_trade_initiation")]

print("Cosmic Cards direct lookup and trade-flow checks passed.")
