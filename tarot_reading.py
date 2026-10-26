"""Lunatick Tarot: reflective, non-fatalistic readings using the public-domain Rider–Waite–Smith deck.

Readings are symbolic prompts, not certain predictions. Artwork is served from Wikimedia Commons'
Special:FilePath endpoint; internet access is needed to display the card images.
"""
from __future__ import annotations

import random
from urllib.parse import quote
import streamlit as st

TAROT_MODULE_VERSION = "lunatick_tarot_v1"

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
            st.image(url, width=180)
        meaning = card["reversed"] if reversed_card else card["upright"]
        st.caption("Reversed reading" if reversed_card else "Upright reading")
        st.write(meaning.capitalize() + ".")
        st.write("**A constructive way forward:** " + card["advice"])
        st.caption("Keywords: " + card["keywords"])

def _render_sample_reading() -> None:
    """Show three compact sample cards in one row, including on portrait phones."""
    st.markdown("### A sample reading")
    st.caption("Illustrative example only — these cards were chosen for the demo, not drawn for you.")
    sample = [
        (DECK[[c["name"] for c in DECK].index("Justice")], False, "What shaped this"),
        (DECK[[c["name"] for c in DECK].index("Six of Swords")], False, "What is present"),
        (DECK[[c["name"] for c in DECK].index("Ten of Pentacles")], False, "A helpful next step"),
    ]

    # Streamlit may stack columns at narrow viewport widths. Override that behavior
    # only inside this sample-card row, so all three cards remain visible on phones.
    st.markdown(
        "<style>"
        ".st-key-tarot_sample_cards [data-testid='stHorizontalBlock']{"
        "flex-wrap:nowrap!important;gap:.35rem!important;align-items:flex-start!important;}"
        ".st-key-tarot_sample_cards [data-testid='column']{"
        "min-width:0!important;width:33.333%!important;flex:1 1 0!important;padding:0!important;}"
        ".st-key-tarot_sample_cards [data-testid='stImage'] img{"
        "width:100%!important;max-height:145px!important;object-fit:contain!important;}"
        ".st-key-tarot_sample_cards [data-testid='stMarkdownContainer'] p{"
        "font-size:.76rem!important;line-height:1.2!important;overflow-wrap:anywhere!important;}"
        ".st-key-tarot_sample_cards .stButton button{"
        "min-height:2rem!important;padding:.25rem .15rem!important;font-size:.7rem!important;}"
        "</style>",
        unsafe_allow_html=True,
    )

    active_key = "tarot_sample_active_card"
    active = st.session_state.get(active_key, 0)
    with st.container(key="tarot_sample_cards"):
        cols = st.columns(3, gap="small")
        for index, (col, (card, reversed_card, position)) in enumerate(zip(cols, sample)):
            with col:
                st.markdown(
                    f"<div style='text-align:center;font-size:.7rem;font-weight:700;min-height:2.5rem;line-height:1.2;'>{position}</div>",
                    unsafe_allow_html=True,
                )
                url = _image_url(card)
                if url:
                    st.image(url, use_container_width=True)
                else:
                    st.markdown("🂠")
                st.markdown(
                    f"<div style='text-align:center;font-weight:700;font-size:.8rem;line-height:1.2;overflow-wrap:anywhere;'>{card['name']}</div>",
                    unsafe_allow_html=True,
                )
                if st.button(
                    "Meaning" if active != index else "Selected",
                    key=f"tarot_sample_card_{index}",
                    use_container_width=True,
                    type="primary" if active == index else "secondary",
                ):
                    st.session_state[active_key] = index
                    active = index

    card, reversed_card, position = sample[active]
    meaning = card["reversed"] if reversed_card else card["upright"]
    st.markdown("---")
    st.markdown(f"### {card['name']} — {position}")
    st.write(meaning.capitalize() + ".")
    st.write("**A constructive way forward:** " + card["advice"])
    st.caption("Keywords: " + card["keywords"])

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

def _combine_three_cards(cards: list[tuple[dict, bool]], intention: str = "") -> str:
    """Create a position-aware narrative rather than repeating generic card definitions."""
    positions = POSITIONS["Three-card reflection"]
    lines = []
    for (card, reversed_card), position in zip(cards, positions):
        meaning = card["reversed"] if reversed_card else card["upright"]
        lines.append(f"**{position} — {card['name']}{' (reversed)' if reversed_card else ''}:** {meaning.capitalize()}.")
    first, second, third = cards
    first_meaning = first[0]["reversed"] if first[1] else first[0]["upright"]
    second_meaning = second[0]["reversed"] if second[1] else second[0]["upright"]
    third_meaning = third[0]["reversed"] if third[1] else third[0]["upright"]
    intro = f"For your intention, **{intention}**, " if intention else ""
    return (
        intro + "read these cards as a connected reflection, not a fixed forecast. "
        + "The first card invites you to examine the background and patterns that brought you here: "
        + first_meaning + ". The second describes a theme worth noticing in the present: "
        + second_meaning + ". The third offers a constructive direction to consider: "
        + third_meaning + ". Taken together, the spread suggests looking honestly at what shaped the situation, "
        "meeting the present without catastrophizing, and choosing one grounded action that supports the future "
        "you want. Keep what fits your lived experience, question what does not, and let real-world evidence "
        "guide important decisions."
    )


def render_tarot() -> None:
    st.markdown("## ✦ Tarot")
    st.caption("A reflective reading for perspective—not a fixed prediction or a substitute for your own judgment.")
    st.markdown(
        "<div style='border:1px solid rgba(188,140,255,.4);border-radius:12px;padding:.8rem 1rem;margin:.4rem 0 1rem;background:linear-gradient(145deg,rgba(35,22,65,.55),rgba(5,7,10,.8));'>"
        "<strong>Our reading promise</strong><br>Honest about challenges. Open to possibilities. No doom, fear tactics, or false certainty."
        "</div>", unsafe_allow_html=True
    )

    _render_sample_reading()
    st.markdown("---")
    st.markdown("### Choose your own three cards")
    st.write("Browse the deck and select one card for each position. Your cards are revealed together when you are ready.")
    intention = st.text_input(
        "Optional question or intention", max_chars=240,
        placeholder="What would be useful to reflect on?", key="tarot_intention_picker"
    )
    st.caption("You can leave this blank. Avoid entering private information you would not want saved in the app session.")

    names = [card["name"] for card in DECK]
    # Compact, mobile-friendly selection controls keep the complete deck available without
    # loading 78 large images at once; selected cards are shown with their artwork on reveal.
    selected = []
    picker_cols = st.columns(3)
    labels = ["What shaped this", "What is present", "A helpful next step"]
    for i, (col, label) in enumerate(zip(picker_cols, labels)):
        with col:
            st.markdown(f"**{i + 1}. {label}**")
            chosen_name = st.selectbox(
                "Choose a card", names, index=(i * 17 + 11) % len(names),
                key=f"tarot_selected_card_{i}", label_visibility="collapsed"
            )
            selected.append(chosen_name)

    if len(set(selected)) < 3:
        st.warning("Choose three different cards to make your reading.")
    if st.button(
        "Reveal my three cards", type="primary", use_container_width=True,
        key="tarot_reveal_selected"
    ):
        if len(set(selected)) == 3:
            st.session_state["tarot_selected_reading"] = {
                "cards": [(name, random.random() < 0.28) for name in selected],
                "intention": intention.strip(),
            }

    reading = st.session_state.get("tarot_selected_reading")
    if reading:
        reading_names = [name for name, _ in reading["cards"]]
        if reading_names == selected:
            st.markdown(
                "<style>@keyframes tarotReveal{0%{transform:rotateY(90deg);opacity:.15}100%{transform:rotateY(0);opacity:1}}"
                ".tarot-reveal{animation:tarotReveal .65s ease-out both;transform-origin:center;}</style>",
                unsafe_allow_html=True
            )
            st.markdown("### Your revealed reading")
            lookup = {card["name"]: card for card in DECK}
            drawn = [(lookup[name], reversed_card) for name, reversed_card in reading["cards"]]
            reveal_cols = st.columns(3)
            for col, ((card, reversed_card), position) in zip(reveal_cols, zip(drawn, labels)):
                with col:
                    st.markdown("<div class='tarot-reveal'>", unsafe_allow_html=True)
                    _display_card(card, reversed_card, position)
                    st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("### Bringing the reading together")
            st.markdown(_combine_three_cards(drawn, reading.get("intention", "")))
            st.info(
                "Reflection, not fate: a difficult theme is not a sentence or a guarantee. "
                "Use it as a prompt to prepare, seek support, set a boundary, or choose a different approach."
            )
        else:
            st.caption("Your previous reveal is kept below only when it matches your current card choices. Reveal again to update it.")

    with st.expander("Browse all 78 cards and their meanings"):
        for card in DECK:
            st.markdown(f"**{card['name']}** — {card['upright']}.")
            st.caption("Reversed: " + card["reversed"] + ".")
