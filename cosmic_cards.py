# cosmic_cards.py
# Birth-chart cosmic cards + trade-as-friend-request (Moon-lit style)

import streamlit as st
import sqlite3
import ephem
import math
from datetime import datetime, timezone, timedelta, date

DB = "lunatick.db"

ZODIAC = [
    ("Aries", "♈"), ("Taurus", "♉"), ("Gemini", "♊"), ("Cancer", "♋"),
    ("Leo", "♌"), ("Virgo", "♍"), ("Libra", "♎"), ("Scorpio", "♏"),
    ("Sagittarius", "♐"), ("Capricorn", "♑"), ("Aquarius", "♒"), ("Pisces", "♓"),
]


def init_cards_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_hash TEXT PRIMARY KEY,
            display_name TEXT,
            birth_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS card_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_hash TEXT,
            receiver_hash TEXT,
            message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def _chart(dt_utc: datetime) -> dict:
    obs = ephem.Observer()
    obs.lat = obs.lon = "0"
    obs.date = ephem.Date(dt_utc)
    moon, sun = ephem.Moon(obs), ephem.Sun(obs)
    elong = float(moon.elong)
    if elong < 0:
        elong += 2 * math.pi
    phase_frac = elong / (2 * math.pi)
    phases = [
        (0.00, "New Moon", "🌑"), (0.07, "Waxing Crescent", "🌒"),
        (0.25, "First Quarter", "🌓"), (0.43, "Waxing Gibbous", "🌔"),
        (0.50, "Full Moon", "🌕"), (0.57, "Waning Gibbous", "🌖"),
        (0.75, "Last Quarter", "🌗"), (0.93, "Waning Crescent", "🌘"),
        (1.00, "New Moon", "🌑"),
    ]
    phase_name, phase_emoji = "New Moon", "🌑"
    for i in range(len(phases) - 1):
        if phases[i][0] <= phase_frac < phases[i + 1][0]:
            phase_name, phase_emoji = phases[i][1], phases[i][2]
            break
    moon_lon = math.degrees(float(ephem.Ecliptic(moon).lon)) % 360
    sun_lon = math.degrees(float(ephem.Ecliptic(sun).lon)) % 360
    mi, si = int(moon_lon / 30) % 12, int(sun_lon / 30) % 12
    return {
        "moon_sign": ZODIAC[mi][0], "moon_symbol": ZODIAC[mi][1],
        "sun_sign": ZODIAC[si][0], "sun_symbol": ZODIAC[si][1],
        "phase_name": phase_name, "phase_emoji": phase_emoji,
        "illum": moon.phase / 100.0,
        "moon_lon": moon_lon,
    }


def get_or_create_profile(user_hash: str) -> dict:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT display_name, birth_date FROM user_profiles WHERE user_hash=?", (user_hash,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"display_name": row[0], "birth_date": row[1]}
    return {"display_name": "Moon Wanderer", "birth_date": None}


def save_profile(user_hash: str, display_name: str, birth_date: str | None):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_profiles (user_hash, display_name, birth_date)
        VALUES (?, ?, ?)
        ON CONFLICT(user_hash) DO UPDATE SET
            display_name=excluded.display_name,
            birth_date=excluded.birth_date
    """, (user_hash, display_name, birth_date))
    conn.commit()
    conn.close()


def build_card(user_hash: str) -> dict | None:
    profile = get_or_create_profile(user_hash)
    if not profile["birth_date"]:
        return None
    try:
        bd = datetime.combine(date.fromisoformat(profile["birth_date"]), datetime.min.time())
        bd = bd.replace(tzinfo=timezone.utc) + timedelta(hours=12)
        natal = _chart(bd)
        now = _chart(datetime.now(timezone.utc))
        return {
            "user_hash": user_hash,
            "display_name": profile["display_name"],
            "birth_date": profile["birth_date"],
            "natal": natal,
            "now": now,
        }
    except Exception:
        return None


def list_users_with_cards(exclude_hash: str) -> list:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT user_hash, display_name, birth_date FROM user_profiles
        WHERE birth_date IS NOT NULL AND user_hash != ?
    """, (exclude_hash,))
    rows = c.fetchall()
    conn.close()
    out = []
    for h, name, bd in rows:
        card = build_card(h)
        if card:
            out.append(card)
    return out


def send_trade(sender: str, receiver: str, message: str = ""):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT id FROM card_trades
        WHERE sender_hash=? AND receiver_hash=? AND status='pending'
    """, (sender, receiver))
    if c.fetchone():
        conn.close()
        return False, "Already have a pending trade with this person."
    c.execute("""
        INSERT INTO card_trades (sender_hash, receiver_hash, message, status)
        VALUES (?, ?, ?, 'pending')
    """, (sender, receiver, message.strip() or None))
    conn.commit()
    conn.close()
    return True, "Trade (friend request) sent!"


def list_trades(user_hash: str, direction: str = "all") -> list:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if direction == "incoming":
        c.execute("""
            SELECT id, sender_hash, receiver_hash, message, status, created_at
            FROM card_trades WHERE receiver_hash=? ORDER BY created_at DESC
        """, (user_hash,))
    elif direction == "outgoing":
        c.execute("""
            SELECT id, sender_hash, receiver_hash, message, status, created_at
            FROM card_trades WHERE sender_hash=? ORDER BY created_at DESC
        """, (user_hash,))
    else:
        c.execute("""
            SELECT id, sender_hash, receiver_hash, message, status, created_at
            FROM card_trades
            WHERE sender_hash=? OR receiver_hash=?
            ORDER BY created_at DESC
        """, (user_hash, user_hash))
    rows = c.fetchall()
    conn.close()
    return [
        {"id": r[0], "sender": r[1], "receiver": r[2], "message": r[3],
         "status": r[4], "created_at": r[5]}
        for r in rows
    ]


def resolve_trade(trade_id: int, user_hash: str, accept: bool):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT receiver_hash, status FROM card_trades WHERE id=?", (trade_id,))
    row = c.fetchone()
    if not row or row[0] != user_hash or row[1] != "pending":
        conn.close()
        return False
    status = "accepted" if accept else "declined"
    c.execute("""
        UPDATE card_trades SET status=?, resolved_at=CURRENT_TIMESTAMP WHERE id=?
    """, (status, trade_id))
    conn.commit()
    conn.close()
    return True


def friends_of(user_hash: str) -> list:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        SELECT sender_hash, receiver_hash FROM card_trades
        WHERE status='accepted' AND (sender_hash=? OR receiver_hash=?)
    """, (user_hash, user_hash))
    friends = set()
    for s, r in c.fetchall():
        friends.add(r if s == user_hash else s)
    conn.close()
    return list(friends)


def render_cosmic_cards_tab():
    init_cards_db()
    user_hash = st.session_state.get("user_hash", "anonymous")

    st.markdown("### 🃏 Cosmic Cards & Friend Trades")
    st.caption("Your birth-chart card is your identity. Send it as a friend request.")

    profile = get_or_create_profile(user_hash)
    with st.expander("🧬 Your Cosmic Profile", expanded=not profile["birth_date"]):
        name = st.text_input("Display name", value=profile["display_name"] or "Moon Wanderer")
        default_bd = date.fromisoformat(profile["birth_date"]) if profile["birth_date"] else date(1990, 1, 1)
        bd = st.date_input(
            "Birth date",
            value=default_bd,
            min_value=date(1920, 1, 1),
            max_value=date.today(),
        )
        if st.button("Save profile", type="primary"):
            save_profile(user_hash, name.strip() or "Moon Wanderer", bd.isoformat())
            st.session_state.display_name = name.strip() or "Moon Wanderer"
            st.session_state.birth_date = bd
            st.success("Profile saved.")
            st.rerun()

    my_card = build_card(user_hash)
    if my_card:
        n = my_card["natal"]
        st.markdown(f"""
        <div style="background:linear-gradient(135deg,#0d1f3c,#05070a);border:1px solid #1f6feb;
                    border-radius:16px;padding:1.2rem;margin:1rem 0;">
          <div style="color:#58a6ff;font-size:0.75rem;letter-spacing:2px;">YOUR COSMIC CARD</div>
          <div style="font-size:1.4rem;font-weight:700;color:#fff;margin:0.4rem 0;">
            {n['sun_symbol']} {n['sun_sign']} · {n['moon_symbol']} {n['moon_sign']}
          </div>
          <div style="color:#bc8cff;">{n['phase_emoji']} Born under {n['phase_name']}</div>
          <div style="color:#8b949e;font-size:0.85rem;margin-top:0.4rem;">{my_card['display_name']}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Add your birth date above to unlock your Cosmic Card.")

    st.markdown("---")
    st.subheader("Send a Card Trade (Friend Request)")
    others = list_users_with_cards(user_hash)
    if not others:
        st.caption("No other cards yet. Share the app so friends can create theirs.")
    else:
        options = {
            f"{c['display_name']} ({c['natal']['sun_symbol']}{c['natal']['sun_sign']} · {c['natal']['moon_symbol']}{c['natal']['moon_sign']})": c["user_hash"]
            for c in others
        }
        pick = st.selectbox("Send card to", list(options.keys()))
        msg = st.text_input("Optional message", max_chars=200)
        if st.button("🃏 Send Trade"):
            ok, note = send_trade(user_hash, options[pick], msg)
            (st.success if ok else st.warning)(note)
            if ok:
                st.rerun()

    st.markdown("---")
    st.subheader("Incoming Trades")
    incoming = [t for t in list_trades(user_hash, "incoming") if t["status"] == "pending"]
    if not incoming:
        st.caption("No pending requests.")
    for t in incoming:
        sender_card = build_card(t["sender"])
        label = sender_card["display_name"] if sender_card else t["sender"][:8]
        cols = st.columns([3, 1, 1])
        cols[0].write(f"**{label}** wants to trade cards. {t['message'] or ''}")
        if cols[1].button("Accept", key=f"acc_{t['id']}"):
            resolve_trade(t["id"], user_hash, True)
            st.rerun()
        if cols[2].button("Decline", key=f"dec_{t['id']}"):
            resolve_trade(t["id"], user_hash, False)
            st.rerun()

    st.markdown("---")
    st.subheader("Friends (accepted trades)")
    friends = friends_of(user_hash)
    if not friends:
        st.caption("No friends yet — send or accept a card trade.")
    for fh in friends:
        fc = build_card(fh)
        if fc:
            n = fc["natal"]
            st.markdown(
                f"• **{fc['display_name']}** — {n['sun_symbol']} {n['sun_sign']} · {n['moon_symbol']} {n['moon_sign']}"
            )
