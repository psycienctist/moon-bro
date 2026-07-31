# cosmic_cards.py
# Birth-chart cosmic cards (date + time + location) + trade-as-friend-request

import streamlit as st
import sqlite3
import ephem
import math
from datetime import datetime, timezone, timedelta, date, time as dtime

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
            birth_time TEXT,
            birth_place TEXT,
            birth_lat REAL,
            birth_lon REAL,
            birth_utc_offset REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Migrate older DBs that only had display_name + birth_date
    c.execute("PRAGMA table_info(user_profiles)")
    cols = {row[1] for row in c.fetchall()}
    for col, typedef in [
        ("birth_time", "TEXT"),
        ("birth_place", "TEXT"),
        ("birth_lat", "REAL"),
        ("birth_lon", "REAL"),
        ("birth_utc_offset", "REAL"),
    ]:
        if col not in cols:
            c.execute(f"ALTER TABLE user_profiles ADD COLUMN {col} {typedef}")

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


def _sign_from_lon(lon_deg: float):
    idx = int(lon_deg / 30) % 12
    return ZODIAC[idx][0], ZODIAC[idx][1]


def _phase_from_frac(phase_frac: float):
    phases = [
        (0.00, "New Moon", "🌑"), (0.07, "Waxing Crescent", "🌒"),
        (0.25, "First Quarter", "🌓"), (0.43, "Waxing Gibbous", "🌔"),
        (0.50, "Full Moon", "🌕"), (0.57, "Waning Gibbous", "🌖"),
        (0.75, "Last Quarter", "🌗"), (0.93, "Waning Crescent", "🌘"),
        (1.00, "New Moon", "🌑"),
    ]
    for i in range(len(phases) - 1):
        if phases[i][0] <= phase_frac < phases[i + 1][0]:
            return phases[i][1], phases[i][2]
    return "New Moon", "🌑"


def _ascendant_lon(lst_hours: float, lat_deg: float, obliquity_deg: float = 23.4367) -> float:
    """Ecliptic longitude of the Ascendant (degrees 0–360)."""
    ramc = math.radians((lst_hours * 15.0) % 360.0)
    lat = math.radians(lat_deg)
    eps = math.radians(obliquity_deg)
    # tan(λ) = cos(RAMC) / (−sin(RAMC)*cos(ε) − tan(φ)*sin(ε))
    y = math.cos(ramc)
    x = -(math.sin(ramc) * math.cos(eps) + math.tan(lat) * math.sin(eps))
    asc = math.degrees(math.atan2(y, x)) % 360.0
    return asc


def natal_chart(
    dt_utc: datetime,
    lat: float | None = None,
    lon: float | None = None,
) -> dict:
    """Sun, Moon, phase, and Rising (if lat/lon provided)."""
    obs = ephem.Observer()
    if lat is not None and lon is not None:
        obs.lat = str(lat)
        obs.lon = str(lon)
    else:
        obs.lat = "0"
        obs.lon = "0"
    obs.date = ephem.Date(dt_utc)

    moon = ephem.Moon(obs)
    sun = ephem.Sun(obs)

    elong = float(moon.elong)
    if elong < 0:
        elong += 2 * math.pi
    phase_frac = elong / (2 * math.pi)
    phase_name, phase_emoji = _phase_from_frac(phase_frac)

    moon_lon = math.degrees(float(ephem.Ecliptic(moon).lon)) % 360
    sun_lon = math.degrees(float(ephem.Ecliptic(sun).lon)) % 360
    moon_sign, moon_symbol = _sign_from_lon(moon_lon)
    sun_sign, sun_symbol = _sign_from_lon(sun_lon)

    result = {
        "moon_sign": moon_sign,
        "moon_symbol": moon_symbol,
        "sun_sign": sun_sign,
        "sun_symbol": sun_symbol,
        "phase_name": phase_name,
        "phase_emoji": phase_emoji,
        "illum": moon.phase / 100.0,
        "moon_lon": moon_lon,
        "sun_lon": sun_lon,
        "rising_sign": None,
        "rising_symbol": None,
        "has_rising": False,
    }

    if lat is not None and lon is not None:
        try:
            lst = obs.sidereal_time()  # hours as ephem Angle
            lst_hours = float(lst) * 12.0 / math.pi  # radians → hours
            asc_lon = _ascendant_lon(lst_hours, float(lat))
            rising_sign, rising_symbol = _sign_from_lon(asc_lon)
            result["rising_sign"] = rising_sign
            result["rising_symbol"] = rising_symbol
            result["rising_lon"] = asc_lon
            result["has_rising"] = True
        except Exception:
            pass

    return result


def _local_to_utc(
    birth_date: str,
    birth_time: str | None,
    utc_offset: float | None,
) -> datetime:
    """Combine date + local time + UTC offset → aware UTC datetime."""
    d = date.fromisoformat(birth_date)
    if birth_time:
        try:
            parts = birth_time.strip().split(":")
            h, m = int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
            t = dtime(hour=h % 24, minute=m % 60)
        except Exception:
            t = dtime(12, 0)
    else:
        t = dtime(12, 0)  # noon local fallback

    local_naive = datetime.combine(d, t)
    offset_h = float(utc_offset) if utc_offset is not None else 0.0
    # local = UTC + offset  →  UTC = local − offset
    utc_naive = local_naive - timedelta(hours=offset_h)
    return utc_naive.replace(tzinfo=timezone.utc)


def get_or_create_profile(user_hash: str) -> dict:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        SELECT display_name, birth_date, birth_time, birth_place,
               birth_lat, birth_lon, birth_utc_offset
        FROM user_profiles WHERE user_hash=?
        """,
        (user_hash,),
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "display_name": row[0] or "Moon Wanderer",
            "birth_date": row[1],
            "birth_time": row[2],
            "birth_place": row[3],
            "birth_lat": row[4],
            "birth_lon": row[5],
            "birth_utc_offset": row[6] if row[6] is not None else 0.0,
        }
    return {
        "display_name": "Moon Wanderer",
        "birth_date": None,
        "birth_time": None,
        "birth_place": None,
        "birth_lat": None,
        "birth_lon": None,
        "birth_utc_offset": 0.0,
    }


def save_profile(
    user_hash: str,
    display_name: str,
    birth_date: str | None,
    birth_time: str | None = None,
    birth_place: str | None = None,
    birth_lat: float | None = None,
    birth_lon: float | None = None,
    birth_utc_offset: float | None = 0.0,
):
    init_cards_db()
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO user_profiles (
            user_hash, display_name, birth_date, birth_time,
            birth_place, birth_lat, birth_lon, birth_utc_offset
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_hash) DO UPDATE SET
            display_name=excluded.display_name,
            birth_date=excluded.birth_date,
            birth_time=excluded.birth_time,
            birth_place=excluded.birth_place,
            birth_lat=excluded.birth_lat,
            birth_lon=excluded.birth_lon,
            birth_utc_offset=excluded.birth_utc_offset
        """,
        (
            user_hash,
            display_name,
            birth_date,
            birth_time,
            birth_place,
            birth_lat,
            birth_lon,
            birth_utc_offset if birth_utc_offset is not None else 0.0,
        ),
    )
    conn.commit()
    conn.close()


def build_card(user_hash: str) -> dict | None:
    profile = get_or_create_profile(user_hash)
    if not profile["birth_date"]:
        return None
    try:
        dt_utc = _local_to_utc(
            profile["birth_date"],
            profile.get("birth_time"),
            profile.get("birth_utc_offset"),
        )
        lat = profile.get("birth_lat")
        lon = profile.get("birth_lon")
        natal = natal_chart(dt_utc, lat, lon)
        now = natal_chart(datetime.now(timezone.utc), lat, lon)
        return {
            "user_hash": user_hash,
            "display_name": profile["display_name"],
            "birth_date": profile["birth_date"],
            "birth_time": profile.get("birth_time"),
            "birth_place": profile.get("birth_place"),
            "birth_lat": lat,
            "birth_lon": lon,
            "natal": natal,
            "now": now,
        }
    except Exception:
        return None


def list_users_with_cards(exclude_hash: str) -> list:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        SELECT user_hash FROM user_profiles
        WHERE birth_date IS NOT NULL AND user_hash != ?
        """,
        (exclude_hash,),
    )
    rows = c.fetchall()
    conn.close()
    out = []
    for (h,) in rows:
        card = build_card(h)
        if card:
            out.append(card)
    return out


def send_trade(sender: str, receiver: str, message: str = ""):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        SELECT id FROM card_trades
        WHERE sender_hash=? AND receiver_hash=? AND status='pending'
        """,
        (sender, receiver),
    )
    if c.fetchone():
        conn.close()
        return False, "Already have a pending trade with this person."
    c.execute(
        """
        INSERT INTO card_trades (sender_hash, receiver_hash, message, status)
        VALUES (?, ?, ?, 'pending')
        """,
        (sender, receiver, message.strip() or None),
    )
    conn.commit()
    conn.close()
    return True, "Trade (friend request) sent!"


def list_trades(user_hash: str, direction: str = "all") -> list:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    if direction == "incoming":
        c.execute(
            """
            SELECT id, sender_hash, receiver_hash, message, status, created_at
            FROM card_trades WHERE receiver_hash=? ORDER BY created_at DESC
            """,
            (user_hash,),
        )
    elif direction == "outgoing":
        c.execute(
            """
            SELECT id, sender_hash, receiver_hash, message, status, created_at
            FROM card_trades WHERE sender_hash=? ORDER BY created_at DESC
            """,
            (user_hash,),
        )
    else:
        c.execute(
            """
            SELECT id, sender_hash, receiver_hash, message, status, created_at
            FROM card_trades
            WHERE sender_hash=? OR receiver_hash=?
            ORDER BY created_at DESC
            """,
            (user_hash, user_hash),
        )
    rows = c.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "sender": r[1],
            "receiver": r[2],
            "message": r[3],
            "status": r[4],
            "created_at": r[5],
        }
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
    c.execute(
        "UPDATE card_trades SET status=?, resolved_at=CURRENT_TIMESTAMP WHERE id=?",
        (status, trade_id),
    )
    conn.commit()
    conn.close()
    return True


def friends_of(user_hash: str) -> list:
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        """
        SELECT sender_hash, receiver_hash FROM card_trades
        WHERE status='accepted' AND (sender_hash=? OR receiver_hash=?)
        """,
        (user_hash, user_hash),
    )
    friends = set()
    for s, r in c.fetchall():
        friends.add(r if s == user_hash else s)
    conn.close()
    return list(friends)


def _card_html(card: dict, title: str = "YOUR COSMIC CARD") -> str:
    n = card["natal"]
    place = card.get("birth_place") or ""
    btime = card.get("birth_time") or ""
    bdate = card.get("birth_date") or ""
    rising_line = ""
    if n.get("has_rising") and n.get("rising_sign"):
        rising_line = (
            f"<div style='color:#58a6ff;margin-top:0.35rem;'>"
            f"↑ Rising {n['rising_symbol']} {n['rising_sign']}</div>"
        )
    meta = " · ".join(x for x in [bdate, btime, place] if x)
    return f"""
    <div style="background:linear-gradient(135deg,#0d1f3c,#05070a);border:1px solid #1f6feb;
                border-radius:16px;padding:1.2rem;margin:1rem 0;">
      <div style="color:#58a6ff;font-size:0.75rem;letter-spacing:2px;">{title}</div>
      <div style="font-size:1.35rem;font-weight:700;color:#fff;margin:0.4rem 0;">
        {n['sun_symbol']} Sun {n['sun_sign']} · {n['moon_symbol']} Moon {n['moon_sign']}
      </div>
      {rising_line}
      <div style="color:#bc8cff;margin-top:0.35rem;">{n['phase_emoji']} Born under {n['phase_name']}</div>
      <div style="color:#8b949e;font-size:0.85rem;margin-top:0.5rem;">{card['display_name']}</div>
      <div style="color:#484f58;font-size:0.7rem;margin-top:0.25rem;">{meta}</div>
    </div>
    """


def render_profile_form(user_hash: str, key_prefix: str = "cards"):
    """Shared birth-data form. Returns True if saved this run."""
    profile = get_or_create_profile(user_hash)

    name = st.text_input(
        "Display name",
        value=profile["display_name"] or "Moon Wanderer",
        key=f"{key_prefix}_name",
    )

    default_bd = (
        date.fromisoformat(profile["birth_date"])
        if profile["birth_date"]
        else date(1990, 1, 1)
    )
    bd = st.date_input(
        "Birth date",
        value=default_bd,
        min_value=date(1920, 1, 1),
        max_value=date.today(),
        key=f"{key_prefix}_bd",
    )

    # Birth time
    default_time = dtime(12, 0)
    if profile.get("birth_time"):
        try:
            hp, mp = profile["birth_time"].split(":")[:2]
            default_time = dtime(int(hp), int(mp))
        except Exception:
            pass
    bt = st.time_input("Birth time (local)", value=default_time, key=f"{key_prefix}_bt")

    place = st.text_input(
        "Birth place (city, country)",
        value=profile.get("birth_place") or "",
        placeholder="e.g. Austin, Texas",
        key=f"{key_prefix}_place",
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        lat = st.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            value=float(profile["birth_lat"]) if profile.get("birth_lat") is not None else 30.27,
            step=0.01,
            format="%.4f",
            key=f"{key_prefix}_lat",
            help="Positive = North",
        )
    with c2:
        lon = st.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            value=float(profile["birth_lon"]) if profile.get("birth_lon") is not None else -97.74,
            step=0.01,
            format="%.4f",
            key=f"{key_prefix}_lon",
            help="Negative = West",
        )
    with c3:
        utc_off = st.number_input(
            "UTC offset (hours)",
            min_value=-12.0,
            max_value=14.0,
            value=float(profile["birth_utc_offset"]) if profile.get("birth_utc_offset") is not None else -6.0,
            step=0.5,
            key=f"{key_prefix}_utc",
            help="Local time − UTC. EST=-5, CST=-6, PST=-8, GMT=0",
        )

    st.caption(
        "Tip: look up your city’s lat/lon (e.g. Google “Austin coordinates”). "
        "UTC offset is for your birth time zone — ignore daylight-saving quirks if unsure."
    )

    if st.button("💾 Save birth chart data", type="primary", key=f"{key_prefix}_save"):
        time_str = f"{bt.hour:02d}:{bt.minute:02d}"
        save_profile(
            user_hash,
            name.strip() or "Moon Wanderer",
            bd.isoformat(),
            birth_time=time_str,
            birth_place=place.strip() or None,
            birth_lat=float(lat),
            birth_lon=float(lon),
            birth_utc_offset=float(utc_off),
        )
        st.session_state.display_name = name.strip() or "Moon Wanderer"
        st.session_state.birth_date = bd
        # Keep auth.users in sync if logged in
        try:
            import auth

            if st.session_state.get("username"):
                auth.update_user_profile(
                    st.session_state.username,
                    name.strip() or "Moon Wanderer",
                    bd.isoformat(),
                    birth_time=time_str,
                    birth_place=place.strip() or None,
                    birth_lat=float(lat),
                    birth_lon=float(lon),
                    birth_utc_offset=float(utc_off),
                )
        except Exception:
            pass
        st.success("Birth chart data saved — your Cosmic Card is ready.")
        st.rerun()
        return True
    return False


def render_cosmic_cards_tab():
    init_cards_db()
    user_hash = st.session_state.get("user_hash", "anonymous")

    st.markdown("### 🃏 Cosmic Cards & Friend Trades")
    st.caption(
        "Your birth chart card uses date, time, and place. "
        "Send it as a friend request."
    )

    profile = get_or_create_profile(user_hash)
    needs_data = not profile.get("birth_date")
    with st.expander("🧬 Your birth chart data", expanded=needs_data):
        render_profile_form(user_hash, key_prefix="cards")

    my_card = build_card(user_hash)
    if my_card:
        st.markdown(_card_html(my_card), unsafe_allow_html=True)
        n = my_card["natal"]
        if not n.get("has_rising"):
            st.info("Add latitude & longitude above to unlock your Rising sign.")
    else:
        st.info("Add your birth date (and ideally time + place) to unlock your Cosmic Card.")

    st.markdown("---")
    st.subheader("Send a Card Trade (Friend Request)")
    others = list_users_with_cards(user_hash)
    if not others:
        st.caption("No other cards yet. Share the app so friends can create theirs.")
    else:
        options = {}
        for c in others:
            n = c["natal"]
            rising = f" · ↑{n['rising_symbol']}{n['rising_sign']}" if n.get("has_rising") else ""
            label = (
                f"{c['display_name']} "
                f"({n['sun_symbol']}{n['sun_sign']} · {n['moon_symbol']}{n['moon_sign']}{rising})"
            )
            options[label] = c["user_hash"]
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
        if sender_card:
            cols[0].markdown(_card_html(sender_card, "THEIR CARD"), unsafe_allow_html=True)
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
            rising = f" · ↑ {n['rising_symbol']} {n['rising_sign']}" if n.get("has_rising") else ""
            place = f" · {fc['birth_place']}" if fc.get("birth_place") else ""
            st.markdown(
                f"• **{fc['display_name']}** — "
                f"{n['sun_symbol']} {n['sun_sign']} · {n['moon_symbol']} {n['moon_sign']}"
                f"{rising}{place}"
            )
