"""Lunatick Tarot: reflective, non-fatalistic readings using the public-domain Rider–Waite–Smith deck.

Readings are symbolic prompts, not certain predictions. Artwork is served from Wikimedia Commons'
Special:FilePath endpoint; internet access is needed to display the card images.
"""
from __future__ import annotations

import random
import hashlib
from datetime import date, datetime
from zoneinfo import ZoneInfo
from urllib.parse import quote
import streamlit as st
import reading_requests

TAROT_MODULE_VERSION = "personalized_daily_tarot_v2"

MAJORS = [
("The Fool","beginnings, openness, a leap of faith","recklessness, hesitation, or a need to check your footing","Approach the next step with curiosity, while giving yourself enough information to feel grounded."),
("The Magician","initiative, resourcefulness, focused action","scattered effort, self-doubt, or using influence carelessly","You may have more tools than you realize. Choose one clear intention and put a practical skill to work."),
("The High Priestess","intuition, quiet knowledge, patient observation","noise, withheld information, or disconnect from your inner voice","Make room for stillness. You do not need to force an answer before you have listened carefully."),
("The Empress","nurturing, creativity, growth, abundance","overgiving, stagnation, or neglecting your own needs","Growth is supported by care. Include yourself in the care you offer others."),
("The Emperor","structure, boundaries, responsibility","rigidity, control, or a lack of useful structure","A steady framework can help you feel safer and act more confidently. Keep structure flexible enough to serve people."),
("The Hierophant","learning, shared wisdom, tradition, belonging","questioning conventions, restrictive rules, or finding your own path","Learn from trusted sources, then decide which principles genuinely fit your life."),
("The Lovers","connection, values, meaningful choice","misalignment, avoidance, or a need for honest communication","Bring your choices into line with your values. Clear, respectful honesty can deepen connection."),
("The Chariot","determination, direction, self-command","conflicting priorities, forcing progress, or losing focus","Progress comes from steering competing impulses toward one chosen destination."),
("Strength","courage, patience, compassionate confidence","harsh self-judgment, exhaustion, or reacting from fear","Gentleness is not weakness. A calm response may accomplish more than trying to overpower the situation."),
("The Hermit","reflection, solitude, inner guidance","isolation, overthinking, or reluctance to reconnect","Take space to hear yourself, but remember you can return to others when you are ready."),
("Wheel of Fortune","change, cycles, opportunity, turning points","resistance to change, unstable timing, or repeating patterns","You cannot control every turn, but you can notice the pattern and choose how to meet this moment."),
("Justice","fairness, accountability, clear-eyed decisions","bias, avoidance of responsibility, or an incomplete picture","Look at the facts with compassion and honesty. A balanced decision considers both impact and context."),
("The Hanged Man","pause, surrender, a fresh perspective","stalled action, needless sacrifice, or resisting a useful pause","A pause can be productive when it helps you see differently. Decide what is worth releasing and what needs action."),
("Death","ending, transition, renewal, letting go","clinging to an expired chapter, fear of change, or unfinished closure","This card is about transition, not literal death. Naming what has run its course can make room for renewal."),
("Temperance","balance, integration, patience, healing","extremes, impatience, or difficulty finding a workable middle","Small adjustments can restore balance. Give different needs time to find a sustainable rhythm."),
("The Devil","attachment, temptation, limiting patterns","recognizing a pattern, reclaiming agency, or loosening a bond","Notice where you feel stuck without shaming yourself. Naming a pattern is a first step toward choosing differently."),
("The Tower","disruption, revelation, unstable foundations","fear of change, delayed truth, or rebuilding after upheaval","A sudden change can be difficult, but it can also reveal what needs repair. Start with what is real and rebuild one piece at a time."),
("The Star","hope, renewal, perspective, quiet trust","discouragement, depleted faith, or needing rest","Hope does not require certainty. Let one small, restorative action remind you that recovery can begin gently."),
("The Moon","uncertainty, dreams, intuition, ambiguity","confusion clearing, checking assumptions, or fear shaping perception","Not everything is clear yet. Separate what you know from what you fear, and let evidence emerge before deciding."),
("The Sun","clarity, vitality, warmth, confidence","temporary low energy, overexposure, or overlooking a simple joy","Make room for what is working. A realistic moment of joy can be meaningful even when life remains complicated."),
("Judgement","reckoning, self-forgiveness, awakening, a new chapter","harsh self-criticism, avoiding a call, or difficulty moving on","Review the past to learn, not to punish yourself. You can acknowledge what happened and still choose a new response."),
("The World","completion, integration, accomplishment","unfinished business, a delayed milestone, or difficulty recognizing progress","Notice how far you have come. If something remains, define the final practical step rather than dismissing the whole journey."),
]

SUITS = {
"Wands": ("fire, energy, creativity, initiative", "bold action, inspiration, momentum", "burnout, impatience, scattered energy", "Choose a manageable action that gives your enthusiasm somewhere useful to go."),
"Cups": ("water, feelings, relationships, imagination", "emotional honesty, connection, compassion", "avoidance, overwhelm, unclear boundaries", "Make space for your feelings without treating every feeling as a final verdict."),
"Swords": ("air, thought, communication, discernment", "clarity, truth, decisions, perspective", "mental overload, conflict, assumptions", "Slow the story down. Identify the facts, name the concern, and choose the next clear conversation or decision."),
"Pentacles": ("earth, resources, work, body, daily life", "patience, stability, practical growth", "scarcity thinking, rigidity, neglected basics", "Support the larger goal with one concrete, sustainable step in everyday life."),
}
RANKS = [
("Ace","a seed of potential, a fresh opening","hesitation, an opening needing care"),
("Two","choice, balance, or collaboration","indecision, imbalance, or competing needs"),
("Three","learning through teamwork and practice","miscommunication, uneven effort, or a need to refine"),
("Four","stability, protection, or consolidation","holding too tightly, restlessness, or reconsidering security"),
("Five","friction, challenge, or adjustment","repair, perspective, or moving beyond unhelpful conflict"),
("Six","progress, support, or a transition","slow progress, lingering baggage, or accepting help"),
("Seven","assessment, perseverance, or discernment","second-guessing, impatience, or revising a strategy"),
("Eight","movement, dedication, or focused effort","delays, scattered attention, or a need to reset"),
("Nine","near-completion, independence, or resilience","fatigue, overextension, or asking for support"),
("Ten","culmination, responsibility, or a larger pattern","a burden to redistribute, a cycle ending, or simplifying"),
("Page","curiosity, a message, or beginner's mind","inexperience, distraction, or a lesson not yet integrated"),
("Knight","pursuit, momentum, or a chosen approach","overdoing it, inconsistency, or acting before reflecting"),
("Queen","mature understanding, stewardship, or inner mastery","neglecting your own needs, insecurity, or imbalance"),
("King","leadership, command, or responsible mastery","rigidity, overcontrol, or a need to lead more thoughtfully"),
]

def _image_url(card: dict) -> str:
    filename = card.get("image_file")
    return "https://commons.wikimedia.org/wiki/Special:FilePath/" + quote(filename) if filename else ""

def build_deck() -> list[dict]:
    deck = []
    for index, (name, upright, reversed_meaning, advice) in enumerate(MAJORS):
        deck.append({"name": name, "arcana": "Major Arcana", "upright": upright,
                     "reversed": reversed_meaning, "advice": advice,
                     "keywords": upright, "image_file": f"RWS Tarot {index:02d} {name.removeprefix('The ')}.jpg"})
    for suit, (element, themes, shadows, advice) in SUITS.items():
        for rank_index, (rank, theme, shadow) in enumerate(RANKS):
            name = f"{rank} of {suit}"
            deck.append({
                "name": name, "arcana": "Minor Arcana", "suit": suit, "element": element,
                "upright": f"{theme}; {themes}",
                "reversed": f"{shadow}; {shadows}",
                "advice": advice,
                "keywords": f"{theme}; {element}",
                "image_file": f"{ {'Wands': 'Wands', 'Cups': 'Cups', 'Swords': 'Swords', 'Pentacles': 'Pents'}[suit] }{ (rank_index + 1):02d}.jpg",
            })
    return deck

DECK = build_deck()
POSITIONS = {
    "One-card reflection": ["Your focus"],
    "Three-card reflection": ["What shaped this", "What is present", "A helpful next step"],
    "Celtic Cross": ["Present situation", "The crossing influence", "The foundation", "Recent past", "What you are reaching toward", "Near-term direction", "Your stance", "Your environment", "Hopes and concerns", "A possible trajectory"],
}

def _draw_cards(count: int) -> list[tuple[dict, bool]]:
    chosen = random.sample(DECK, count)
    return [(card, random.random() < 0.28) for card in chosen]

def _display_card(card: dict, reversed_card: bool, position: str) -> None:
    with st.container(border=True):
        st.markdown(f"**{position}**")
        st.markdown(f"### {card['name']}" + (" · Reversed" if reversed_card else ""))
        url = _image_url(card)
        if url:
            st.image(url, width=110)
        meaning = card["reversed"] if reversed_card else card["upright"]
        st.caption("Reversed reading" if reversed_card else "Upright reading")
        st.write(meaning.capitalize() + ".")
        st.write("**A constructive way forward:** " + card["advice"])
        st.caption("Keywords: " + card["keywords"])

def _render_sample_reading() -> None:
    """Show an illustrative reading immediately so first-time visitors understand the experience."""
    st.markdown("### A sample reading")
    st.caption("Illustrative example only — these cards were chosen for the demo, not drawn for you.")
    sample = [
        (DECK[[c["name"] for c in DECK].index("Justice")], False, "What shaped this"),
        (DECK[[c["name"] for c in DECK].index("Six of Swords")], False, "What is present"),
        (DECK[[c["name"] for c in DECK].index("Ten of Pentacles")], False, "A helpful next step"),
    ]
    cols = st.columns(3)
    for col, (card, reversed_card, position) in zip(cols, sample):
        with col:
            _display_card(card, reversed_card, position)
    st.markdown("**The story connecting these cards**")
    st.write(
        "Justice asks for a clear-eyed and fair look at what has happened. The Six of Swords "
        "then points toward moving out of turbulence one manageable step at a time, even if "
        "the transition is not instant. The Ten of Pentacles brings the focus to the kind of "
        "stability, belonging, and long-term support you want to build. Together, the cards "
        "suggest that honest reflection can help you move toward calmer ground and make choices "
        "that serve your longer-term wellbeing. They do not guarantee an outcome; they offer "
        "a useful question: what fair, practical choice would make your future feel more secure?"
    )


def _combine_three_cards(cards: list[tuple[dict, bool]], intention: str = "", chart: dict | None = None) -> str:
    """Synthesize the specific cards into a practical, non-fatalistic story."""
    positions = POSITIONS["Three-card reflection"]
    rendered = []
    for (card, reversed_card), position in zip(cards, positions):
        meaning = card["reversed"] if reversed_card else card["upright"]
        rendered.append(f"**{position} — {card['name']}{' (reversed)' if reversed_card else ''}:** {meaning.capitalize()}.")

    first, second, third = cards
    c1, r1 = first
    c2, r2 = second
    c3, r3 = third
    m1 = c1["reversed"] if r1 else c1["upright"]
    m2 = c2["reversed"] if r2 else c2["upright"]
    m3 = c3["reversed"] if r3 else c3["upright"]
    first_theme = c1.get("keywords", m1).split(";")[0].strip().lower()
    second_theme = c2.get("keywords", m2).split(";")[0].strip().lower()
    third_advice = c3.get("advice", "Choose one practical step and see what you learn.")
    transition = (
        f"The movement from **{c1['name']}** to **{c2['name']}** shifts the focus from {first_theme} "
        f"toward {second_theme}. Rather than treating those themes as separate predictions, ask how the "
        "first may be shaping the second in your actual circumstances."
    )
    direction = (
        f"**A useful way to work with this:** {third_advice} "
        f"That makes **{c3['name']}** a practical response to the tension or opportunity raised by the first two cards."
    )
    intention_line = f"**Your question:** {intention.strip()}\n\n" if intention.strip() else ""
    story = (
        f"{intention_line}Read this spread as a reflection, not a fixed forecast. "
        f"**The pattern:** {m1}. **What needs attention now:** {m2}. "
        f"{transition}\n\n{direction}\n\n"
        "**Keep it grounded:** choose one small action you can take, identify what evidence would tell you it is helping, "
        "and revise your approach as needed. Difficult cards can point to something worth facing; they do not guarantee harm."
    )
    if chart:
        natal = chart.get("natal", chart)
        sun, moon, rising = natal.get("sun_sign"), natal.get("moon_sign"), natal.get("rising_sign")
        details = []
        if sun: details.append(f"Sun in {sun} (identity and direction)")
        if moon: details.append(f"Moon in {moon} (emotional needs)")
        if rising: details.append(f"Rising sign {rising} (how you approach new situations)")
        if details:
            story += "\n\n**Optional birth-chart lens:** Using only the chart saved to your own account, consider this reading alongside " + ", ".join(details) + ". Treat these as symbolic prompts, not proven personality facts. Your birth date, time, and place are not included here."
    return "\n\n".join(rendered) + "\n\n" + story


def _daily_draw(user_key: str, day: date | None = None) -> list[tuple[dict, bool]]:
    """Stable daily draw per account and date; anonymous visitors share a session-local key."""
    day = day or datetime.now(ZoneInfo("America/New_York")).date()
    seed = hashlib.sha256(f"lunatick-tarot:{user_key}:{day.isoformat()}".encode("utf-8")).hexdigest()
    rng = random.Random(seed)
    chosen = rng.sample(DECK, 3)
    return [(card, rng.random() < 0.28) for card in chosen]


def render_tarot() -> None:
    tarot_tab, private_tab = st.tabs(["Tarot", "Community Requests"])
    with private_tab:
        reading_requests.render_reading_requests()
    with tarot_tab:
        st.markdown("## ✦ Tarot")
        st.caption("A reflective reading for perspective—not a fixed prediction or a substitute for your own judgment.")
        st.markdown(
            "<div style='border:1px solid rgba(188,140,255,.4);border-radius:12px;padding:.8rem 1rem;margin:.4rem 0 1rem;background:linear-gradient(145deg,rgba(35,22,65,.55),rgba(5,7,10,.8));'>"
            "<strong>Our reading promise</strong><br>Honest about challenges. Open to possibilities. No doom, fear tactics, or false certainty."
            "</div>", unsafe_allow_html=True
        )
    
        st.markdown("### Your daily three-card reflection")
        st.caption("Your cards stay the same for the day and refresh tomorrow. This is a reflective prompt, not a prediction.")
        authenticated = bool(st.session_state.get("is_authenticated")) and str(st.session_state.get("user_hash") or "anonymous") != "anonymous"
        use_chart = False
        chart = None
        if authenticated:
            use_chart = st.checkbox(
                "Personalize with my saved birth chart (optional)",
                value=False,
                key="tarot_daily_use_birth_chart",
                help="Only your own saved chart is used. Your birth date, time, and place are not displayed in the reading."
            )
            if use_chart:
                try:
                    import cosmic_cards
                    chart = cosmic_cards.build_card(str(st.session_state.get("user_hash")))
                except Exception:
                    chart = None
                if not chart:
                    st.info("No usable birth chart was found on your account. Add or correct your saved birth details in your profile to use this option.")
        else:
            st.caption("Sign in to keep a daily draw tied to your account and optionally use your own saved birth chart.")
        daily_key = str(st.session_state.get("user_hash") or "anonymous")
        if daily_key == "anonymous":
            if "tarot_anonymous_daily_key" not in st.session_state:
                st.session_state["tarot_anonymous_daily_key"] = hashlib.sha256(str(random.random()).encode()).hexdigest()
            daily_key = st.session_state["tarot_anonymous_daily_key"]
        daily_cards = _daily_draw(daily_key)
        st.caption("Today's cards")
        daily_cols = st.columns(3)
        for col, ((card, reversed_card), position) in zip(daily_cols, zip(daily_cards, POSITIONS["Three-card reflection"])):
            with col:
                _display_card(card, reversed_card, position)
        st.markdown("**The story connecting today's cards**")
        st.markdown(_combine_three_cards(daily_cards, chart=chart if use_chart else None))
        st.markdown("---")
        _render_sample_reading()
        st.markdown("---")
        st.markdown("### Choose your own three cards")
        st.write("Browse the deck and select one card for each position. Your cards are revealed together when you are ready.")
        intention = st.text_input(
            "Optional question or intention", max_chars=240,
            placeholder="What would be useful to reflect on?", key="tarot_intention_picker"
        )
        st.caption("You can leave this blank. Avoid entering private information you would not want saved in the app session.")
    
        # Shuffle the complete deck once per session; the grid shows identical backs until reveal.
        if "tarot_grid_order" not in st.session_state:
            st.session_state["tarot_grid_order"] = random.sample(DECK, len(DECK))
        if "tarot_grid_selected" not in st.session_state:
            st.session_state["tarot_grid_selected"] = []
        if "tarot_grid_revealed" not in st.session_state:
            st.session_state["tarot_grid_revealed"] = False

        labels = ["What shaped this", "What is present", "A helpful next step"]
        selected_indices = st.session_state["tarot_grid_selected"]
        st.caption(f"Cards selected: {len(selected_indices)} of 3")
        st.write("Tap any three face-down cards. Their identities stay hidden until you reveal your draw.")

        # Six columns on desktop; CSS wraps into a larger three-column tap grid on phones.
        with st.container(key="tarot_picker_grid"):
            for start in range(0, len(DECK), 6):
                cols = st.columns(6)
                for offset, col in enumerate(cols):
                    grid_index = start + offset
                    if grid_index >= len(DECK):
                        continue
                    with col:
                        is_selected = grid_index in selected_indices
                        if st.session_state["tarot_grid_revealed"] and is_selected:
                            card_name = st.session_state["tarot_grid_order"][grid_index]["name"]
                            button_label = "✓"
                            help_text = card_name
                        else:
                            button_label = "✦" if not is_selected else "✓"
                            help_text = "Selected card" if is_selected else "Face-down tarot card"
                        disabled = st.session_state["tarot_grid_revealed"] or (len(selected_indices) >= 3 and not is_selected)
                        if st.button(button_label, key=f"tarot_grid_card_{grid_index}", help=help_text,
                                     use_container_width=True, disabled=disabled):
                            if is_selected:
                                selected_indices.remove(grid_index)
                            elif len(selected_indices) < 3:
                                selected_indices.append(grid_index)
                            st.session_state["tarot_grid_selected"] = selected_indices
                            st.rerun()

        selected_animation_css = "".join(
            f".st-key-tarot_grid_card_{idx} button{{animation:tarotFlip .55s ease-out;}}"
            for idx in selected_indices
        )
        st.markdown(
            "<style>"
            "@keyframes tarotFlip{0%{transform:perspective(500px) rotateY(0deg) scale(1);}"
            "45%{transform:perspective(500px) rotateY(90deg) scale(.94);}"
            "100%{transform:perspective(500px) rotateY(0deg) scale(1);}}"
            ".st-key-tarot_picker_grid [data-testid=\"stHorizontalBlock\"]{gap:.4rem!important;}"
            ".st-key-tarot_picker_grid [data-testid=\"column\"]{min-width:0!important;}"
            ".st-key-tarot_picker_grid button{min-height:58px!important;font-size:1.25rem!important;"
            "border:1px solid rgba(188,140,255,.65)!important;border-radius:9px!important;"
            "background:linear-gradient(145deg,rgba(49,31,84,.95),rgba(9,12,22,.98))!important;"
            "box-shadow:inset 0 0 0 2px rgba(188,140,255,.08);transition:transform .2s ease,border-color .2s ease;}"
            ".st-key-tarot_picker_grid button:hover{border-color:#d7b7ff!important;transform:translateY(-2px);}"
            "@media(max-width:600px){"
            ".st-key-tarot_picker_grid [data-testid=\"stHorizontalBlock\"]{flex-wrap:wrap!important;}"
            ".st-key-tarot_picker_grid [data-testid=\"column\"]{flex:1 0 28%!important;width:28%!important;min-width:28%!important;}"
            "}"
            "@media(prefers-reduced-motion:reduce){.st-key-tarot_picker_grid button{animation:none!important;transition:none!important;}}"
            + selected_animation_css +
            "</style>", unsafe_allow_html=True
        )
        if len(selected_indices) == 3 and not st.session_state["tarot_grid_revealed"]:
            if st.button("Reveal my three cards", type="primary", use_container_width=True, key="tarot_reveal_grid"):
                st.session_state["tarot_grid_revealed"] = True
                st.session_state["tarot_selected_reading"] = {
                    "cards": [
                        (st.session_state["tarot_grid_order"][idx]["name"], random.random() < 0.28)
                        for idx in selected_indices
                    ],
                    "intention": intention.strip(),
                }
                st.rerun()

        if st.session_state["tarot_grid_revealed"]:
            reading = st.session_state.get("tarot_selected_reading")
            if reading:
                lookup = {card["name"]: card for card in DECK}
                drawn = [(lookup[name], reversed_card) for name, reversed_card in reading["cards"]]
                st.markdown("### Your revealed reading")
                st.markdown(
                    "<style>.st-key-tarot_reveal_row [data-testid=\"stHorizontalBlock\"]{flex-wrap:nowrap!important;gap:.45rem!important}"
                    ".st-key-tarot_reveal_row [data-testid=\"stHorizontalBlock\"]>div[data-testid=\"column\"]{min-width:0!important;flex:1 1 0!important;width:33.333%!important}"
                    ".st-key-tarot_reveal_row img{max-width:100%!important;height:auto!important}"
                    ".st-key-tarot_reveal_row [data-testid=\"stMarkdownContainer\"]{overflow-wrap:anywhere;font-size:.88rem}"
                    "@media(max-width:600px){.st-key-tarot_reveal_row [data-testid=\"stHorizontalBlock\"]{flex-wrap:wrap!important}"
                    ".st-key-tarot_reveal_row [data-testid=\"stHorizontalBlock\"]>div[data-testid=\"column\"]{flex:1 1 100%!important;width:100%!important;min-width:100%!important}}"
                    "@media(prefers-reduced-motion:reduce){.st-key-tarot_reveal_row *{scroll-behavior:auto!important;}}"
                    "</style>", unsafe_allow_html=True
                )
                with st.container(key="tarot_reveal_row"):
                    reveal_cols = st.columns(3, gap="small")
                    for col, ((card, reversed_card), position) in zip(reveal_cols, zip(drawn, labels)):
                        with col:
                            _display_card(card, reversed_card, position)
                st.markdown("### Bringing the reading together")
                st.markdown(_combine_three_cards(drawn, reading.get("intention", ""), chart=chart if use_chart else None))
                st.info(
                    "Reflection, not fate: a difficult theme is not a sentence or a guarantee. "
                    "Use it as a prompt to prepare, seek support, set a boundary, or choose a different approach."
                )
            if st.button("Shuffle and draw again", use_container_width=True, key="tarot_grid_shuffle_again"):
                st.session_state["tarot_grid_order"] = random.sample(DECK, len(DECK))
                st.session_state["tarot_grid_selected"] = []
                st.session_state["tarot_grid_revealed"] = False
                st.session_state.pop("tarot_selected_reading", None)
                st.rerun()

        with st.expander("Browse all 78 cards and their meanings"):
            for card in DECK:
                st.markdown(f"**{card['name']}** — {card['upright']}.")
                st.caption("Reversed: " + card["reversed"] + ".")
