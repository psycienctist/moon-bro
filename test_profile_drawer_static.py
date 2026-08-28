"""Static safety checks for the isolated, non-breaking Profile drawer."""

from pathlib import Path

app_source = Path("app.py").read_text(encoding="utf-8")
drawer_source = Path("profile_drawer.py").read_text(encoding="utf-8")

assert "try:\n    import profile_drawer\nexcept Exception:\n    profile_drawer = None" in app_source
assert "def toggle_profile_drawer()" in app_source
assert 'st.session_state["profile_drawer_open"] = not st.session_state.get("profile_drawer_open", False)' in app_source
assert "profile_drawer.render_profile_drawer(cosmic_cards)" in app_source
assert "except Exception:\n        st.session_state[\"profile_drawer_open\"] = False" in app_source
assert "NAV_ITEMS = [" in app_source
assert 'elif current_page == "Profile":' in app_source

assert 'DRAWER_MODULE_VERSION = "profile_drawer_isolated_v1"' in drawer_source
assert "def render_profile_drawer(cosmic_module: Any)" in drawer_source
assert 'with st.container(key="profile-drawer-overlay", border=True)' in drawer_source
assert "position: fixed !important" in drawer_source
assert "width: min(50vw, 30rem) !important" in drawer_source
assert "def _safe_public_profile()" in drawer_source
assert "getattr(cosmic_module, \"build_card\", None)" in drawer_source
assert "except Exception:" in drawer_source

print("Isolated Profile drawer safety checks passed.")
