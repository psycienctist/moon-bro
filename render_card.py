def render_collectible_card(card: dict):
    n = card["natal"]
    sun_c = sign_color(n["sun_sign"])
    moon_c = sign_color(n["moon_sign"])
    rise_c = sign_color(n.get("rising_sign")) if n.get("has_rising") else "#8b949e"
    rarity = card.get("rarity", "Common")
    r_color, r_label = RARITY_STYLE.get(rarity, RARITY_STYLE["Common"])
    dom = card.get("dominant") or {"name": "—", "symbol": "✦"}
    moons = card.get("full_moons_lived", 0)
    hd = card.get("hd_type", "—")
    hd_profile = card.get("hd_profile", "—")
    hd_authority = card.get("hd_authority", "—")
    time_line = card.get("birth_time") or "—"
    place = card.get("birth_place") or "Location unknown"

    # --- RISING BLOCK (HTML) ---
    if n.get("has_rising"):
        rising_block = f"""
        <div style="text-align:center;flex:1;cursor:pointer;">
          <div style="font-size:0.55rem;color:#8b949e;letter-spacing:1px;">RISING</div>
          <div style="font-size:1.15rem;font-weight:700;color:{rise_c};">{n['rising_symbol']}</div>
          <div style="font-size:1.15rem;font-weight:700;color:{rise_c};">{n['rising_sign']}</div>
        </div>"""
    else:
        rising_block = """
        <div style="text-align:center;flex:1;">
          <div style="font-size:0.55rem;color:#8b949e;letter-spacing:1px;">RISING</div>
          <div style="font-size:0.85rem;color:#484f58;">Add time & place</div>
        </div>"""

    # --- FLIP BUTTON ---
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Flip", key=f"flip_{card['user_hash']}"):
            st.session_state.show_card_back = not st.session_state.get("show_card_back", False)
            st.rerun()

    # --- MAIN CARD HTML ---
    st.html(f"""
    <div style="background: linear-gradient(160deg, #0a0e17 0%, #12101f 40%, #0d1f3c 100%); border: 2px solid {sun_c}; border-radius: 20px; padding: 1.25rem 1.35rem 1.4rem; margin: 0.8rem 0 1.2rem; box-shadow: 0 0 32px {sun_c}44, inset 0 0 40px rgba(0,0,0,0.35); position: relative; overflow: hidden;">
      <div style="position:absolute;top:-30px;right:-30px;width:120px;height:120px; background:radial-gradient(circle,{sun_c}33,transparent 70%);pointer-events:none;"></div>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.7rem;">
        <div style="font-family:Orbitron,sans-serif;font-size:0.65rem;letter-spacing:3px;color:#58a6ff;">COSMIC CARD</div>
        <div style="font-family:Orbitron,sans-serif;font-size:0.55rem;letter-spacing:2px; color:{r_color};border:1px solid {r_color};border-radius:999px; padding:0.2rem 0.65rem;background:{r_color}22;">{r_label}</div>
      </div>
      <div style="font-size:1.35rem;font-weight:700;color:#f0f6fc;margin-bottom:0.15rem;">{card['display_name']}</div>
      <div style="color:#8b949e;font-size:0.8rem;margin-bottom:1rem;">📍 {place} · 🕐 {time_line}</div>
    </div>
    """)

    # --- TAP-TO-EXPAND SECTIONS ---
    st.markdown("##### ✨ Tap any field below to explore its meaning")

    # 1. SUN
    with st.expander(f"☀️ Sun: {n['sun_symbol']} {n['sun_sign']}", expanded=False):
        st.markdown(f"""
        **Your core identity** — the energy you radiate most consistently. It shapes your ego, willpower, and life purpose.  
        *Why it matters:* It defines your fundamental sense of self and the conscious creative force you bring to the world.
        """)

    # 2. MOON
    with st.expander(f"🌙 Moon: {n['moon_symbol']} {n['moon_sign']}", expanded=False):
        st.markdown(f"""
        **Your emotional inner world** — how you feel, nurture, and process. It reveals what you need to feel safe and whole.  
        *Why it matters:* It governs your subconscious reactions, emotional resilience, and private sanctuary needs.
        """)

    # 3. RISING
    if n.get("has_rising"):
        with st.expander(f"⬆️ Rising: {n['rising_symbol']} {n['rising_sign']}", expanded=False):
            st.markdown(f"""
            **The mask you wear** — the first impression you make. It is the lens through which the world sees you.  
            *Why it matters:* It dictates your spontaneous outward demeanor and the physical vitality filtering your chart.
            """)
    else:
        st.caption("⬆️ Rising: Add birth time & place to unlock.")

    # 4. BIRTH PHASE
    with st.expander(f"🌗 Birth Phase: {n['phase_emoji']} {n['phase_name']}", expanded=False):
        st.markdown(f"""
        **Your soul's innate rhythm** — the lunar phase at your exact moment of birth. It reveals whether you are here to initiate, build, refine, or release.  
        *Why it matters:* It aligns your natural energetic cadence with cosmic timing and developmental cycles.
        """)

    # 5. FULL MOONS LIVED
    with st.expander(f"🌕 Full Moons Lived: {moons}", expanded=False):
        st.markdown(f"""
        **Your lived chapters** — the number of complete lunar cycles since your birth. Each one is a milestone of emotional wisdom.  
        *Why it matters:* It acts as a profound chronological marker of maturational chapters and accumulated inner knowing.
        """)

    # 6. DOMINANT PLANET
    with st.expander(f"⭐ Dominant: {dom['symbol']} {dom['name']}", expanded=False):
        st.markdown(f"""
        **Your primary planetary lens** — the celestial body with the strongest influence over your chart based on your Sun, Moon, and Rising rulers.  
        *Why it matters:* It colors your motivations and default operating mode, focusing your astrological signature.
        """)

    # 7. HD TYPE + PROFILE + AUTHORITY (Combined for brevity)
    with st.expander(f"🧬 Human Design: {hd} · {hd_profile} · {hd_authority}", expanded=False):
        st.markdown(f"""
        **Your energetic blueprint** — your Type, Profile, and Authority work together to guide how you interact with the world.  
        - **Type:** {hd} — Defines how your aura functions.  
        - **Profile:** {hd_profile} — Your life role archetype.  
        - **Authority:** {hd_authority} — Your inner decision-making compass.  
        *Why it matters:* It removes resistance by showing you how you are uniquely designed to make correct choices without burnout.
        """)

    # --- SUN SIGN ARCHETYPE (Bottom of card) ---
    st.markdown("---")
    desc = SUN_SIGN_DESCRIPTIONS.get(n["sun_sign"], "Radiant and purposeful, you embody unique cosmic gifts.")
    st.info(f"**{n['sun_sign']} Sun Archetype:** {desc}")